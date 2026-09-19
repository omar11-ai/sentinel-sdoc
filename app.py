"""SENTINEL — FastAPI service: dashboard + API + optional self-eval proxy."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import requests
from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel

sys.path.insert(0, str(Path(__file__).resolve().parent))

import config                      # noqa: E402
from loader import Inbox           # noqa: E402
from pipeline import run           # noqa: E402
from llm import LLMClient          # noqa: E402

app = FastAPI(title="SENTINEL — Shipping Document Verification", version="1.0.0")

_STATE: dict = {"results": None}


def _ensure_results() -> dict:
    if _STATE["results"] is None:
        _STATE["results"] = run(Inbox())
    return _STATE["results"]


@app.on_event("startup")
async def _startup() -> None:
    try:
        _ensure_results()
    except Exception as e:  # noqa: BLE001 — never block startup; dashboard shows the error
        _STATE["results"] = {"error": str(e), "emails": [], "summary": {}, "submission": {},
                             "config": {}, "generated_at": None, "elapsed_s": 0}


@app.get("/api/health")
async def health():
    try:
        r = _ensure_results()
        return {"status": "ok", "emails": r.get("summary", {}).get("total", 0),
                "llm": r.get("config", {}).get("llm", "?")}
    except Exception as e:  # noqa: BLE001
        return {"status": "degraded", "error": str(e)}


@app.get("/api/results")
async def results():
    r = _ensure_results()
    public = {k: v for k, v in r.items() if k != "submission"}
    return JSONResponse(public)


@app.get("/api/submission")
async def submission():
    """The system's own submission document (what /submit would send)."""
    r = _ensure_results()
    return JSONResponse({"submission": r.get("submission", {})})


@app.get("/api/emails/{email_id}")
async def email_detail(email_id: str):
    r = _ensure_results()
    for e in r.get("emails", []):
        if e["email_id"] == email_id:
            return JSONResponse(e)
    return JSONResponse({"error": "not found"}, status_code=404)


class Submission(BaseModel):
    data: dict


@app.post("/api/submit")
async def submit(sub: Submission):
    """Self-evaluation. Proxies to the official scoring server when configured."""
    if config.SCORING_URL:
        try:
            resp = requests.post(f"{config.SCORING_URL}/submit", json=sub.data, timeout=30)
            return JSONResponse({"source": "official_server",
                                 "status_code": resp.status_code,
                                 "scoreboard": _safe_json(resp)})
        except Exception as e:  # noqa: BLE001
            return JSONResponse({"source": "official_server", "error": str(e)}, status_code=502)
    # no scoring server: local sanity summary only
    r = _ensure_results()
    return JSONResponse({
        "source": "local",
        "message": "No SCORING_URL configured — showing local output summary. "
                   "Set SENTINEL_SCORING_URL to the hackathon server to self-evaluate.",
        "local_summary": r.get("summary", {}),
        "submitted_entries": len(sub.data),
    })


class GeneralizeReq(BaseModel):
    subject: str = ""
    body: str = ""
    si_text: str = ""
    bl_text: str = ""


@app.post("/api/generalize")
async def generalize(req: GeneralizeReq):
    """Judge-facing: paste a NEW email (not from the dataset) and watch the
    AI-first path classify + extract + compare it live. LLM when configured,
    deterministic fallback otherwise."""
    import tempfile
    from classify import classify_email
    from extract import extract_document as _ext
    from compare import compare as _cmp
    from escalate import judge as _judge
    from normalize import norm_value

    def _fake_get_bytes(content: str):
        def _get(_path):
            return content.encode("utf-8")
        return _get

    client = LLMClient()
    email = {"email_id": "pasted", "subject": req.subject, "body": req.body, "attachments": []}
    cls = classify_email(client, email)

    si_doc = bl_doc = None
    if req.si_text.strip():
        si_doc = _ext(client, "pasted_SI.txt", _fake_get_bytes(req.si_text), client.available(), True)
    if req.bl_text.strip():
        bl_doc = _ext(client, "pasted_BL.txt", _fake_get_bytes(req.bl_text), client.available(), True)

    result = {"classification": cls, "llm_available": client.available(),
              "llm_provider": f"{config.LLM_PROVIDER}:{config.LLM_MODEL}" if client.available() else None}

    # prompt-injection screening on pasted documents (untrusted input!)
    from sanitize import sanitize_text
    inj_flags: list[str] = []
    if config.FLAG_SANITIZE:
        _t, f_si = sanitize_text(req.si_text or "")
        _t2, f_bl = sanitize_text(req.bl_text or "")
        inj_flags = list(dict.fromkeys(f_si + f_bl))
    result["injection_flags"] = inj_flags

    if cls["category"] != "BL_COMPARISON":
        result.update({"route": cls["category"], "status": "OK",
                       "note": "not a document-comparison request — classification only"})
        return JSONResponse(result)

    common = 0
    blanks: list[str] = []
    cmp_res = None
    if si_doc and bl_doc:
        blanks = sorted(set(si_doc.get("blank_fields", []) + bl_doc.get("blank_fields", [])))
        sf, bf = si_doc["fields"], bl_doc["fields"]
        common = sum(1 for f in config.FIELDS
                     if f in sf and f in bf and not sf[f].get("blank") and not bf[f].get("blank"))
        esc, canonical, details = _judge(si_doc, bl_doc, 2, "compare", common, blanks, [])
        if esc:
            result.update({"status": "NEEDS_REVIEW", "review_reason": canonical,
                           "details": details, "si": _pub(si_doc), "bl": _pub(bl_doc)})
            return JSONResponse(result)
        cmp_res = _cmp(si_doc, bl_doc)
        result.update({
            "status": "MISMATCH" if cmp_res["defects"] else "OK",
            "defects": cmp_res["defects"],
            "si": _pub(si_doc), "bl": _pub(bl_doc),
        })
    else:
        result.update({"status": "NEEDS_REVIEW", "review_reason": "missing_attachment",
                       "details": ["paste both SI and BL text to compare"]})
    return JSONResponse(result)


def _pub(doc):
    return {"engine": doc["engine"], "coverage": doc["coverage"],
            "confidence": doc["confidence"], "fields": doc["fields"]}


@app.post("/api/run")
async def rerun():
    _STATE["results"] = run(Inbox())
    return await results()


@app.get("/")
async def dashboard():
    return FileResponse(Path(__file__).resolve().parent / "static" / "index.html")


def _safe_json(resp: requests.Response):
    try:
        return resp.json()
    except json.JSONDecodeError:
        return {"raw": resp.text[:1000]}
