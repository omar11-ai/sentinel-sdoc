"""L4 Comparison v2 — only compare fields present & non-blank on BOTH sides."""
from __future__ import annotations

import config
from normalize import values_equal


def compare(si_doc: dict, bl_doc: dict) -> dict:
    if not si_doc or not bl_doc:
        return {"defects": [], "missing": list(config.FIELDS), "matched": []}
    sf, bf = si_doc["fields"], bl_doc["fields"]
    defects, missing, matched = [], [], []
    for f in config.FIELDS:
        s, b = sf.get(f), bf.get(f)
        if not s or not b or s.get("blank") or b.get("blank"):
            if s or b:
                missing.append(f)
            else:
                missing.append(f)  # absent on both sides too
            continue
        si_v, bl_v = s["value"], b["value"]
        if values_equal(f, si_v, bl_v):
            matched.append(f)
        else:
            defects.append({
                "field": f,
                "si": s["display"], "bl": b["display"],
                "si_line": s.get("line", ""), "bl_line": b.get("line", ""),
            })
    return {"defects": defects, "missing": missing, "matched": matched}
