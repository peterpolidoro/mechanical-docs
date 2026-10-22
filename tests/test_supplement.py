"""supplement.json (items not modelled in CAD) and the inventory's stock record.

Decisions from the Linux CAD agent, 2026-10-22: every field explicit, quantities
integer or null (never coerced to 0), `included_with` a discriminated object or
null, `intended_configuration_confirmed` an explicit boolean, one stock
authority (`on_hand_each` with `counted_by`/`counted_date`), family rows
without integer quantities, status rules, `attaches_to` validated against the
scene with empty lists allowed.
"""
import json

import pytest

from mechanical_docs.manifest import SUPPLEMENT_ITEM_FIELDS, ManifestError, load_project

FIELDS = list(SUPPLEMENT_ITEM_FIELDS)


def _problems(project):
    with pytest.raises(ManifestError) as ei:
        load_project(project.dir)
    return "\n".join(ei.value.problems)


def _edit_row(project, index, fn):
    def f(d):
        fn(d["items"][index])
    project.edit("supplement.json", f)


def test_fixture_supplement_loads(fixture_dir):
    pr = load_project(fixture_dir)
    sup = pr.supplement
    assert sup is not None and [it.item_id for it in sup.items] == ["pin-retainer", "pin-spacer", "pin-label"]
    fam, sku, new = sup.items
    # a family row: unknown quantities stay None (not 0), a kit included_with is free text
    assert fam.item_kind == "family" and fam.status == "candidate_requires_review"
    assert fam.confirmed_required_each is None and fam.on_hand_each is None and fam.on_order_each is None
    assert fam.included_with == {"kind": "kit", "name": "synthetic pin kit"} and fam.attaches_to == ["pin-pair"]
    assert fam.intended_configuration_confirmed is False
    # a specified SKU: integers, an explicit 0 on order, a scene-part included_with, a counted stock record
    assert sku.item_kind == "sku" and sku.status == "specified"
    assert sku.confirmed_required_each == 2 and sku.on_hand_each == 3 and sku.on_order_each == 0
    assert sku.counted_by == "fixture author" and sku.counted_date == "2026-10-22" and sku.stock_location == "synthetic drawer A"
    assert sku.included_with == {"kind": "scene_part", "id": "base"} and sku.attaches_to == ["pin-a", "pin-b"]
    assert sku.supplier_part_number == "FIXTURE-SPACER-10" and sku.supplier_specification_verified is True
    assert sku.unit_cost == 0.1 and sku.currency == "USD"
    # a new-design row may be unplaced
    assert new.scope == "new_design" and new.attaches_to == [] and new.included_with is None
    assert "supplement.json" in pr.input_hashes()
    assert set(sku.as_dict()) == set(FIELDS) and len(FIELDS) == 23


def test_supplement_is_optional(project_copy):
    (project_copy.dir / "supplement.json").unlink()
    pr = load_project(project_copy.dir)
    assert pr.supplement is None and "supplement.json" not in pr.input_hashes()


def test_bare_string_included_with_rejected(project_copy):
    _edit_row(project_copy, 0, lambda r: r.__setitem__("included_with", "synthetic pin kit"))
    p = _problems(project_copy)
    assert "included_with: expected null or an object" in p and "a bare string is not accepted" in p


def test_included_with_scene_part_must_exist_and_kit_needs_a_name(project_copy):
    _edit_row(project_copy, 1, lambda r: r.__setitem__("included_with", {"kind": "scene_part", "id": "washer"}))
    assert "included_with.id: unknown scene part 'washer'" in _problems(project_copy)
    _edit_row(project_copy, 1, lambda r: r.__setitem__("included_with", {"kind": "kit", "name": ""}))
    assert "included_with.name: expected a non-empty kit name" in _problems(project_copy)
    _edit_row(project_copy, 1, lambda r: r.__setitem__("included_with", {"kind": "kit", "name": "x", "id": "base"}))
    assert "included_with: unsupported field(s) ['id']" in _problems(project_copy)
    _edit_row(project_copy, 1, lambda r: r.__setitem__("included_with", {"kind": "box", "name": "x"}))
    assert "included_with.kind: expected one of" in _problems(project_copy)


def test_quantities_are_never_coerced_to_zero(project_copy):
    # a string, an empty string, a float and a boolean are all rejected; nothing becomes 0
    for bad in ("0", "", 2.0, False):
        _edit_row(project_copy, 1, lambda r, bad=bad: r.__setitem__("confirmed_required_each", bad))
        p = _problems(project_copy)
        assert "confirmed_required_each: expected null (unknown) or a non-negative integer" in p and "never coerced to 0" in p, bad
    # an absent quantity field is an error, not 0 and not null
    def drop(r):
        del r["on_order_each"]
    _edit_row(project_copy, 1, drop)
    p = _problems(project_copy)
    assert "missing field(s) ['on_order_each']" in p
    # null and 0 load as different values
    pr = load_project(FIXTURE_DIR())
    assert pr.supplement.items[0].on_hand_each is None and pr.supplement.items[1].on_order_each == 0


