"""Generate a tiny synthetic STEP/manifest fixture; run using FreeCADCmd."""

from collections import Counter
import hashlib
import json
import math
from pathlib import Path

import FreeCAD as App
import Part


ROOT = Path(__file__).resolve().parent
ASSETS = ROOT / "assets"
ASSETS.mkdir(exist_ok=True)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def transform(x=0, y=0, z=0):
    return [[1, 0, 0, x], [0, 1, 0, y], [0, 0, 1, z], [0, 0, 0, 1]]


base = Part.makeBox(100, 60, 8, App.Vector(-50, -30, 0))
for x in (-25, 25):
    base = base.cut(Part.makeCylinder(5.25, 8, App.Vector(x, 0, 0)))
pin = Part.makeCylinder(5, 30)
expected = {
    "base": {"extent": [100, 60, 8], "volume": 100 * 60 * 8 - 2 * math.pi * 5.25**2 * 8},
    "pin": {"extent": [10, 10, 30], "volume": math.pi * 5**2 * 30},
}
geometry = {}
shapes = {}
doc = App.newDocument("MechanicalDocsSyntheticFixture")
try:
    for name, shape in [("base", base), ("pin", pin)]:
        if not shape.isValid() or len(shape.Solids) != 1:
            raise RuntimeError(f"Invalid fixture source: {name}")
        obj = doc.addObject("Part::Feature", name.title())
        obj.Label = f"Synthetic {name} — documentation fixture only"
        obj.Shape = shape
        doc.recompute()
        path = ASSETS / f"{name}.step"
        Part.export([obj], str(path))
        imported = Part.read(str(path))
        bb = imported.BoundBox
        extent = [bb.XLength, bb.YLength, bb.ZLength]
        if not imported.isValid() or len(imported.Solids) != 1:
            raise RuntimeError(f"Invalid exported/reimported shape: {name}")
        if any(abs(a - b) > 1e-7 for a, b in zip(extent, expected[name]["extent"])):
            raise RuntimeError(f"Wrong dimensions: {name}")
        if abs(imported.Volume - expected[name]["volume"]) > 1e-5:
            raise RuntimeError(f"Wrong volume: {name}")
        shapes[name] = imported
        geometry[name] = {
            "path": f"assets/{name}.step", "sha256": digest(path), "bytes": path.stat().st_size,
            "valid": True, "solids": 1, "extent_mm": extent, "volume_mm3": imported.Volume,
        }
finally:
    App.closeDocument(doc.Name)

scene = {
    "schema_version": "draft-1", "id": "three-part-fixture",
    "title": "Synthetic base and two pins", "units": "mm",
    "coordinate_system": {"handedness": "right", "up_axis": "+Z", "origin": "base bottom center"},
    "source": {"kind": "synthetic", "generator": "generate_fixture.py", "qualification": "fixture only"},
    "parts": [
        {"id": "base", "name": "Base", "asset": {"path": "assets/base.step", "format": "step", "units": "mm", "sha256": geometry["base"]["sha256"]},
         "identifying_dimensions_mm": {"width": 100, "depth": 60, "height": 8, "hole_diameter": 10.5}},
        {"id": "pin", "name": "Pin", "asset": {"path": "assets/pin.step", "format": "step", "units": "mm", "sha256": geometry["pin"]["sha256"]},
         "identifying_dimensions_mm": {"diameter": 10, "length": 30}},
    ],
    "assemblies": [
        {"id": "root", "parent_id": None, "transform": transform()},
        {"id": "pin-pair", "parent_id": "root", "transform": transform(10)},
    ],
    "occurrences": [
        {"id": "base-1", "part_id": "base", "parent_id": "root", "transform": transform()},
        {"id": "pin-a", "part_id": "pin", "parent_id": "pin-pair", "transform": transform(-35)},
        {"id": "pin-b", "part_id": "pin", "parent_id": "pin-pair", "transform": transform(15)},
    ],
}
(ROOT / "scene.json").write_text(json.dumps(scene, indent=2) + "\n")

# Check the known fixture hierarchy and final arrangement, not arbitrary manifests.
world_x = [10 + item["transform"][0][3] for item in scene["occurrences"] if item["part_id"] == "pin"]
if world_x != [-25, 25]:
    raise RuntimeError("Fixture parent transform no longer places the pins in their holes")
overlaps = []
for x in world_x:
    placed = shapes["pin"].copy()
    placed.translate(App.Vector(x, 0, 0))
    overlaps.append(shapes["base"].common(placed).Volume)
if any(abs(v) > 1e-7 for v in overlaps):
    raise RuntimeError("A fixture pin overlaps the base in its final pose")

inventory = json.loads((ROOT / "inventory.json").read_text())
required = Counter(item["part_id"] for item in scene["occurrences"])
if {row["part_id"]: row["required"] for row in inventory["items"]} != dict(required):
    raise RuntimeError("Fixture inventory does not match occurrences")
instructions = json.loads((ROOT / "instructions.json").read_text())
seen_steps, installed = set(), []
for step in instructions["steps"]:
    if step["id"] in seen_steps or not set(step["requires"]) <= seen_steps:
        raise RuntimeError("Invalid fixture step prerequisite/order")
    seen_steps.add(step["id"])
    installed.extend(step["add"])
if Counter(installed) != Counter(item["id"] for item in scene["occurrences"]):
    raise RuntimeError("Fixture steps do not install each occurrence exactly once")

report = {
    "schema_version": 1, "kind": "synthetic-fixture-geometry-receipt",
    "freecad_version": list(App.Version()[:3]), "geometry": geometry,
    "part_types": 2, "occurrences": 3, "pin_world_x_mm": world_x,
    "base_pin_final_overlap_volumes_mm3": overlaps,
    "known_fixture_inventory_and_step_reconciliation": "passed",
    "files": {name: digest(ROOT / name) for name in
              ["generate_fixture.py", "scene.json", "instructions.json", "inventory.json"]},
    "physical_assembly_validated": False,
    "not_run": ["continuous insertion-path checks", "tool access", "rendering", "HTML/PDF generation", "production CAD checks"],
}
(ROOT / "geometry-validation.json").write_text(json.dumps(report, indent=2) + "\n")
print("FIXTURE_VALIDATED", json.dumps(report), flush=True)
