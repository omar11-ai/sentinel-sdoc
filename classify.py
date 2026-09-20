"""L1 Triage v2 — classifier tuned to real data_v2 subject/body conventions."""
from __future__ import annotations

import re

import config
from llm import LLMClient

# ---------------- SPAM ----------------
_SPAM_S = [r"you\s+(?:have\s+)?won\b", r"winner", r"prize", r"lottery", r"claim\s+your",
           r"mailbox\s+is\s+full", r"parcel\s+fee", r"customs?\s+fee.{0,20}(?:release|collect)",
           r"verify\s+your\s+account", r"urgent\s+action\s+required", r"limited\s+time",
           r"congratulations", r"weird\s+trick", r"bitcoin", r"investment\s+opportunity",
           r"guaranteed\s+\d+%\s+returns", r"exclusive\s+offer", r"\d{2,3}%\s+off\b",
           r"update\s+your\s+account", r"(?:email\s+)?storage\s+is\s+full",
           r"hot\s+singles", r"dear\s+valued\s+customer",
           r"singles?\s+in\s+your\s+area", r"avoid\s+suspension"]
_SPAM_B = [r"unsubscribe", r"click\s+(?:here|the\s+link)", r"act\s+now", r"free\s+money",
           r"crypto", r"lottery", r"you\s+have\s+won", r"claim\s+your\s+prize",
           r"100%\s+free", r"risk[- ]free", r"miracle"]

# ---------------- SI_REQUEST ----------------
_SIR_S = [r"^si\s*[-–>:]", r"[\|\-–]\s*si\s*[-–>]", r"\bcust(?:omer)?\s+si\b", r"\brequest(?:ing)?\s+si\b",
          r"\bsi\s+needed\b", r"\bnew\s+si\b", r"\bsi\s+request\b", r"shipping\s+instruction\s+request"]
_SIR_B = [r"shipping\s+instruction\s+(?:is\s+)?(?:required|needed|requested)",
          r"(?:prepare|draft|issue|create|make|provide|send|share)\b.{0,30}\bshipping\s+instruction",
          r"shipping\s+instruction.{0,30}\b(?:for\s+the\s+new|new)\b",
          r"\bnew\s+si\b", r"provide\s+(?:us\s+with\s+)?(?:a\s+)?(?:new\s+)?si\b",
          r"send\s+(?:us\s+)?the\s+si\b", r"si\s+for\s+(?:this\s+)?shipment"]

# ---------------- BL_COMPARISON ----------------
_BL_S = [r"to\s+confirm\s+docs?\b", r"request\s+bl\s+draft", r"\bbl\s+draft\b", r"draft\s+bl\b",
         r"\bcheck\s+docs?\b", r"docs?\s+check\b", r"document\s+check", r"verify.{0,20}\bbl\b",
         r"\bbl\b.{0,12}\b(?:check|confirm|verify|review)\b",
         r"(?:check|confirm|verify|review).{0,12}\bbl\b", r"\bamend\b.{0,20}\bbl\b",
         r"bl\s+for\s+approval", r"bl\s+to\s+be\s+(?:checked|confirmed|approved)"]
_BL_B = [r"attached\s+are\s+the\s+si", r"\bsi\b.{0,30}\b(?:and|with|&)\b.{0,10}\b(?:draft\s+)?bl\b",
         r"draft\s+bill\s+of\s+lading", r"(?:check|verify|confirm|review|compare)\b.{0,40}"
         r"(?:documents?|draft|bl|bill\s+of\s+lading)",
         r"against\s+the\s+shipping\s+instruction", r"shipping\s+instruction.{0,40}(?:attached|enclosed)",
         r"before\s+(?:we\s+)?(?:finali[sz]|releas|approv)", r"\bdiscrepanc", r"\bmismatch\b",
         r"please\s+(?:check|verify|confirm|review)\s+the\s+(?:attached\s+)?(?:details|documents?|draft)"]

# ---------------- INVOICE_QUERY ----------------
_INV_S = [r"\binvoice\b", r"\bbilling\b", r"local\s+charges", r"\bd\s*&\s*d\b", r"total\s+freight",
          r"cancel(?:lation)?\s+invoice", r"missing\s+gr\b", r"\bpayment\b", r"debit\s+note",
          r"\bcharge?s?\b.{0,20}(?:query|question|dispute)?"]
_INV_B = [r"\binvoice\b", r"billing", r"payment", r"remittance", r"outstanding", r"overdue",
          r"local\s+charges", r"detention", r"demurrage", r"debit\s+note", r"credit\s+note",
          r"\bgr\b.{0,20}(?:number|missing|not\s+)", r"total\s+freight", r"charges?\s+(?:are|is|were)"]


_RE_PREFIX = re.compile(r"^\s*(?:re|fw|fwd|aw|sv)\s*[:_\-\]]+\s*", re.I)


def _strip_re(subject: str) -> str:
    """Strip repeated RE_/FW_ prefixes from forwarded chains + underscore-separators."""
    out = subject or ""
    for _ in range(4):
        nxt = _RE_PREFIX.sub("", out)
        if nxt == out:
            break
        out = nxt
    return re.sub(r"_+", " ", out)