def test_attaches_to_ids_must_exist(project_copy):
    _edit_row(project_copy, 0, lambda r: r.__setitem__("attaches_to", ["pin-pair", "nowhere"]))
    assert "attaches_to: 'nowhere' is not an assembly or occurrence id in the scene" in _problems(project_copy)
    _edit_row(project_copy, 0, lambda r: r.__setitem__("attaches_to", ["pin-a", "pin-a"]))
    assert "attaches_to: 'pin-a' listed twice" in _problems(project_copy)
    _edit_row(project_copy, 0, lambda r: r.__setitem__("attaches_to", "pin-pair"))
    assert "attaches_to: expected a list" in _problems(project_copy)


def test_family_cannot_carry_integer_quantities(project_copy):
    _edit_row(project_copy, 0, lambda r: r.__setitem__("confirmed_required_each", 4))
    assert "a family row must have confirmed_required_each null" in _problems(project_copy)
    _edit_row(project_copy, 0, lambda r: r.__setitem__("confirmed_required_each", None) or r.__setitem__("on_order_each", 1))
    assert "a family row cannot be on order" in _problems(project_copy)
    _edit_row(project_copy, 0, lambda r: r.__setitem__("on_order_each", None) or r.__setitem__("candidate_item_family", None))
    assert "candidate_item_family: required for a family row" in _problems(project_copy)


def test_count_requires_counted_by_and_date(project_copy):
    _edit_row(project_copy, 1, lambda r: r.__setitem__("counted_by", None))
    assert "counted_by: required when on_hand_each is a number" in _problems(project_copy)
    _edit_row(project_copy, 1, lambda r: r.__setitem__("counted_by", "x") or r.__setitem__("counted_date", "22/10/2026"))
    assert "counted_date: expected an ISO date (YYYY-MM-DD)" in _problems(project_copy)
    # attribution without a count is inconsistent too
    _edit_row(project_copy, 0, lambda r: r.__setitem__("counted_by", "someone"))
    assert "counted_by/counted_date without an on_hand_each count" in _problems(project_copy)


def test_explicit_booleans_required(project_copy):
    _edit_row(project_copy, 0, lambda r: r.__setitem__("intended_configuration_confirmed", "no"))
    assert "intended_configuration_confirmed: expected an explicit true/false, got 'no'" in _problems(project_copy)
    _edit_row(project_copy, 0, lambda r: r.__setitem__("intended_configuration_confirmed", None))
    assert "intended_configuration_confirmed: expected an explicit true/false, got None" in _problems(project_copy)
    _edit_row(project_copy, 0, lambda r: r.__setitem__("intended_configuration_confirmed", False) or r.__setitem__("supplier_specification_verified", "yes"))
    assert "supplier_specification_verified: expected an explicit true/false" in _problems(project_copy)


def test_status_rules(project_copy):
    _edit_row(project_copy, 0, lambda r: r.__setitem__("status", "covered") or r.__setitem__("included_with", None))
    assert "status 'covered' requires a non-null included_with" in _problems(project_copy)
    _edit_row(project_copy, 0, lambda r: r.__setitem__("status", "specified") or r.__setitem__("included_with", {"kind": "kit", "name": "k"}))
    p = _problems(project_copy)
    assert "status 'specified' requires item_kind 'sku'" in p and "requires supplier_part_number" in p and "requires supplier_specification_verified true" in p
    _edit_row(project_copy, 1, lambda r: r.__setitem__("status", "ordered"))
    assert "status: expected one of" in _problems(project_copy)
    _edit_row(project_copy, 1, lambda r: r.__setitem__("status", "candidate_requires_review") or r.__setitem__("supplier_part_number", None))
    assert "supplier_specification_verified true without a supplier_part_number" in _problems(project_copy)
    _edit_row(project_copy, 1, lambda r: r.__setitem__("supplier_part_number", "X") or r.__setitem__("currency", None))
    assert "currency: required when unit_cost is given" in _problems(project_copy)


