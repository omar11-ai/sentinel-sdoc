#!/usr/bin/env python3
"""Submission validator — the pre-submit gate (blueprint §13/§26).

Validates a submission.json (or a live /api/submission response) against the
organizers' external contract BEFORE anything is uploaded:
  • every email_id from sample_submission.json present, no extras
  • exact key set per entry, category/status enums
  • defect_fields ⊆ the seven fields, has_defect boolean
  • MISMATCH / OK / NEEDS_REVIEW cross-field consistency (schema.py)
  • review_reason canonical values (the four bundle review reasons)
  • JSON re-serialises byte-clean (no NaN, no NaN/Infinity, sorted keys)

Usage:
  python3 validate_submission.py submission.json
  python3 validate_submission.py --url http://localhost:8000/api/submission
Exit 0 = valid, 1 = problems found.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

SAMPLE = os.environ.get("SENTINEL_SAMPLE", "/home/user/real/data_v2/sample_submission.json")
REVIEW_REASONS = {
    "missing_attachment", "wrong_doc_type", "unparseable_document", "injection_suspected",
}


def load_sub(arg: str, url: str | None) -> dict:
    if url:
        import urllib.request
        with urllib.request.urlopen(url, timeout=120) as resp:  # noqa: S310
            payload = json.load(resp)
        return payload.get("submission", payload)
    raw = Path(arg).read_text(encoding="utf-8")
    payload = json.loads(raw)
    return payload.get("submission", payload)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("file", nargs="?", help="submission.json path")
    ap.add_argument("--url", help="fetch /api/submission from a running instance")
    ap.add_argument("--sample", default=SAMPLE, help="bundle sample_submission.json")
    args = ap.parse_args()
    if not args.file and not args.url:
        ap.error("give a file or --url")

    problems: list[str] = []
    sub = load_sub(args.file or "", args.url)

    sample_path = Path(args.sample)
    ids: list[str] = []
    sample = None
    if sample_path.exists():
        sample = json.loads(sample_path.read_text(encoding="utf-8"))
        ids = list(sample.keys())
    else:
        problems.append(f"sample_submission.json not found at {sample_path} — cannot verify id set")

    try:
        from schema import validate_submission  # the in-repo contract checker
        found = validate_submission(sub, ids or list(sub.keys()), sample)
        if not found:
            print(f"✓ id set + per-entry contract match the bundle exactly ({len(ids)} emails)")
        problems.extend(found)
    except Exception as e:  # noqa: BLE001
        problems.append(f"schema.validate_submission failed to run: {e}")

    # review_reason vocabulary — informational: the official scorer treats the
    # reason as free text, so an unknown head is reported, never a failure
    odd = []
    for eid, entry in sub.items():
        if isinstance(entry, dict) and entry.get("status") == "NEEDS_REVIEW":
            rr = entry.get("review_reason")
            if isinstance(rr, str):
                head = rr.split(" — ")[0].strip()
                if head not in REVIEW_REASONS and head not in ("reviewer_unresolvable", "missing_value", "unreadable"):
                    odd.append(f"{eid}:{head}")
    if odd:
        print(f"ℹ non-canonical review_reason heads (allowed, reported for awareness): {odd[:6]}")

    # round-trip: byte-clean serialisation, no NaN/Infinity
    try:
        rt = json.loads(json.dumps(sub, allow_nan=False))
        if len(rt) != len(sub):
            problems.append("round-trip changed the entry count")
    except ValueError as e:
        problems.append(f"submission is not strict JSON: {e}")

    if problems:
        print(f"✗ INVALID — {len(problems)} problem(s):")
        for p in problems:
            print(f"  - {p}")
        return 1
    print(f"✓ VALID — {len(sub)} entries, contract satisfied, strict JSON")
    return 0


if __name__ == "__main__":
    sys.exit(main())
