"""Integration: the FreeCAD stage on the units fixture (skipped without FreeCADCmd).

    guix shell --pure -m manifest.scm -m .guix/manifest-cad.scm -- python3 -B -m pytest -q tests/test_cad_stage.py

Checks that the kernel honours each file's declared unit (inch 25.4x, centimetre
10x the millimetre coordinates), that the stage records millimetre bounds with
the 0.001 factor whatever the file says, and that an asset declared in the wrong
unit in the manifest is refused with a message naming both units.
"""
import hashlib
import json
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
FIX = ROOT / "examples" / "units-fixture"
FREECAD = shutil.which("FreeCADCmd")

pytestmark = pytest.mark.skipif(FREECAD is None, reason="FreeCADCmd not on PATH (run in the CAD role)")


def run_stage(project, out, *options):
    r = subprocess.run([FREECAD, str(ROOT / "mechanical_docs" / "cad_mesh.py"), "--pass", str(project), str(out), *options],
                       capture_output=True, text=True, timeout=600)
    receipt = out / "meshes.json"
    log = r.stdout + r.stderr
    assert receipt.is_file(), log[-3000:]
    return json.loads(receipt.read_text()), log


def test_declared_units_scale_the_imported_geometry(tmp_path):
    rec, log = run_stage(FIX, tmp_path / "meshes")
    assert rec["all_checks_passed"], [p["checks"]["problems"] for p in rec["parts"].values()]
    fx = json.loads((FIX / "fixture-receipt.json").read_text())["assets"]
    for pid, p in rec["parts"].items():
        st, me = p["step"], p["mesh"]
        assert st["declared_unit"] == fx[pid]["declared_unit"], pid
        assert st["freecad_unit"] == "mm" and me["frame"]["unit_factor"] == 0.001 and me["frame"]["source_units"] == fx[pid]["declared_unit"]
        assert sorted(st["extent_mm"]) == pytest.approx(sorted(fx[pid]["expected_extent_mm"]), abs=1e-3), pid
        assert st["volume_mm3"] == pytest.approx(fx[pid]["expected_volume_mm3"], rel=1e-6), pid
        assert p["checks"]["declared_extent_deviation_mm"] < 1e-3
        # the GLB is the millimetre geometry scaled to metres: bounds in mm recorded alongside
        assert me["bounds_units"] == "mm"
        assert sorted(b - a for a, b in zip(me["bounds_min"], me["bounds_max"])) == pytest.approx(sorted(fx[pid]["expected_extent_mm"]), abs=0.1)
    pin_in, pin_mm = rec["parts"]["pin-in"]["step"], rec["parts"]["pin-mm"]["step"]
    assert [a / b for a, b in zip(pin_in["extent_mm"], pin_mm["extent_mm"])] == pytest.approx([25.4] * 3)
    assert rec["scene_units"] == "in" and rec["native_up_axis"] == "+Y"
    assert "unit in" in log and "unit cm" in log and "unit mm" in log


def test_wrong_manifest_unit_is_refused(tmp_path):
    """The inch file declared as millimetres: the stage must say so and fail, and
    the extent check must also fire (the manifest extent is then 25.4x off)."""
    proj = tmp_path / "project"
    shutil.copytree(FIX, proj)
    scene = json.loads((proj / "scene.json").read_text())
    for part in scene["parts"]:
        if part["id"] == "pin-in":
            part["asset"]["units"] = "mm"
            part["identifying_dimensions_mm"]["extent"] = [10, 10, 30]
    (proj / "scene.json").write_text(json.dumps(scene))
    rec, log = run_stage(proj, tmp_path / "meshes")
    assert rec["all_checks_passed"] is False
    problems = "\n".join(rec["parts"]["pin-in"]["checks"]["problems"])
    assert "STEP declares 'in' but the manifest says 'mm'" in problems
    assert "manifest extent [10.0, 10.0, 30.0] mm differs from the imported extent [254.0, 254.0, 762.0] mm" in problems
    assert rec["parts"]["base-cm"]["checks"]["passed"] and rec["parts"]["pin-mm"]["checks"]["passed"]
    assert "exit status 1" in log


