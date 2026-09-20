#!/usr/bin/env python3
"""One E7 leg: run the full pipeline in this process env, dump the submission."""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from loader import Inbox  # noqa: E402
from pipeline import run  # noqa: E402

out = Path(sys.argv[1])
r = run(Inbox())
out.write_text(json.dumps(r["submission"], ensure_ascii=False, allow_nan=False), encoding="utf-8")
print(f"leg done: {len(r['submission'])} entries in {r['elapsed_s']}s")
