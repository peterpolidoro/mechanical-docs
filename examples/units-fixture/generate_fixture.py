"""Generate the units fixture: the same two solids declared in three units.

    python3 examples/units-fixture/generate_fixture.py

FreeCAD cannot write a STEP file in inches or centimetres, so this generator
derives them from the three-part fixture's millimetre files (FreeCAD-written,
hashes pinned below) by rewriting only the file's unit context: the LENGTH_UNIT
referenced from GLOBAL_UNIT_ASSIGNED_CONTEXT becomes a CONVERSION_BASED_UNIT
inch (25.4 mm, the way Inventor writes it) or SI_UNIT(.CENTI.,.METRE.). The
coordinates are untouched, so the 10 x 30 pin becomes a 10 x 30 inch pin
(254 x 762 mm) and the 100 x 60 x 8 base a 100 x 60 x 8 cm base. A kernel
that honours the declared unit therefore reads them 25.4 or 10 times larger
than the millimetre original, which is exactly what the pipeline's extent and
bounds checks must see. The scene is in inches, +Y up with a declared basis,
and a nested group, so scene-unit, asset-unit and frame conversions are all
exercised in one small project. Synthetic fixture only: not a product.
"""
from __future__ import annotations

import hashlib
import json
import math
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SRC = ROOT.parent / "three-part-fixture"
ASSETS = ROOT / "assets"
ASSETS.mkdir(exist_ok=True)

GUAC = re.compile(r"GLOBAL_UNIT_ASSIGNED_CONTEXT\s*\(\s*\(([^)]*)\)\s*\)", re.S)
ENTITY = re.compile(r"#(\d+)\s*=\s*", re.S)
COMMENT = "/* mechanical-docs units fixture: derived from the three-part fixture's millimetre file by rewriting the unit context only; coordinates unchanged */"


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def length_unit_entity(text):
    """(entity id, full entity text) of the LENGTH_UNIT the unit context references."""
    ctx = GUAC.findall(text)
    if len(ctx) != 1:
        raise RuntimeError("expected exactly one GLOBAL_UNIT_ASSIGNED_CONTEXT")
    for ref in ctx[0].split(","):
        eid = int(ref.strip()[1:])
        m = re.search(r"#%d\s*=\s*.*?;" % eid, text, re.S)
        if m and "LENGTH_UNIT" in m.group(0):
            return eid, m.group(0)
    raise RuntimeError("no LENGTH_UNIT in the unit context")


def retag(text, unit):
    """The STEP text with its geometry length unit redeclared as `unit`."""
    eid, ent = length_unit_entity(text)
    if "SI_UNIT(.MILLI.,.METRE.)" not in ent:
        raise RuntimeError("source file is not in millimetres")
    nmax = max(int(m.group(1)) for m in ENTITY.finditer(text))
    if unit == "cm":
        new = f"#{eid} = ( LENGTH_UNIT() NAMED_UNIT(*) SI_UNIT(.CENTI.,.METRE.) );"
        extra = ""
    elif unit == "in":
        a, b, c = nmax + 1, nmax + 2, nmax + 3
        new = f"#{eid} = ( CONVERSION_BASED_UNIT('INCH',#{a}) LENGTH_UNIT() NAMED_UNIT(#{b}) );"
        extra = (f"#{a} = LENGTH_MEASURE_WITH_UNIT(LENGTH_MEASURE(25.4),#{c});\n"
                 f"#{b} = DIMENSIONAL_EXPONENTS(1.,0.,0.,0.,0.,0.,0.);\n"
                 f"#{c} = ( LENGTH_UNIT() NAMED_UNIT(*) SI_UNIT(.MILLI.,.METRE.) );\n")
    else:
        raise ValueError(unit)
    out = text.replace(ent, new, 1)
    out = out.replace("ENDSEC;\nEND-ISO-10303-21;", extra + "ENDSEC;\nEND-ISO-10303-21;")
    out = out.replace("HEADER;\n", "HEADER;\n" + COMMENT + "\n", 1)
    if extra and extra not in out:
        raise RuntimeError("could not append the inch unit entities")
    return out