def _score(patterns: list[str], subj: str, body: str) -> tuple[int, int]:
    """returns (subject_hits, body_hits)"""
    s = sum(1 for p in patterns if re.search(p, subj, re.I))
    b = sum(1 for p in patterns if re.search(p, body, re.I))
    return s, b


def classify_rules(subject: str, body: str) -> tuple[str, float]:
    subj, txt = _strip_re(subject or ""), body or ""

    # ---- vetoes FIRST: known internal series beat any spammy body cues ----
    # RPA bot notices are operational GENERAL, not billing/spam.
    if re.search(r"^\s*rpa\b", subj, re.I):
        return "GENERAL", 0.85
    # Recurring internal periodicals ("Miss Connection 2 January 2026").
    if re.search(r"miss\s+connection", subj, re.I):
        return "GENERAL", 0.8


    ss, sb = _score(_SPAM_S, subj, txt)
    bs, bb = _score(_SPAM_B, subj, txt)
    strong_spam = [r"weird\s+trick", r"bitcoin", r"investment\s+opportunity",
                   r"guaranteed\s+\d+%\s+returns", r"exclusive\s+offer",
                   r"\d{2,3}%\s+off\b", r"hot\s+singles", r"miss\s+connection",
                   r"storage\s+is\s+full", r"avoid\s+suspension", r"update\s+your\s+account",
                   r"undelivered\s+messages", r"messages\s+in\s+your\s+mailbox",
                   r"confirm\s+your\s+bank\s+details", r"bank\s+details\s+(?:for|are)"
                   r"you\s+(?:have\s+)?won\b", r"claim\s+your\s+prize", r"lottery",
                   r"dear\s+valued\s+customer"]
    if any(re.search(p, subj, re.I) for p in strong_spam):
        return "SPAM", 0.9
    if (ss + bs) >= 2 or (ss >= 1 and bb >= 1):
        return "SPAM", min(0.6 + 0.12 * (ss + bs + bb), 0.95)

    # coded subjects like "SI - MSDUL... - DIRECT(...)" start with SI
    if re.search(r"^\s*si\s*[-–>:]", subj, re.I):
        return "SI_REQUEST", 0.85

    sir_s, sir_b = _score(_SIR_S, subj, txt)
    if sir_s >= 1 or sir_b >= 1:
        return "SI_REQUEST", min(0.6 + 0.12 * (sir_s * 2 + sir_b), 0.92)

    bl_s, bl_b = _score(_BL_S, subj, txt)
    if bl_s >= 1 or (bl_b >= 2):
        return "BL_COMPARISON", min(0.55 + 0.13 * (bl_s * 2 + bl_b), 0.95)
    if bl_b >= 1 and "invoice" not in txt.lower():
        return "BL_COMPARISON", 0.6

    inv_s, inv_b = _score(_INV_S, subj, txt)
    if inv_s >= 1 or inv_b >= 2:
        return "INVOICE_QUERY", min(0.55 + 0.12 * (inv_s * 2 + inv_b), 0.92)

    return "GENERAL", 0.5


CLASSIFY_SYSTEM = """You are an email triage agent for a shipping operations team.
Classify the email into EXACTLY one category:
- BL_COMPARISON: asks to check/verify/confirm a draft Bill of Lading against a Shipping Instruction.
- SI_REQUEST: asks the team to prepare/issue/provide a new Shipping Instruction.
- INVOICE_QUERY: invoices, billing, charges, payments.
- GENERAL: operational updates or general messages.
- SPAM: unsolicited/irrelevant (prizes, phishing, mailbox notices).
Answer with JSON: {"category": "...", "confidence": 0.0-1.0, "reason": "short"}"""


def classify_email(client: LLMClient, email: dict, use_llm: bool | None = None) -> dict:
    """use_llm=None -> follow config.LLM_BATCH (bulk runs); True -> force (interactive)."""
    subject = str(email.get("subject", "") or "")
    body = str(email.get("body", "") or "")
    cat, conf = classify_rules(subject, body)
    out = {"category": cat, "confidence": conf, "engine": "rules", "reason": "keyword cues"}

    eff = (client.available() and config.LLM_BATCH and config.LLM_CLASSIFY) if use_llm is None else (use_llm and client.available())
    if eff:
        data = client.chat_json(CLASSIFY_SYSTEM,
                                f"Subject: {subject}\n\nBody:\n{body[:2500]}",
                                model=client.fast_model)
        if data and data.get("category") in config.CATEGORIES:
            llm_conf = float(data.get("confidence", 0.5) or 0.5)
            if data["category"] != cat:
                out.update(category=data["category"], confidence=max(0.5, llm_conf),
                           engine="llm", reason=str(data.get("reason", ""))[:200],
                           disagreement=True)
            else:
                out.update(confidence=max(conf, llm_conf), engine="llm+rules",
                           reason=str(data.get("reason", ""))[:200])
    return out
