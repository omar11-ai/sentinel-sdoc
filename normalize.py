"""Normalization v2 — real-data label synonyms, qualifiers, values like "1 x 40'HC"."""
from __future__ import annotations

import re

# Optional qualifier right after the label: "Port of Loading (POL):", "Gross Weight (KG):"
_QUAL = r"(?:(?:\s*\([^)]{0,30}\))|(?:\s*[/|][A-Za-z\u4e00-\u9fff][^:]{0,32})){0,3}"

LABELS: dict[str, list[str]] = {
    "shipper": [
        r"shipper(?:\s*/\s*exporter)?", r"exporter",
    ],
    "consignee": [
        r"consignee", r"to\s+the\s+order\s+of", r"importer",
    ],
    "notify_party": [
        r"notify\s+party(?:\s+name)?", r"notify\s+address", r"notified\s+party", r"notify",
    ],
    "port_of_loading": [
        r"port\s+of\s+loading", r"load(?:ing)?\s+port", r"port\s+of\s+shipment",
        r"shipment\s+port", r"\bpol\b",
    ],
    "port_of_discharge": [
        r"port\s+of\s+discharge", r"discharge\s+port", r"port\s+of\s+delivery", r"\bpod\b",
    ],
    "container_count": [
        r"container\s+count", r"(?:no\.?|number|total|qty|quantity)\s+of\s+containers(?:\s+or\s+packages)?",
        r"container\s+(?:qty|quantity|total|count)", r"total\s+containers", r"containers",
    ],
    "gross_weight_kg": [
        r"gross\s+(?:weight|wt|mass)[\u4e00-\u9fff\u25a0\u25a1\u25a2]{0,6}\s*(?:\(\s*kgs?\s*\))?",
        r"\bgw\b\s*(?:\(\s*kgs?\s*\))?",
        r"weight\s*\(?\s*kgs?\s*\)?",
        r"gross\s+weight\s+in\s+kgs?",
    ],
}

# values that mean "field present but blank" -> uncertainty, not a mismatch
_BLANK_VALUE = re.compile(r"^(?:\?+|_+|tba|tbd|n/?a|nil|not\s+available|unknown)[\s.?!]*$", re.I)


def label_regex(field: str) -> re.Pattern:
    alts = "|".join(f"(?:{p})" for p in LABELS[field])
    return re.compile(rf"^\s*(?:{alts}){_QUAL}\s*[:：]\s*(.+?)\s*$", re.IGNORECASE)


def blank_label_regex(field: str) -> re.Pattern:
    """A label whose value is EMPTY ("SHIPPER:" / "SHIPPER:  ") — a blank, not an absence."""
    alts = "|".join(f"(?:{p})" for p in LABELS[field])
    return re.compile(rf"^\s*(?:{alts}){_QUAL}\s*[:：]\s*$", re.IGNORECASE)


def label_only_regex(fields: list[str] | None = None) -> re.Pattern:
    """A line that is JUST a field label (PDF block style: value on the next line)."""
    fs = fields or list(LABELS.keys())
    alts = "|".join(f"(?:{p})" for f in fs for p in LABELS[f])
    return re.compile(rf"^\s*(?:{alts}){_QUAL}\s*[:：]?\s*$", re.IGNORECASE)


def is_blank_value(raw: str) -> bool:
    return bool(_BLANK_VALUE.match(raw.strip()))


def norm_text(value: str) -> str:
    s = value.lower().strip()
    s = re.sub(r"[^\w\s]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


_NUM = re.compile(r"[-+]?\d[\d,\.]*")


_PORT_CODE = re.compile(r"\s*\([A-Z]{2,6}\)\s*$")


def norm_value(field: str, raw: str):
    """Returns (typed_value, display) | ("BLANK", raw) | (None, raw) if unparseable."""
    raw = raw.strip()
    if field in ("port_of_loading", "port_of_discharge"):
        # txt renders carry a trailing UN/LOCODE "(MYPKG)"; pdf/docx do not.
        raw = _PORT_CODE.sub("", raw).strip() or raw
    if is_blank_value(raw):
        return "BLANK", raw
    if field == "container_count":
        # "1 x 40'HC", "3", "Total 4 containers" -> leading integer
        m = re.match(r"^\s*(\d{1,4})\b", raw)
        if not m:
            return None, raw
        n = int(m.group(1))
        return n, str(n)
    if field == "gross_weight_kg":
        m = _NUM.search(raw)
        if not m:
            return None, raw
        try:
            w = float(m.group(0).replace(",", ""))
        except ValueError:
            return None, raw
        low = raw.lower()
        if re.search(r"\b(mt|tons?|tonnes?)\b", low):
            w *= 1000.0
        display = str(int(w)) if w == int(w) else str(w)
        return w, display
    # text fields: normalize case/punct, strip trailing UN/LOCODE "(MYPKG)" for display parity
    t = norm_text(raw)
    if not t:
        return None, raw
    return t, raw.strip()


def values_equal(field: str, a, b) -> bool:
    if a is None or b is None or a == "BLANK" or b == "BLANK":
        return False
    if field in ("container_count", "gross_weight_kg"):
        return abs(float(a) - float(b)) < 1e-6
    return a == b
