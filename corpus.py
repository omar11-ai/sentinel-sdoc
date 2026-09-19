"""Corpus intelligence — statistics over the VISIBLE corpus only (inbox/ + attachments/).

HARD RULE: never touches ground truth; never produces defect fields.
Alias clusters (same logical party/port written in several forms) are surfaced as
review NOTES only.
"""
from __future__ import annotations

from collections import defaultdict

from normalize import norm_text


def build_alias_clusters(extractions: dict[str, dict]) -> dict:
    """extractions: email_id -> {field: {'display': str}} (SI docs preferred).
    Returns clusters[field] = {norm: set(raw_forms)} for forms with >1 spelling."""
    pools: dict[str, dict[str, set]] = defaultdict(lambda: defaultdict(set))
    for _eid, fields in extractions.items():
        for f, ev in fields.items():
            display = str(ev.get("display", "")).strip()
            if not display:
                continue
            pools[f][norm_text(display)].add(display)
    clusters: dict[str, dict[str, list[str]]] = {}
    for f, by_norm in pools.items():
        multi = {n: sorted(forms) for n, forms in by_norm.items() if len(forms) > 1}
        if multi:
            clusters[f] = multi
    return clusters


def notes_for_email(fields: dict, clusters: dict) -> list[str]:
    """Human-readable notes for the dashboard/review — NEVER defects."""
    notes: list[str] = []
    for f, ev in fields.items():
        display = str(ev.get("display", "")).strip()
        n = norm_text(display)
        forms = clusters.get(f, {}).get(n)
        if forms and len(forms) > 1 and display in forms:
            others = [x for x in forms if x != display]
            if others:
                notes.append(f"corpus-alias[{f}]: '{display}' also appears as "
                             f"{', '.join(chr(39)+o+chr(39) for o in others[:3])} elsewhere in the inbox")
    return notes
