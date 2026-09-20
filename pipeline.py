"""SENTINEL pipeline v2 — real data_v2 wiring: intent split, lanes, canonical escalation."""
from __future__ import annotations

import re
import time
from datetime import datetime, timezone

import config
import schema
from loader import Inbox
from llm import LLMClient
from classify import classify_email
from extract import extract_document
from verifier import verify_extraction
from compare import compare
from escalate import judge, no_docs_intent
from corpus import build_alias_clusters, notes_for_email
from sanitize import sanitize_text


def run(inbox: Inbox | None = None, progress_cb=None) -> dict:
    inbox = inbox or Inbox()
    client = LLMClient()
    t0 = time.time()
    emails = inbox.emails()
    get_bytes = inbox.read_bytes
    results: list[dict] = []

    for idx, email in enumerate(emails):
        eid = inbox.get_id(email)
        subject = inbox.get_subject(email)
        body = inbox.get_body(email)
        attachments = inbox.get_attachments(email)

        cls = classify_email(client, email)
        category = cls["category"]
        rec = {
            "email_id": eid, "subject": subject, "attachments": attachments,
            "category": category,
            "category_confidence": round(cls["confidence"], 2),
            "classifier_engine": cls["engine"], "classifier_reason": cls.get("reason", ""),
            "classifier_disagreement": bool(cls.get("disagreement")),
            "status": config.STATUS_FOR_NON_BL, "has_defect": False,
            "defect_fields": [], "review_reason": None,
            "si": None, "bl": None, "comparison": None,
            "injection_flags": [], "corpus_notes": [], "verifier": None, "engine_trace": [],
        }

        if category == "BL_COMPARISON":
            si_path, bl_path = inbox.guess_si_bl(email)
            intent = no_docs_intent(body) if not attachments else "compare"

            use_llm = client.available() and config.LLM_BATCH and config.LLM_EXTRACT
            shaky = (cls["confidence"] < config.COURT_CONFIDENCE) or bool(cls.get("disagreement"))

            si_doc = extract_document(client, si_path, get_bytes, use_llm, shaky) if si_path else None
            bl_doc = extract_document(client, bl_path, get_bytes, use_llm, shaky) if bl_path else None
            rec["si"] = _doc_public(si_doc) if si_doc else None
            rec["bl"] = _doc_public(bl_doc) if bl_doc else None
            if si_doc:
                rec["engine_trace"].append(f"si:{si_doc['engine']}/{si_doc['doc_status']}")
            if bl_doc:
                rec["engine_trace"].append(f"bl:{bl_doc['engine']}/{bl_doc['doc_status']}")

            # sanitizer on whichever docs we have
            flags: list[str] = []
            if config.FLAG_SANITIZE:
                for doc in (si_doc, bl_doc):
                    if not doc or doc["doc_status"] != "ok":
                        continue
                    raw = get_bytes(doc["path"])
                    text = (raw or b"").decode("utf-8", errors="replace")
                    _, f = sanitize_text(text)
                    flags.extend(f)
            rec["injection_flags"] = list(dict.fromkeys(flags))

            comparable, canonical, esc_details, cmp_res = True, "", [], None
            if intent == "send_me" and not attachments:
                rec["status"] = "OK"          # request to RECEIVE the BL — clean OK, not an escalation
                rec["review_reason"] = None
                results.append(rec)
                if progress_cb:
                    progress_cb(idx + 1, len(emails), eid)
                continue
            else:
                blanks = sorted(set((si_doc or {}).get("blank_fields", []) +
                                    (bl_doc or {}).get("blank_fields", [])))
                common = _common_fields(si_doc, bl_doc)
                escalate_now, canonical, esc_details = judge(
                    si_doc, bl_doc, len(attachments), intent, common, blanks,
                    rec["injection_flags"])
                if escalate_now:
                    comparable = False
                else:
                    cmp_res = compare(si_doc, bl_doc)
                    rec["comparison"] = cmp_res

            if comparable:
                # adversarial verifier on the BL doc (log-only in advisory)
                verifier = None
                if (config.FLAG_ADVERSARIAL and config.LLM_BATCH
                        and client.available() and bl_doc and bl_doc["fields"]):
                    attack = {f: bl_doc["fields"][f] for f in list(bl_doc["fields"])[:7]}
                    bl_bytes = get_bytes(bl_doc["path"]) or b""
                    verifier = verify_extraction(client, attack,
                                                 bl_bytes.decode("utf-8", errors="replace"),
                                                 config.ADVERSARIAL_MODE)
                rec["verifier"] = {"mode": config.ADVERSARIAL_MODE,
                                   "objections": (verifier or {}).get("objections", []),
                                   "enforcing_flip": (verifier or {}).get("enforcing_flip", False)}
                if cmp_res["defects"]:
                    rec["status"] = "MISMATCH"
                    rec["has_defect"] = True
                    rec["defect_fields"] = [d["field"] for d in cmp_res["defects"]]
                else:
                    rec["status"] = "OK"
            else:
                rec["status"] = "NEEDS_REVIEW"
                reason = canonical or "missing_value"
                if esc_details:
                    reason = reason + " — " + "; ".join(esc_details)
                rec["review_reason"] = reason

        results.append(rec)
        if progress_cb:
            progress_cb(idx + 1, len(emails), eid)

    if config.FLAG_CORPUS:
        ext_for_corpus = {}
        for r in results:
            if r["si"] and r["si"].get("fields"):
                ext_for_corpus[r["email_id"]] = r["si"]["fields"]
        clusters = build_alias_clusters(ext_for_corpus)
        for r in results:
            if r["si"] and r["si"].get("fields"):
                r["corpus_notes"] = notes_for_email(r["si"]["fields"], clusters)

    submission = schema.build_submission(results)
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "elapsed_s": round(time.time() - t0, 2),
        "summary": summarize(results),
        "emails": results,
        "submission": submission,
        "config": public_config(),
    }



