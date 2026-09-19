"""Prompt-injection defense: documents are UNTRUSTED input.

Detects instruction-override attempts and strips control characters before any
LLM sees the text. Flags never change rules-engine decisions — they are surfaced
for review and logged.
"""
from __future__ import annotations

import re

PATTERNS: list[tuple[str, re.Pattern]] = [
    ("instruction_override", re.compile(
        r"(ignore|disregard|forget)\s+(all\s+|any\s+)?(previous|prior|above)\s+(instructions|prompts?|rules?)",
        re.I)),
    ("role_hijack", re.compile(
        r"(you\s+are\s+now|act\s+as|pretend\s+to\s+be|from\s+now\s+on\s+you\s+are)\s+", re.I)),
    ("system_prompt_probe", re.compile(
        r"(system\s*prompt|repeat\s+your\s+instructions|reveal\s+your\s+prompt|initial\s+instructions)",
        re.I)),
    ("verdict_manipulation", re.compile(
        r"(mark|report|classify|label)\s+(this|it|the\s+\w+)?\s*(as\s+)?(match|matched|mismatch|no\s+mismatch|spham|spam)",
        re.I)),
    ("fake_delimiters", re.compile(r"(<\|?endoftext\|?>|###\s*(system|instruction)|```system)", re.I)),
    ("authority_spoof", re.compile(
        r"(as\s+an?\s+admin|administrator\s+note|developer\s+message|operator\s+override)", re.I)),
]

_CTRL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
_ZW = re.compile(r"[\u200b-\u200f\u202a-\u202e\u2060\ufeff]")


def sanitize_text(text: str) -> tuple[str, list[str]]:
    """Returns (clean_text, flags). Clean text is safe(r) to embed in prompts."""
    flags: list[str] = []
    if not text:
        return text, flags
    for name, rx in PATTERNS:
        if rx.search(text):
            flags.append(name)
    clean = _CTRL.sub(" ", text)
    clean = _ZW.sub("", clean)
    return clean, flags
