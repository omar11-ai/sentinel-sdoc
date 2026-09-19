"""L5 Escalation Judge v2 — canonical GT-aligned reasons, single clean entry point.

Priority: missing_attachment > unreadable > wrong_doc_type > missing_value.
Reason keywords match the official vocabulary; human detail appended for reviewers.
"""
from __future__ import annotations

import re

import config
from docparse import NOT_BL_KINDS

SEND_CUES = [
    r"please\s+(?:kindly\s+)?send", r"kindly\s+send", r"pls\s+send", r"plz\s+send",
    r"share\s+the\s+(?:draft\s+)?bl", r"provide\s+(?:us\s+)?(?:with\s+)?the\s+(?:draft\s+)?bl",
    r"send\s+(?:us\s+)?the\s+(?:draft\s+)?bl", r"forward\s+the\s+(?:draft\s+)?bl",
    r"await(?:ing)?\s+(?:the\s+)?(?:draft\s+)?bl", r"send\s+the\s+draft", r"share\s+the\s+draft",
    r"once\s+(?:we\s+)?(?:receive|get)", r"we\s+(?:have\s+)?not\s+(?:yet\s+)?received",
    r"(?:still\s+)?(?:waiting|await)\b.{0,20}\b(?:bl|draft|documents?)",
]
ATTACHED_CUES = [
    r"attach(?:ed|ment|ments)?\b", r"enclos", r"as\s+(?:per|in)\s+(?:the\s+)?attach",
    r"documents?\s+attached", r"find\s+attached",
]


# External-sender security banners are boilerplate — they mention "attachments"
# without meaning "documents are attached". (The participant README explicitly
# flags this: "bodies contain ... external-sender warning banners".)
_BANNER = re.compile(r"WARNING:\s*This email originated outside[^\n]*", re.I)


def no_docs_intent(body: str) -> str:
    """For requests with no (or partial) attachments: are docs expected, or is this
    a 'please send me the draft' request (nothing to compare yet -> legitimate OK)?"""
    b = _BANNER.sub("", body or "")
    if any(re.search(p, b, re.I) for p in ATTACHED_CUES):
        return "expected_docs"
    if any(re.search(p, b, re.I) for p in SEND_CUES):
        return "send_me"
    return "send_me"  # benign default


def judge(si: dict | None, bl: dict | None, n_attachments: int, intent: str,
          common: int | None = None, blanks: list[str] | None = None,
          injection_flags: list[str] | None = None) -> tuple[bool, str, list[str]]:
    """si/bl: extraction dicts (or None). Returns (escalate?, canonical_reason, details)."""
    blanks = blanks or []
    injection_flags = injection_flags or []
    details: list[str] = []

    if intent == "send_me":
        return False, "", []

    if n_attachments == 0:
        return True, "missing_attachment", ["comparison request but no documents attached"]

    if si is None or si.get("doc_status") == "missing":
        return True, "missing_attachment", ["SI (reference) document not found among attachments"]
    if bl is None or bl.get("doc_status") == "missing":
        return True, "missing_attachment", ["BL document not found among attachments"]

    reasons: list[tuple[str, str]] = []
    for name, doc in (("SI", si), ("BL", bl)):
        ds = doc.get("doc_status")
        if ds in ("empty", "corrupt", "image_only"):
            reasons.append(("unreadable", f"{name} document {ds}"))

    kind = bl.get("kind")
    if kind in NOT_BL_KINDS:
        reasons.append(("wrong_doc_type",
                        f"BL slot actually contains a {str(kind).replace('_', ' ')}"))

    if blanks:
        reasons.append(("missing_value",
                        "blank/placeholder values: " + ", ".join(sorted(set(blanks)))))

    if not reasons and common is not None and common < config.MIN_COMMON_FIELDS:
        reasons.append(("missing_value",
                        f"only {common}/7 fields extractable across both documents"))

    if not reasons and injection_flags:
        reasons.append(("unreadable", "untrusted/injection content — manual review"))

    if not reasons:
        return False, "", []
    canonical, detail = reasons[0]
    return True, canonical, [detail] + [d for _, d in reasons[1:]]
