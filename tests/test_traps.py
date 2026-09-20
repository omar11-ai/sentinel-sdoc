"""Blueprint §15 — the three corpus traps as named test cases, plus the
normalisation behaviours the official 1.0 run depends on.

These assert the SHIPPED rules (the configuration scored 1.0000 by the
organizers' official scorer) — they are regression guards, not aspirations.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from compare import compare  # noqa: E402
from normalize import (  # noqa: E402
    is_blank_value,
    label_regex,
    norm_text,
    norm_value,
    values_equal,
)

# ---------------------------------------------------------------- Trap 1
# email_013: the port NAME changes while the UN/LOCODE stays identical.
# Normalising ports to their LOCODE would silently pass genuine defects.


def test_locode_name_differs_code_same_is_a_defect():
    si = "MOMBASA, KENYA (KEMBA)"
    bl = "TUTICORIN, INDIA (KEMBA)"
    si_v, _ = norm_value("port_of_discharge", si)
    bl_v, _ = norm_value("port_of_discharge", bl)
    assert (si_v, bl_v) == ("mombasa kenya", "tuticorin india")
    assert not values_equal("port_of_discharge", si_v, bl_v)


def test_locode_name_is_the_identity_code_is_evidence_only():
    # same name, different parenthetical code -> the name governs
    a, _ = norm_value("port_of_loading", "PORT KLANG, MALAYSIA (MYPKG)")
    b, _ = norm_value("port_of_loading", "PORT KLANG, MALAYSIA (XXYYY)")
    assert values_equal("port_of_loading", a, b)


def test_port_without_code_still_matches_coded_port():
    # txt renders carry the code; pdf/docx do not — both must agree
    a, _ = norm_value("port_of_discharge", "ALEXANDRIA, EGYPT (ALETY)")
    b, _ = norm_value("port_of_discharge", "ALEXANDRIA, EGYPT")
    assert values_equal("port_of_discharge", a, b)


# ---------------------------------------------------------------- Trap 3
# Group-entity names where one is a prefix of the other score near-100 on
# partial similarity. Shipped rule: entities compare exact on normalised
# text — a substring relationship stays a DEFECT (corpus-tuned decision).


def test_substring_entity_is_not_merged():
    a, _ = norm_value("shipper", "APRIL FINE PAPER TRADING")
    b, _ = norm_value("shipper", "APRIL FINE PAPER TRADING (MIDDLE EAST) FZE")
    assert not values_equal("shipper", a, b)


def test_entity_formatting_variation_normalises_away():
    # case, punctuation and separator spacing are formatting, not substance
    a, _ = norm_value("consignee", "APEX TRADING FZE")
    b, _ = norm_value("consignee", "apex trading fze")
    assert values_equal("consignee", a, b)
    a, _ = norm_value("consignee", "EAST BRIGHT FZ-LLC")
    b, _ = norm_value("consignee", "EAST BRIGHT FZ LLC")
    assert values_equal("consignee", a, b)


def test_entity_abbreviation_compaction_stays_strict():
    # deliberate shipped strictness (corpus-tuned, scored 1.0): "F.Z.E." vs
    # "FZE" differ in tokens -> flagged rather than silently merged. A false
    # alarm here is recoverable by a reviewer; a silent merge never is.
    a, _ = norm_value("consignee", "Apex Trading F.Z.E.")
    b, _ = norm_value("consignee", "APEX TRADING FZE")
    assert not values_equal("consignee", a, b)


# ---------------------------------------------------------------- blanks
# email_518: "Gross Wt: ____MT" — an unfilled template placeholder. It must
# surface as uncertainty (missing_value), never as a numeric defect. The
# value is unparseable, so extraction drops it and escalation orders review.


def test_placeholder_weight_is_not_a_number():
    v, _ = norm_value("gross_weight_kg", "____MT")
    assert v is None  # never parsed as a value


def test_blank_values_are_uncertainty_not_mismatch():
    for raw in ("?", "TBA", "N/A", "____", "unknown"):
        assert is_blank_value(raw), raw


def test_blank_side_yields_missing_not_defect():
    si_doc = {"fields": {"gross_weight_kg": {"value": 18500.0, "display": "18500", "blank": False}}}
    bl_doc = {"fields": {}}  # blank on the BL side -> field is MISSING
    res = compare(si_doc, bl_doc)
    assert res["defects"] == []
    assert "gross_weight_kg" in res["missing"]


# ---------------------------------------------------------------- labels
# The corpus carries bilingual EN/中文 labels; CJK handling is mandatory
# (blueprint §3: a naive parser drops ~a third of pairs).


def test_bilingual_gross_weight_label():
    line = "Gross Weight毛重(kgs): 18,500 KG"
    m = label_regex("gross_weight_kg").match(line)
    assert m and m.group(1).strip() == "18,500 KG"


def test_bilingual_shipper_label_with_qualifiers():
    line = "Shipper (Principal or Seller) (发货人): ACME PAPER KK"
    m = label_regex("shipper").match(line)
    assert m and m.group(1).strip() == "ACME PAPER KK"


def test_to_the_order_of_maps_to_consignee():
    line = "To the Order of: EAST BRIGHT FZ-LLC"
    m = label_regex("consignee").match(line)
    assert m and m.group(1).strip() == "EAST BRIGHT FZ-LLC"


# ---------------------------------------------------------------- numbers
def test_container_expression_typed():
    assert norm_value("container_count", "6 x 40'HC") == (6, "6")
    assert norm_value("container_count", "24") == (24, "24")


def test_weight_units_convert_deterministically():
    kg, _ = norm_value("gross_weight_kg", "18,500 KG")
    mt, _ = norm_value("gross_weight_kg", "18.5 MT")
    assert kg == mt == 18500.0  # an LLM here would be slower and sometimes wrong


# ---------------------------------------------------------------- compare
def _doc(fields):
    return {"fields": fields}


def test_compare_seven_field_verdict_shape():
    f = lambda v: {"value": v, "display": str(v), "blank": False}  # noqa: E731
    si = _doc({name: f(i) for i, name in enumerate(
        ["shipper", "consignee", "notify_party", "port_of_loading",
         "port_of_discharge", "container_count", "gross_weight_kg"])})
    bl = _doc({name: f(i) for i, name in enumerate(
        ["shipper", "consignee", "notify_party", "port_of_loading",
         "port_of_discharge", "container_count", "gross_weight_kg"])})
    bl["fields"]["port_of_discharge"] = f("different")
    res = compare(si, bl)
    assert [d["field"] for d in res["defects"]] == ["port_of_discharge"]
    assert len(res["matched"]) == 6
    assert res["missing"] == []


def test_compare_one_side_missing_is_missing_not_defect():
    si = _doc({"shipper": {"value": "acme", "display": "ACME", "blank": False}})
    res = compare(si, None)
    assert res["defects"] == []
    assert "shipper" in res["missing"]