def test_unknown_field_duplicate_id_and_schema_version(project_copy):
    _edit_row(project_copy, 0, lambda r: r.__setitem__("colour", "red"))
    assert "unsupported field(s) ['colour']" in _problems(project_copy)
    _edit_row(project_copy, 0, lambda r: r.pop("colour") and r.__setitem__("item_id", "pin-spacer"))
    assert "duplicate item_id 'pin-spacer'" in _problems(project_copy)
    project_copy.edit("supplement.json", lambda d: d.__setitem__("schema_version", "1"))
    assert "schema_version must be the integer 1, got '1'" in _problems(project_copy)
    project_copy.edit("supplement.json", lambda d: d.__setitem__("schema_version", 1) or d.__setitem__("scene", "other.json"))
    assert "supplement.scene: 'other.json' is not the loaded scene" in _problems(project_copy)
    project_copy.edit("supplement.json", lambda d: d.__setitem__("scene", "scene.json") or d.__setitem__("notes", "x"))
    assert "supplement: unsupported field(s) ['notes']" in _problems(project_copy)


def test_all_supplement_problems_reported_together(project_copy):
    def f(r):
        r["included_with"] = "kit"
        r["attaches_to"] = ["nowhere"]
        r["on_hand_each"] = 2
    _edit_row(project_copy, 0, f)
    p = _problems(project_copy)
    assert p.count("\n") >= 2 and "bare string" in p and "'nowhere'" in p and "counted_by: required" in p


# ------------------------------------------------------------ inventory stock record

def test_inventory_stock_record(project_copy):
    def f(d):
        d["items"][0].update({"on_hand_each": 1, "counted_by": "fixture author", "counted_date": "2026-10-22", "stock_location": "shelf 3",
                              "intended_configuration_confirmed": True})
        del d["items"][0]["counted"]
    project_copy.edit("inventory.json", f)
    pr = load_project(project_copy.dir)
    base, pin = pr.inventory.items
    assert base.extended and base.on_hand_each == 1 and base.counted_by == "fixture author" and base.stock_location == "shelf 3"
    assert base.intended_configuration_confirmed is True
    assert not pin.extended and pin.on_hand_each is None and pin.intended_configuration_confirmed is None
    assert base.counted is None     # the paper box is never data


def test_inventory_stock_record_rules(project_copy):
    project_copy.edit("inventory.json", lambda d: d["items"][0].update({"on_hand_each": 1, "intended_configuration_confirmed": True}))
    p = _problems(project_copy)
    assert "counted_by: required when on_hand_each is a number" in p and "counted_date: required" in p
    project_copy.edit("inventory.json", lambda d: d["items"][0].update({"on_hand_each": None, "counted_by": None, "stock_location": "shelf 3"}) or d["items"][0].pop("intended_configuration_confirmed"))
    assert "missing field 'intended_configuration_confirmed' (an explicit true/false is required)" in _problems(project_copy)
    project_copy.edit("inventory.json", lambda d: d["items"][0].update({"on_hand_each": "3", "intended_configuration_confirmed": False}))
    assert "on_hand_each: expected null (unknown) or a non-negative integer, got '3'" in _problems(project_copy)


def test_counted_is_paper_only(project_copy):
    """The deprecated `counted` field is accepted only as null; a number must go to on_hand_each."""
    project_copy.edit("inventory.json", lambda d: d["items"][1].__setitem__("counted", 2))
    p = _problems(project_copy)
    assert "counted: the counted box is paper only and not a data field" in p and "on_hand_each" in p
    project_copy.edit("inventory.json", lambda d: [row.pop("counted") for row in d["items"]])
    assert load_project(project_copy.dir).inventory.items[1].counted is None


def test_inventory_notes_reach_the_status_block(project_copy, tmp_path):
    """Project-authored sentences in inventory.json print on the status block verbatim; nothing is authored here."""
    project_copy.edit("inventory.json", lambda d: d.__setitem__("notes", ["The tank is to be replaced in the modified build (stated 2026-10-22; not a designer confirmation)."]))
    pr = load_project(project_copy.dir)
    assert pr.inventory.notes == ["The tank is to be replaced in the modified build (stated 2026-10-22; not a designer confirmation)."]
    project_copy.edit("inventory.json", lambda d: d.__setitem__("notes", ["ok", ""]))
    assert "inventory.notes: expected a list of non-empty strings" in _problems(project_copy)


def test_inventory_template_has_no_count_field(fixture_dir):
    from mechanical_docs.manifest import inventory_template, load_scene
    t = inventory_template(load_scene(fixture_dir / "scene.json"))
    assert t["items"] == [{"part_id": "base", "required": 1, "unit": "each"}, {"part_id": "pin", "required": 2, "unit": "each"}]
    assert "stock" in t["status"]


def FIXTURE_DIR():
    from pathlib import Path
    return Path(__file__).resolve().parents[1] / "examples" / "three-part-fixture"