def _common_fields(si_doc, bl_doc) -> int:
    if not si_doc or not bl_doc:
        return 0
    sf, bf = si_doc["fields"], bl_doc["fields"]
    n = 0
    for f in config.FIELDS:
        s, b = sf.get(f), bf.get(f)
        if s and b and not s.get("blank") and not b.get("blank"):
            n += 1
    return n


def _doc_public(doc: dict) -> dict:
    return {"fields": doc["fields"], "coverage": doc["coverage"],
            "confidence": doc["confidence"], "engine": doc["engine"],
            "doc_status": doc["doc_status"], "kind": doc["kind"],
            "blank_fields": doc["blank_fields"], "path": doc["path"]}


def summarize(results: list[dict]) -> dict:
    from collections import Counter
    cats = Counter(r["category"] for r in results)
    stats = Counter(r["status"] for r in results)
    confs = [r["category_confidence"] for r in results]
    return {
        "total": len(results),
        "categories": dict(cats),
        "statuses": dict(stats),
        "mismatch": stats.get("MISMATCH", 0),
        "ok": stats.get("OK", 0),
        "needs_review": stats.get("NEEDS_REVIEW", 0),
        "avg_confidence": round(sum(confs) / len(confs), 2) if confs else 0.0,
        "injection_flagged": sum(1 for r in results if r["injection_flags"]),
        "corpus_notes": sum(1 for r in results if r["corpus_notes"]),
    }


def public_config() -> dict:
    client = LLMClient()
    return {
        "mode": config.MODE,
        "data_dir": str(config.DATA_DIR),
        "llm": (f"{config.LLM_PROVIDER}:{config.LLM_MODEL}" if client.available()
                else "off (rules engine)"),
        "court": config.FLAG_COURT,
        "court_confidence": config.COURT_CONFIDENCE,
        "adversarial": config.ADVERSARIAL_MODE if config.FLAG_ADVERSARIAL else "off",
        "sanitize": config.FLAG_SANITIZE,
        "corpus_notes": config.FLAG_CORPUS,
        "min_common_fields": config.MIN_COMMON_FIELDS,
        "scoring_url": config.SCORING_URL or "not configured",
    }