def test_a_scene_alone_is_meshed_as_a_project_is(tmp_path):
    """A directory with a scene and no inventory, as mechanical-cad's flatten step writes one: the same meshes,
    and a receipt whose inputs are the scene, its assets and the finishes."""
    whole, _ = run_stage(FIX, tmp_path / "meshes-project")
    alone = tmp_path / "scene"
    alone.mkdir()
    shutil.copy(FIX / "scene.json", alone)
    shutil.copytree(FIX / "assets", alone / "assets")
    finishes = {"schema_version": 1, "scene": "scene.json", "finishes": {"brass": {"color": "#c9a13c", "metallic": 1.0, "roughness": 0.35, "opacity": 1.0}},
                "parts": {pid: "brass" for pid in whole["parts"]}}
    (alone / "finishes.json").write_text(json.dumps(finishes))
    rec, log = run_stage(alone, tmp_path / "meshes-scene")
    assert rec["all_checks_passed"] and "exit status 0" in log
    assert sorted(rec["input_hashes"]) == sorted(["scene.json", "finishes.json"] + [f"assets/{p.name}" for p in (FIX / "assets").iterdir()])
    assert {pid: p["mesh"]["sha256"] for pid, p in rec["parts"].items()} == {pid: p["mesh"]["sha256"] for pid, p in whole["parts"].items()}
    # the finishes are no geometry: the scene and the assets hash as they do in the project
    assert all(rec["input_hashes"][k] == whole["input_hashes"][k] for k in rec["input_hashes"] if k != "finishes.json")


def test_the_stage_s_own_options_go_after_a_bare_double_dash(tmp_path):
    """FreeCADCmd reads a dashed option itself, even after --pass, and stops at one it does not know. A bare `--`
    before them hands the script its own: a triangle budget, a deflection."""
    rec, log = run_stage(FIX, tmp_path / "meshes", "--", "--max-triangles", "400", "--linear-deflection", "0.1")
    assert rec["all_checks_passed"] and "exit status 0" in log
    assert rec["tessellation"]["max_triangles_per_part"] == 400 and rec["tessellation"]["linear_deflection"] == 0.1
    base = rec["parts"]["base-cm"]["mesh"]
    assert base["triangles"] <= 400 and len(base["tessellation_attempts"]) > 1       # coarsened until it fitted
    # without the bare `--` FreeCADCmd takes the option for its own, and the stage never runs
    r = subprocess.run([FREECAD, str(ROOT / "mechanical_docs" / "cad_mesh.py"), "--pass", str(FIX), str(tmp_path / "none"), "--max-triangles", "400"],
                       capture_output=True, text=True, timeout=600)
    assert not (tmp_path / "none" / "meshes.json").exists() and "[cad_mesh]" not in r.stdout + r.stderr
    # a bare `--` is no argument of the stage: with the output directory left out it says how it is called
    r = subprocess.run([FREECAD, str(ROOT / "mechanical_docs" / "cad_mesh.py"), "--pass", str(FIX), "--"], capture_output=True, text=True, timeout=600)
    log = r.stdout + r.stderr
    assert "IndexError" not in log and "--pass PROJECT_DIR OUT_DIR" in log and "exit status 1" in log


