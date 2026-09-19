"""Smoke test — full pipeline on the mock dataset + validator + planted-case assertions."""
from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
os.environ.setdefault("SENTINEL_DATA", str(Path(__file__).resolve().parents[1] / "mock_data"))

import config  # noqa: E402
from loader import Inbox  # noqa: E402
from pipeline import run  # noqa: E402
from schema import validate_submission  # noqa: E402
from mock_data.gen_mock import (  # noqa: E402
    PLANNED_MATCH_IDS, PLANNED_MISMATCH_IDS, PLANNED_REVIEW_IDS,
)


def main() -> int:
    assert config.FIELDS and len(config.FIELDS) == 7
    inbox = Inbox()
    res = run(inbox)
    s = res["summary"]
    sub = res["submission"]
    by_id = {r["email_id"]: r for r in res["emails"]}

    print(f"total={s['total']} ok={s['ok']} mismatch={s['mismatch']} "
          f"review={s['needs_review']} elapsed={res['elapsed_s']}s")

    # 1) every email present exactly once + validator passes
    problems = validate_submission(sub, inbox.all_ids(), inbox.sample_submission())
    assert not problems, "validator failed:\n" + "\n".join(problems)

    # 2) planted mismatches caught
    caught = [eid for eid in PLANNED_MISMATCH_IDS if by_id[eid]["status"] == "MISMATCH"]
    print(f"planted mismatches caught: {len(caught)}/{len(PLANNED_MISMATCH_IDS)}")
    for eid in PLANNED_MISMATCH_IDS:
        r = by_id[eid]
        assert r["status"] == "MISMATCH", f"missed planted mismatch {eid}: {r['status']}"

    # 3) planted matches stay clean
    for eid in PLANNED_MATCH_IDS:
        r = by_id[eid]
        assert r["status"] == "OK", f"false alarm on {eid}: {r['status']} {r['defect_fields']}"

    # 4) damaged/low-coverage escalate with reasons
    for eid in PLANNED_REVIEW_IDS:
        r = by_id[eid]
        assert r["status"] == "NEEDS_REVIEW", f"{eid} should escalate, got {r['status']}"
        assert r["review_reason"], f"{eid} escalated without a reason"
    print(f"escalations with reasons: {len(PLANNED_REVIEW_IDS)}/{len(PLANNED_REVIEW_IDS)}")

    # 5) spam corner
    spam = [r for r in res["emails"] if r["category"] == "SPAM"]
    assert len(spam) == 4, f"expected 4 spam, got {len(spam)}"

    # 6) no escalated case invents defects (default policy)
    for eid in PLANNED_REVIEW_IDS:
        r = by_id[eid]
        assert not r["defect_fields"], f"{eid} escalated but emitted defects {r['defect_fields']}"

    # 7) corpus notes never create defects (spot check flag presence)
    assert "corpus_notes" in res["emails"][0]

    # 8) canonical review reasons on escalations
    CANON = {"wrong_doc_type", "missing_attachment", "unreadable", "missing_value"}
    for r in res["emails"]:
        if r["status"] == "NEEDS_REVIEW":
            first = (r["review_reason"] or "").split(" — ")[0]
            assert first in CANON, f"{r['email_id']}: non-canonical reason {first!r}"

    # 9) schema consistency v2
    for eid, entry in sub.items():
        if entry["status"] == "OK":
            assert not entry["has_defect"] and not entry["defect_fields"]
        if entry["status"] == "NEEDS_REVIEW":
            assert entry["review_reason"] and not entry["has_defect"]

    print("SMOKE TEST: ALL PASS ✅")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
