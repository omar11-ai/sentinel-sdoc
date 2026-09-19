"""Submission schema v2 — exact data_v2 semantics."""
from __future__ import annotations

import config

REQUIRED_KEYS = ["category", "status", "review_reason", "has_defect", "defect_fields"]


def build_entry(category: str, status: str, has_defect: bool,
                defect_fields: list[str] | None, review_reason: str | None) -> dict:
    return {
        "category": category,
        "status": status,
        "review_reason": review_reason,
        "has_defect": bool(has_defect),
        "defect_fields": sorted(defect_fields or []),
    }


def build_submission(results: list[dict]) -> dict:
    sub: dict[str, dict] = {}
    for r in results:
        sub[r["email_id"]] = build_entry(
            r["category"], r["status"], r["has_defect"],
            r["defect_fields"], r["review_reason"])
    return sub


def validate_submission(sub: dict, all_ids: list[str], sample: dict | None = None) -> list[str]:
    problems: list[str] = []
    missing = [i for i in all_ids if i not in sub]
    extra = [i for i in sub if i not in set(all_ids)]
    if missing:
        problems.append(f"missing {len(missing)} email_ids: {missing[:8]}{'...' if len(missing) > 8 else ''}")
    if extra:
        problems.append(f"unknown email_ids present: {extra[:8]}")

    for eid, entry in sub.items():
        if not isinstance(entry, dict):
            problems.append(f"{eid}: entry is not an object")
            continue
        for k in REQUIRED_KEYS:
            if k not in entry:
                problems.append(f"{eid}: missing key '{k}'")
        if entry.get("category") not in config.CATEGORIES:
            problems.append(f"{eid}: bad category {entry.get('category')!r}")
        if entry.get("status") not in config.STATUSES:
            problems.append(f"{eid}: bad status {entry.get('status')!r}")
        dfs = entry.get("defect_fields")
        if not isinstance(dfs, list):
            problems.append(f"{eid}: defect_fields must be a list")
        else:
            bad = [f for f in dfs if f not in config.FIELDS]
            if bad:
                problems.append(f"{eid}: unknown defect_fields {bad}")
        if not isinstance(entry.get("has_defect"), bool):
            problems.append(f"{eid}: has_defect must be boolean")
        rr = entry.get("review_reason")
        if rr is not None and not isinstance(rr, str):
            problems.append(f"{eid}: review_reason must be null or string")

        status = entry.get("status")
        if status == "MISMATCH":
            if entry.get("has_defect") is not True:
                problems.append(f"{eid}: MISMATCH requires has_defect=true")
            if isinstance(dfs, list) and not dfs:
                problems.append(f"{eid}: MISMATCH requires non-empty defect_fields")
            if rr is not None:
                problems.append(f"{eid}: MISMATCH should have review_reason=null")
        elif status == "OK":
            if entry.get("has_defect") is not False:
                problems.append(f"{eid}: OK requires has_defect=false")
            if isinstance(dfs, list) and dfs:
                problems.append(f"{eid}: OK requires empty defect_fields")
            if rr is not None:
                problems.append(f"{eid}: OK should have review_reason=null")
        else:  # NEEDS_REVIEW
            if entry.get("has_defect") is not False:
                problems.append(f"{eid}: NEEDS_REVIEW requires has_defect=false")
            if isinstance(dfs, list) and dfs:
                problems.append(f"{eid}: NEEDS_REVIEW requires empty defect_fields")
            if not rr:
                problems.append(f"{eid}: NEEDS_REVIEW requires a review_reason")
    return problems