def matrix(rot, t):
    return [[*rot[0], float(t[0])], [*rot[1], float(t[1])], [*rot[2], float(t[2])], [0.0, 0.0, 0.0, 1.0]]


IDENT = [[1, 0, 0], [0, 1, 0], [0, 0, 1]]
# part Z (the pin's axis, the base's normal) -> native +Y, so the parts stand up in the Y-up native frame
Z_TO_Y = [[1, 0, 0], [0, 0, 1], [0, -1, 0]]
BASIS_Y_UP = [[1, 0, 0, 0], [0, 0, -1, 0], [0, 1, 0, 0], [0, 0, 0, 1]]     # native (x, y, z) -> z-up (x, -z, y)

src_scene = json.loads((SRC / "scene.json").read_text())
src_hash = {p["id"]: p["asset"]["sha256"] for p in src_scene["parts"]}
sources = {}
for name in ("pin", "base"):
    path = SRC / "assets" / f"{name}.step"
    if digest(path) != src_hash[name]:
        raise RuntimeError(f"{path} does not match the three-part fixture's scene.json")
    sources[name] = path.read_text(encoding="utf-8")

derived = {
    "pin-in": ("pin", "in", 25.4),
    "base-cm": ("base", "cm", 10.0),
    "pin-mm": ("pin", "mm", 1.0),
}
expected_mm = {"pin": ([10, 10, 30], math.pi * 5 ** 2 * 30), "base": ([100, 60, 8], 100 * 60 * 8 - 2 * math.pi * 5.25 ** 2 * 8)}
assets = {}
for pid, (src, unit, f) in derived.items():
    text = sources[src] if unit == "mm" else retag(sources[src], unit)
    path = ASSETS / f"{pid}.step"
    path.write_text(text, encoding="utf-8")
    ext, vol = expected_mm[src]
    assets[pid] = {"path": f"assets/{pid}.step", "sha256": digest(path), "bytes": path.stat().st_size, "declared_unit": unit,
                   "derived_from": f"three-part-fixture/assets/{src}.step", "source_sha256": src_hash[src],
                   "coordinates_unchanged": True, "expected_extent_mm": [v * f for v in ext], "expected_volume_mm3": vol * f ** 3}

scene = {
    "schema_version": "draft-1", "id": "units-fixture",
    "title": "Units fixture: inch, centimetre and millimetre assets in an inch, Y-up scene", "units": "in",
    "coordinate_system": {"handedness": "right", "up_axis": "+Y", "origin": "base bottom centre (native)",
                          "note": "native frame is Y up; basis_to_z_up is applied once at the root", "basis_to_z_up": BASIS_Y_UP},
    "source": {"kind": "synthetic", "generator": "examples/units-fixture/generate_fixture.py",
               "qualification": "fixture only: the inch and centimetre files are the millimetre fixture files with their unit context rewritten"},
    "parts": [
        {"id": "pin-in", "name": "Pin declared in inches", "asset": {"path": "assets/pin-in.step", "format": "step", "units": "in", "sha256": assets["pin-in"]["sha256"]},
         "identifying_dimensions_mm": {"extent": assets["pin-in"]["expected_extent_mm"]}, "volume_mm3": assets["pin-in"]["expected_volume_mm3"],
         "description": "10 x 30 inch cylinder: the millimetre pin's coordinates read in inches"},
        {"id": "base-cm", "name": "Base declared in centimetres", "asset": {"path": "assets/base-cm.step", "format": "step", "units": "cm", "sha256": assets["base-cm"]["sha256"]},
         "identifying_dimensions_mm": {"extent": assets["base-cm"]["expected_extent_mm"]}, "volume_mm3": assets["base-cm"]["expected_volume_mm3"],
         "description": "100 x 60 x 8 cm plate with two 10.5 cm holes: the millimetre base's coordinates read in centimetres"},
        {"id": "pin-mm", "name": "Pin in millimetres", "asset": {"path": "assets/pin-mm.step", "format": "step", "units": "mm", "sha256": assets["pin-mm"]["sha256"]},
         "identifying_dimensions_mm": {"extent": assets["pin-mm"]["expected_extent_mm"]}, "volume_mm3": assets["pin-mm"]["expected_volume_mm3"],
         "description": "the unchanged 10 x 30 mm pin"},
    ],
    "assemblies": [
        {"id": "root", "parent_id": None, "transform": matrix(IDENT, (0, 0, 0))},
        {"id": "stand", "parent_id": "root", "transform": matrix(IDENT, (0, 0, -10))},
    ],
    "occurrences": [
        {"id": "base-cm-1", "part_id": "base-cm", "parent_id": "root", "transform": matrix(Z_TO_Y, (0, 0, 0))},
        {"id": "pin-in-1", "part_id": "pin-in", "parent_id": "stand", "transform": matrix(Z_TO_Y, (30, 2, 10))},
        {"id": "pin-mm-1", "part_id": "pin-mm", "parent_id": "stand", "transform": matrix(Z_TO_Y, (-30, 0, 10))},
    ],
}
(ROOT / "scene.json").write_text(json.dumps(scene, indent=2) + "\n")

