"""Submission contract (blueprint §13) — the validator rejects every
violation class before anything reaches the organizers' form/scorer."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from schema import build_entry, validate_submission  # noqa: E402

IDS = [f"email_{i:03d}" for i in (1, 2, 3)]


def _ok_entry(**kw):
    base = dict(category="BL_COMPARISON", status="OK", has_defect=False,
                defect_fields=[], review_reason=None)
    base.update(kw)
    return build_entry(**base)


def test_valid_submission_passes():
    sub = {i: _ok_entry() for i in IDS}
    sub["email_002"] = _ok_entry(status="MISMATCH", has_defect=True, defect_fields=["consignee"])
    sub["email_003"] = _ok_entry(status="NEEDS_REVIEW", review_reason="wrong_doc_type — named BL is a Packing List")
    assert validate_submission(sub, IDS) == []


def test_missing_or_extra_ids_flagged():
    sub = {i: _ok_entry() for i in IDS[:2]}
    problems = validate_submission(sub, IDS)
    assert any("missing" in p for p in problems)
    sub["email_999"] = _ok_entry()
    problems = validate_submission(sub, IDS)
    assert any("unknown email_ids" in p for p in problems)


def test_mismatch_requires_defects():
    sub = {IDS[0]: _ok_entry(status="MISMATCH", has_defect=False, defect_fields=[])}
    problems = validate_submission(sub, IDS)
    assert any("MISMATCH requires" in p for p in problems)


def test_ok_rejects_defects():
    sub = {IDS[0]: _ok_entry(has_defect=True, defect_fields=["shipper"])}
    problems = validate_submission(sub, IDS)
    assert any("OK requires" in p for p in problems)


def test_bad_enums_flagged():
    sub = {IDS[0]: _ok_entry(category="SHIPPING", status="MAYBE")}
    problems = validate_submission(sub, IDS)
    assert any("bad category" in p for p in problems)
    assert any("bad status" in p for p in problems)


def test_unknown_defect_field_flagged():
    sub = {IDS[0]: _ok_entry(status="MISMATCH", has_defect=True, defect_fields=["container_no"])}
    problems = validate_submission(sub, IDS)
    assert any("unknown defect_fields" in p for p in problems)
