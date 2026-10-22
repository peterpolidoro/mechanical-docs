"""The units fixture: inch, centimetre and millimetre assets in an inch, Y-up scene.

These tests need only Python. tests/test_cad_stage.py runs the FreeCAD stage on
the same fixture when FreeCADCmd is on PATH and checks the kernel reads the inch
file 25.4 times and the centimetre file 10 times larger than the millimetre one.
"""
import json
from pathlib import Path

import pytest

from mechanical_docs import geometry, stepinfo, transforms as T
from mechanical_docs.manifest import load_project
from mechanical_docs.render_settings import load_settings

ROOT = Path(__file__).resolve().parents[1]
FIX = ROOT / "examples" / "units-fixture"


def test_assets_declare_three_different_units():
    assert stepinfo.length_unit(FIX / "assets" / "pin-in.step") == "in"
    assert stepinfo.length_unit(FIX / "assets" / "base-cm.step") == "cm"
    assert stepinfo.length_unit(FIX / "assets" / "pin-mm.step") == "mm"


def test_derived_files_are_the_millimetre_files_with_a_new_unit_context():
    """Only the unit context differs: every CARTESIAN_POINT is byte-identical to the source."""
    src = (ROOT / "examples" / "three-part-fixture" / "assets" / "pin.step").read_text()
    for name in ("pin-in", "pin-mm"):
        text = (FIX / "assets" / f"{name}.step").read_text()
        pts = lambda t: [line for line in t.splitlines() if "CARTESIAN_POINT" in line]  # noqa: E731
        assert pts(text) == pts(src) and len(pts(src)) > 5
    inch = (FIX / "assets" / "pin-in.step").read_text()
    assert "CONVERSION_BASED_UNIT('INCH'" in inch and "LENGTH_MEASURE(25.4)" in inch
    assert "SI_UNIT(.CENTI.,.METRE.)" in (FIX / "assets" / "base-cm.step").read_text()


def test_receipt_hashes_match_the_files():
    rec = json.loads((FIX / "fixture-receipt.json").read_text())
    from mechanical_docs.receipts import sha256_file
    for pid, a in rec["assets"].items():
        assert sha256_file(FIX / a["path"]) == a["sha256"], pid
    for name, h in rec["files"].items():
        if name != "fixture-receipt.json":
            assert sha256_file(FIX / name) == h, name
    assert rec["assets"]["pin-in"]["expected_extent_mm"] == [254.0, 254.0, 762.0]
    assert rec["assets"]["base-cm"]["expected_extent_mm"] == [1000.0, 600.0, 80.0]


def test_scene_loads_in_inches_y_up_with_a_nested_group():
    pr = load_project(FIX)
    sc = pr.scene
    assert sc.units == "in" and sc.native_up_axis == "+Y"
    assert {p.id: p.asset.units for p in sc.parts.values()} == {"pin-in": "in", "base-cm": "cm", "pin-mm": "mm"}
    rec = json.loads((FIX / "fixture-receipt.json").read_text())
    for oid, want in rec["expected_world_translation_in"].items():
        assert T.translation(sc.occurrences[oid].world) == pytest.approx(want), oid
    # the part Z axis (pin axis) ends up along world +Z after the Y-up basis and the Z->Y occurrence rotation
    for oid in ("pin-in-1", "pin-mm-1", "base-cm-1"):
        R = [v for r in sc.occurrences[oid].world[:3] for v in r[:3]]
        assert R == pytest.approx([1, 0, 0, 0, 1, 0, 0, 0, 1], abs=1e-12), oid
    assert sc.occurrences["pin-in-1"].path == ["root", "stand"]
    assert pr.instructions is not None and [s.id for s in pr.instructions.steps] == ["place-base", "stand-inch-pin", "stand-mm-pin"]
    settings, path = load_settings(FIX)
    assert settings["inspection_groups"] == ["stand"] and path is not None


def test_each_unit_converts_once():
    """Mesh bounds in millimetres (what the CAD stage records whatever the file
    declares) times 0.001, placed by an inch-scene pose times 0.0254."""
    pr = load_project(FIX)
    sc = pr.scene
    pin_in = {"bounds_min": [-127, -127, 0], "bounds_max": [127, 127, 762], "frame": {"unit_factor": 0.001}}
    mn, mx = geometry.aabb(geometry.occurrence_corners_m(pin_in, sc.occurrences["pin-in-1"].world, sc.units))
    assert mn == pytest.approx([0.762 - 0.127, -0.127, 0.0508]) and mx == pytest.approx([0.762 + 0.127, 0.127, 0.0508 + 0.762])
    pin_mm = {"bounds_min": [-5, -5, 0], "bounds_max": [5, 5, 30], "frame": {"unit_factor": 0.001}}
    mn, mx = geometry.aabb(geometry.occurrence_corners_m(pin_mm, sc.occurrences["pin-mm-1"].world, sc.units))
    assert mn == pytest.approx([-0.762 - 0.005, -0.005, 0]) and mx == pytest.approx([-0.762 + 0.005, 0.005, 0.03])
    # the inch pin is 25.4 times the millimetre pin in every direction
    assert (762 - 0) / 30 == pytest.approx(25.4) and T.unit_factor("in", "mm") == pytest.approx(25.4)


def test_manifest_unit_mismatch_is_what_the_cad_stage_compares():
    """The manifest alone cannot know the file's unit; stepinfo reads it so the
    CAD stage can refuse an asset declared in the wrong unit."""
    declared = {p.id: stepinfo.length_unit(p.asset.resolved) for p in load_project(FIX).scene.parts.values()}
    manifest = {p.id: p.asset.units for p in load_project(FIX).scene.parts.values()}
    assert declared == manifest
    assert declared["pin-in"] != "mm"
