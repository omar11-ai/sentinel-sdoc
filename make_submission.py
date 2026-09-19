#!/usr/bin/env python3
"""CLI: run the SENTINEL pipeline and write submission.json (validated)."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import config  # noqa: E402
from loader import Inbox  # noqa: E402
from pipeline import run  # noqa: E402
from schema import validate_submission  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description="SENTINEL — build submission.json")
    ap.add_argument("--data", default=str(config.DATA_DIR), help="data folder (contains inbox/ attachments/) or server URL")
    ap.add_argument("--out", default="submission.json", help="output path")
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args()

    inbox = Inbox(args.data)
    res = run(inbox)
    sub = res["submission"]
    sample = inbox.sample_submission()
    problems = validate_submission(sub, inbox.all_ids(), sample)

    Path(args.out).write_text(json.dumps(sub, ensure_ascii=False, indent=2), encoding="utf-8")
    if not args.quiet:
        s = res["summary"]
        print(f"emails: {s['total']}  |  OK {s['ok']}  MISMATCH {s['mismatch']}  "
              f"NEEDS_REVIEW {s['needs_review']}  |  elapsed {res['elapsed_s']}s")
        print(f"submission -> {args.out}")
        if problems:
            print("VALIDATION ISSUES:")
            for p in problems:
                print(" -", p)
            return 2
        print("validation: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
