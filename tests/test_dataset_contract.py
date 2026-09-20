"""Dataset-level regression — the deterministic batch run over the full
participant inbox must keep reproducing the officially scored verdicts on
the named corpus cases (skipped automatically when the dataset dir or the
data dir is absent, e.g. on a fresh clone without SENTINEL_DATA)."""
from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = Path(os.environ.get("SENTINEL_DATA", str(ROOT / "data")))

if not (DATA / "inbox").exists():
    import pytest

    pytest.skip(f"dataset not present at {DATA}", allow_module_level=True)

os.environ.setdefault("SENTINEL_LLM_BATCH", "0")  # deterministic leg — fast and quota-free
sys.path.insert(0, str(ROOT))

from loader import Inbox  # noqa: E402
from pipeline import run  # noqa: E402


def test_full_run_official_verdicts():
    r = run(Inbox())
    emails = {e["email_id"]: e for e in r["emails"]}
    assert len(emails) == 520

    # email_013 — the LOCODE trap, cleanest form: one differing field
    e13 = emails["email_013"]
    assert e13["status"] == "MISMATCH"
    assert e13["defect_fields"] == ["port_of_discharge"]

    # email_518 — the placeholder weight escalates as missing_value
    e518 = emails["email_518"]
    assert e518["status"] == "NEEDS_REVIEW"
    assert (e518["review_reason"] or "").startswith("missing_value")

    # email_502 — a Packing List named as a BL → wrong_doc_type
    e502 = emails["email_502"]
    assert e502["status"] == "NEEDS_REVIEW"
    assert (e502["review_reason"] or "").startswith("wrong_doc_type")

    # the submission object stays in lockstep with the email rows
    sub = r["submission"]
    assert len(sub) == 520
    assert sub["email_013"]["status"] == "MISMATCH"
    assert sub["email_518"]["status"] == "NEEDS_REVIEW"
