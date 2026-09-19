"""Pluggable LLM client with disk cache. No key configured -> available() is False
and every caller must fall back to the deterministic rules engine.

Providers: openai | deepseek | groq | openrouter  (all OpenAI-compatible)
           anthropic | gemini
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import time
from pathlib import Path

import requests

import config, sanitize

_ENDPOINTS = {
    "openai": "https://api.openai.com/v1/chat/completions",
    "deepseek": "https://api.deepseek.com/chat/completions",
    "groq": "https://api.groq.com/openai/v1/chat/completions",
    "openrouter": "https://openrouter.ai/api/v1/chat/completions",
}
_TIMEOUT = 60


class LLMClient:
    def __init__(self):
        self.provider = config.LLM_PROVIDER
        self.key = config.LLM_API_KEY
        self.model = config.LLM_MODEL
        self.fast_model = config.LLM_FAST_MODEL
        self.cache_dir = config.CACHE_DIR
        self.enabled = config.effective_llm_enabled()
        if config.LLM_CACHE:
            self.cache_dir.mkdir(parents=True, exist_ok=True)

    # ---------------- public ----------------
    def available(self) -> bool:
        return self.enabled

    def chat_json(self, system: str, user: str, model: str | None = None,
                  use_cache: bool = True) -> dict | None:
        """Returns parsed JSON dict or None (caller falls back to rules)."""
        if not self.available():
            return None
        model = model or self.model
        cache_key = hashlib.sha256(
            json.dumps([self.provider, model, system, user], ensure_ascii=False).encode()
        ).hexdigest()
        cpath = self.cache_dir / f"{cache_key}.json"
        if use_cache and cpath.exists():
            try:
                return json.loads(cpath.read_text(encoding="utf-8"))
            except Exception:
                pass
        raw = self._call(system, user, model)
        data = self._extract_json(raw) if raw else None
        if data is not None and config.LLM_CACHE:
            try:
                cpath.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
            except Exception:
                pass
        return data

    def safe_doc(self, text: str) -> tuple[str, list[str]]:
        """Sanitize a document before embedding into a prompt (if sanitizer on)."""
        if config.FLAG_SANITIZE:
            return sanitize.sanitize_text(text)
        return text, []

    # ---------------- providers ----------------
    def _call(self, system: str, user: str, model: str) -> str | None:
        try:
            if self.provider in _ENDPOINTS:
                r = requests.post(
                    _ENDPOINTS[self.provider],
                    headers={"Authorization": f"Bearer {self.key}",
                             "HTTP-Referer": "https://sentinel.local",
                             "X-Title": "SENTINEL-SDOC"},
                    json={
                        "model": model,
                        "temperature": config.LLM_TEMPERATURE,
                        "response_format": {"type": "json_object"},
                        "messages": [
                            {"role": "system", "content": system},
                            {"role": "user", "content": user},
                        ],
                    },
                    timeout=_TIMEOUT,
                )
                r.raise_for_status()
                return r.json()["choices"][0]["message"]["content"]

            if self.provider == "anthropic":
                r = requests.post(
                    "https://api.anthropic.com/v1/messages",
                    headers={"x-api-key": self.key, "anthropic-version": "2023-06-01"},
                    json={
                        "model": model,
                        "max_tokens": 1024,
                        "temperature": config.LLM_TEMPERATURE,
                        "system": system + "\nRespond with a single JSON object and nothing else.",
                        "messages": [{"role": "user", "content": user}],
                    },
                    timeout=_TIMEOUT,
                )
                r.raise_for_status()
                return r.json()["content"][0]["text"]

            if self.provider == "gemini":
                url = (f"https://generativelanguage.googleapis.com/v1beta/models/"
                       f"{model}:generateContent?key={self.key}")
                r = requests.post(url, json={
                    "systemInstruction": {"parts": [{"text": system}]},
                    "contents": [{"role": "user", "parts": [{"text": user}]}],
                    "generationConfig": {
                        "temperature": config.LLM_TEMPERATURE,
                        "responseMimeType": "application/json",
                    },
                }, timeout=_TIMEOUT)
                r.raise_for_status()
                return r.json()["candidates"][0]["content"]["parts"][0]["text"]
        except Exception as e:  # noqa: BLE001 — never crash the pipeline on LLM errors
            print(f"[llm] call failed ({self.provider}/{model}): {e}")
            return None
        return None

    @staticmethod
    def _extract_json(text: str | None) -> dict | None:
        if not text:
            return None
        text = text.strip()
        m = re.search(r"\{.*\}", text, re.S)
        if not m:
            return None
        try:
            data = json.loads(m.group(0))
            return data if isinstance(data, dict) else None
        except json.JSONDecodeError:
            return None
