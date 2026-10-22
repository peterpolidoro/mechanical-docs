"""Integration: the FreeCAD stage on the units fixture (skipped without FreeCADCmd).

    guix shell --pure -m manifest.scm -m .guix/manifest-cad.scm -- python3 -B -m pytest -q tests/test_cad_stage.py

Checks that the kernel honours each file's declared unit (inch 25.4x, centimetre
10x the millimetre coordinates), that the stage records millimetre bounds with
the 0.001 factor whatever the file says, and that an asset declared in the wrong
unit in the manifest is refused with a message naming both units.
"""
import json
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
FIX = ROOT / "examples" / "units-fixture"
FREECAD = shutil.which("FreeCADCmd")

pytestmark = pytest.mark.skipif(FREECAD is None, reason="FreeCADCmd not on PATH (run in the CAD role)")


def run_stage(project, out):
    r = subprocess.run([FREECAD, str(ROOT / "mechanical_docs" / "cad_mesh.py"), "--pass", str(project), str(out)], capture_output=True, text=True, timeout=600)
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