instructions = {
    "schema_version": "draft-1", "scene": "scene.json", "id": "units-fixture-sequence",
    "title": "Units fixture: synthetic sequence", "review_state": "draft",
    "views": [{"id": "iso", "projection": "orthographic", "eye": [90, -110, 70], "target": [0, 0, 12], "up": [0, 0, 1]}],
    "steps": [
        {"id": "place-base", "requires": [], "add": ["base-cm-1"], "view": "iso", "caption": "Place the centimetre base."},
        {"id": "stand-inch-pin", "requires": ["place-base"], "add": ["pin-in-1"], "view": "iso", "caption": "Stand the inch pin beside it (illustration only).",
         "approach": {"occurrence_id": "pin-in-1", "start_offset": [0, 0, 8], "end_offset": [0, 0, 0], "validation": "unverified-render-hint"}},
        {"id": "stand-mm-pin", "requires": ["place-base"], "add": ["pin-mm-1"], "view": "iso", "caption": "Stand the millimetre pin on the other side (illustration only).",
         "approach": {"occurrence_id": "pin-mm-1", "start_offset": [0, 0, 3], "end_offset": [0, 0, 0], "validation": "unverified-render-hint"}},
    ],
}
(ROOT / "instructions.json").write_text(json.dumps(instructions, indent=2) + "\n")
inventory = {"schema_version": "draft-1", "scene": "scene.json", "status": "synthetic required quantities; physical stock not counted",
             "items": [{"part_id": pid, "required": 1, "unit": "each", "counted": None} for pid in ("pin-in", "base-cm", "pin-mm")]}
(ROOT / "inventory.json").write_text(json.dumps(inventory, indent=2) + "\n")
render = {"schema_version": "draft-1", "note": "Illustration settings only.",
          "looks": {"pin-in": "blue-anodized", "base-cm": "aluminium", "pin-mm": "red-plastic"}, "inspection_groups": ["stand"]}
(ROOT / "render.json").write_text(json.dumps(render, indent=2) + "\n")

# expected z-up world translations, in the scene's inches: native (x, y, z) -> (x, -z, y)
expected_world_in = {"base-cm-1": [0, 0, 0], "pin-in-1": [30, 0, 2], "pin-mm-1": [-30, 0, 0]}
receipt = {
    "schema_version": 1, "kind": "units-fixture-receipt",
    "method": "unit context rewritten (CONVERSION_BASED_UNIT inch of 25.4 mm, or SI_UNIT centi metre); coordinates unchanged",
    "assets": assets, "scene_units": "in", "native_up_axis": "+Y", "expected_world_translation_in": expected_world_in,
    "files": {name: digest(ROOT / name) for name in ["generate_fixture.py", "scene.json", "instructions.json", "inventory.json", "render.json"]},
    "not_run_here": ["FreeCAD import (tests/test_cad_stage.py runs the CAD stage when FreeCADCmd is present)", "rendering", "physical anything"],
}
(ROOT / "fixture-receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
print("UNITS_FIXTURE_WRITTEN", json.dumps({k: (v["declared_unit"], v["expected_extent_mm"]) for k, v in assets.items()}))
