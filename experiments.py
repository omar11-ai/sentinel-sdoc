#!/usr/bin/env python3
"""E7 — full-system ablation (blueprint §15/§16). One variable per run.

Legs (each a full 520-email batch run, then scored by the ORGANIZERS'
official bundled scorer against the released answer key — final
verification of a finished system only, never used to iterate):

  deterministic_only   SENTINEL_LLM_BATCH=0          rules classify + rules extract
  hybrid_cls_only      batch LLM ON, extraction OFF   isolates the classifier's share
  hybrid_production    batch LLM ON everywhere        the shipped configuration

The blueprint's "LLM-only" leg is deliberately not run: disabling the
deterministic core removes the system's safety net rather than measuring a
shippable configuration. The shipped axis is hybrid vs deterministic, and the
classifier-only leg shows where the AI contribution actually lives.

Output: artifacts/runs.csv (leg, final, e2e, macroF1, defectF1, reliability, seconds).
"""
from __future__ import annotations

import csv
import importlib.util
import json
import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
GT_PATH = Path(os.environ.get("SENTINEL_DATA_DIR", "/home/user/real/data_v2")) / "ground_truth.json"
RUNNER = ROOT / "experiments_runleg.py"

LEGS = [
    ("deterministic_only", {"SENTINEL_LLM_BATCH": "0"}),
    ("hybrid_cls_only", {"SENTINEL_LLM_BATCH": "1", "SENTINEL_LLM_CLASSIFY": "1",
                         "SENTINEL_LLM_EXTRACT": "0"}),
    ("hybrid_production", {"SENTINEL_LLM_BATCH": "1", "SENTINEL_LLM_CLASSIFY": "1",
                           "SENTINEL_LLM_EXTRACT": "1"}),
]


def official_score(sub: dict) -> dict:
    spec = importlib.util.spec_from_file_location("official_scoring", ROOT / "selfcheck" / "scoring.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    truth = json.loads(GT_PATH.read_text(encoding="utf-8"))
    return mod.score_all(truth, sub)


def main() -> int:
    only = sys.argv[1:] or None
    rows = []
    for name, env in LEGS:
        if only and name not in only:
            continue
        out = Path(f"/tmp/e7_{name}.json")
        e = dict(os.environ)
        e.update(env)
        e.setdefault("SENTINEL_DATA", str(ROOT / "data"))
        t0 = time.time()
        r = subprocess.run([sys.executable, str(RUNNER), str(out)], env=e,
                           capture_output=True, text=True, timeout=3600)
        dt = round(time.time() - t0, 1)
        if r.returncode != 0 or not out.exists():
            print(f"✗ {name}: runner failed\n{r.stderr[-600:]}")
            rows.append({"leg": name, "final": "", "e2e": "", "macroF1": "", "defectF1": "",
                         "reliability": "", "seconds": dt, "error": (r.stderr or "")[-200:]})
            continue
        sub = json.loads(out.read_text(encoding="utf-8"))
        s = official_score(sub)
        row = {
            "leg": name,
            "final": round(float(s.get("final_score", 0.0)), 4),
            "e2e": s.get("end_to_end", {}).get("score", s.get("end_to_end")),
            "macroF1": s.get("stage1", {}).get("macroF1"),
            "defectF1": s.get("stage3", {}).get("defectF1"),
            "reliability": s.get("reliability"),
            "seconds": dt,
            "error": "",
        }
        rows.append(row)
        print(f"✓ {name}: final={row['final']} in {dt}s")

    (ROOT / "artifacts").mkdir(exist_ok=True)
    csv_path = ROOT / "artifacts" / "runs.csv"
    new = not csv_path.exists()
    with csv_path.open("a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["leg", "final", "e2e", "macroF1", "defectF1",
                                          "reliability", "seconds", "error"])
        if new:
            w.writeheader()
        w.writerows(rows)
    print(f"→ appended to {csv_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