def with_a_surface_model(tmp_path):
    """The units fixture with its millimetre pin made a model of surfaces: the same faces in a shell that is no
    solid, as a supplier's file sometimes is."""
    proj = tmp_path / "project"
    shutil.copytree(FIX, proj)
    step = proj / "assets" / "pin-mm.step"
    data = step.read_bytes()
    assert data.count(b"MANIFOLD_SOLID_BREP('',#16)") == 1 and data.count(b"ADVANCED_BREP_SHAPE_REPRESENTATION") == 1
    data = (data.replace(b"MANIFOLD_SOLID_BREP('',#16)", b"SHELL_BASED_SURFACE_MODEL('',(#16))")
                .replace(b"ADVANCED_BREP_SHAPE_REPRESENTATION", b"MANIFOLD_SURFACE_SHAPE_REPRESENTATION"))
    step.write_bytes(data)
    scene = json.loads((proj / "scene.json").read_text())
    next(p for p in scene["parts"] if p["id"] == "pin-mm")["asset"]["sha256"] = hashlib.sha256(data).hexdigest()
    (proj / "scene.json").write_text(json.dumps(scene))
    return proj


def test_a_part_without_a_solid_is_a_problem_unless_it_is_named_a_surface_model(tmp_path):
    proj = with_a_surface_model(tmp_path)
    rec, log = run_stage(proj, tmp_path / "strict")
    assert rec["all_checks_passed"] is False and "exit status 1" in log
    assert rec["parts"]["pin-mm"]["checks"]["problems"] == ["no solid in STEP"]
    assert "surface_parts" not in rec and "surface_model" not in rec["parts"]["pin-mm"]["step"]

    solid, _ = run_stage(FIX, tmp_path / "solid")
    rec, log = run_stage(proj, tmp_path / "named", "--", "--surface-parts", "pin-mm")
    assert rec["all_checks_passed"] and "exit status 0" in log, [p["checks"]["problems"] for p in rec["parts"].values()]
    pin = rec["parts"]["pin-mm"]
    assert pin["step"]["surface_model"] is True and pin["step"]["solids"] == 0 and pin["step"]["faces"] == 3
    assert pin["checks"]["volume_deviation"] is None and pin["checks"]["volume"].startswith("not checked: a surface model")
    assert "declared_volume_deviation" not in pin["checks"]
    # the same faces give the same mesh as the solid's, turned the same way: the shell is closed
    was = solid["parts"]["pin-mm"]["mesh"]
    assert (pin["mesh"]["triangles"], pin["mesh"]["bounds_min"], pin["mesh"]["bounds_max"], pin["mesh"]["winding_flipped"]) == \
           (was["triangles"], was["bounds_min"], was["bounds_max"], was["winding_flipped"])
    assert rec["surface_parts"] == ["pin-mm"]
    assert "the volume of the parts named as surface models: pin-mm" in rec["not_checked"]
    assert "a surface model, volume not checked, OK" in log
    assert "all checks passed: True; meshed from their faces as surface models, volume not checked: pin-mm" in log
    # the parts that are not named are held to everything, as before
    assert "surface_model" not in rec["parts"]["base-cm"]["step"] and rec["parts"]["base-cm"]["checks"]["volume_deviation"] < 0.02


def test_the_option_says_what_a_part_is_and_silences_nothing(tmp_path):
    """A part that has a solid and is named a surface model is a problem of its own, and a name that is no part
    of the scene stops the stage."""
    rec, log = run_stage(FIX, tmp_path / "meshes", "--", "--surface-parts", "pin-mm,base-cm")
    assert rec["all_checks_passed"] is False and "exit status 1" in log
    for pid in ("pin-mm", "base-cm"):
        assert rec["parts"][pid]["checks"]["problems"] == ["named a surface model, and its STEP holds 1 solid(s); take it out of --surface-parts"]
    assert rec["parts"]["pin-in"]["checks"]["passed"]
    r = subprocess.run([FREECAD, str(ROOT / "mechanical_docs" / "cad_mesh.py"), "--pass", str(FIX), str(tmp_path / "none"),
                        "--", "--surface-parts", "washer"], capture_output=True, text=True, timeout=600)
    log = r.stdout + r.stderr
    assert not (tmp_path / "none" / "meshes.json").exists()
    assert "--surface-parts: washer is no part of the scene; its parts: " in log and "exit status 1" in log
