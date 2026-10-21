"""CAD stage, run inside FreeCADCmd: STEP parts -> render meshes with identity preserved.

    FreeCADCmd mechanical_docs/cad_mesh.py PROJECT_DIR OUT_DIR [--linear-deflection MM] [--angular-deflection DEG]

For every part of the validated scene: read its STEP, check it is a valid
closed solid, measure its bounds and volume, tessellate it face by face
(smooth normals within a face, sharp edges between faces), check the mesh's
winding and volume against the B-rep, and write OUT_DIR/<part>.glb in glTF
convention (metres, +Y up; see gltf.to_gltf_frame). OUT_DIR/meshes.json maps
every part and occurrence to its mesh with hashes, tolerances and the checks
performed, so the render stage can verify it is rendering the declared
geometry. Transforms are not applied here: instances stay instances.
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

from mechanical_docs import gltf, receipts  # noqa: E402
from mechanical_docs import transforms as T  # noqa: E402
from mechanical_docs.manifest import ManifestError, load_project  # noqa: E402

import FreeCAD as App  # noqa: E402  (only inside FreeCAD)
import Part  # noqa: E402


def log(*a):
    print("[cad_mesh]", *a, flush=True)


def tessellate_part(shape, linear_deflection, angular_deflection_rad):
    """Per-face tessellation with per-vertex normals averaged over the face's
    triangles (area weighted). Returns positions, normals, indices in the
    shape's own frame and units.

    The whole shape is meshed first (MeshPart, which takes both deflections)
    so every face's stored triangulation shares the same edge discretisation;
    Face.tessellate then returns those triangles face by face."""
    import MeshPart
    whole = MeshPart.meshFromShape(Shape=shape, LinearDeflection=linear_deflection, AngularDeflection=angular_deflection_rad, Relative=False)
    positions, normals, indices = [], [], []
    for face in shape.Faces:
        pts, tris = face.tessellate(linear_deflection)
        if not tris:
            m = MeshPart.meshFromShape(Shape=face, LinearDeflection=linear_deflection, AngularDeflection=angular_deflection_rad, Relative=False)
            pts, tris = m.Topology
            pts = [App.Vector(*p) if not hasattr(p, "x") else p for p in pts]
        if not tris:
            continue
        base = len(positions)
        acc = [[0.0, 0.0, 0.0] for _ in pts]
        for a, b, c in tris:
            pa, pb, pc = pts[a], pts[b], pts[c]
            u = pb - pa; v = pc - pa
            n = u.cross(v)        # area-weighted face normal (not normalised)
            for i in (a, b, c):
                acc[i][0] += n.x; acc[i][1] += n.y; acc[i][2] += n.z
            indices += [base + a, base + b, base + c]
        for p, n in zip(pts, acc):
            L = math.sqrt(n[0] ** 2 + n[1] ** 2 + n[2] ** 2)
            positions.append((p.x, p.y, p.z))
            normals.append((n[0] / L, n[1] / L, n[2] / L) if L > 0 else (0.0, 0.0, 1.0))
    return positions, normals, indices, whole.CountFacets


def mesh_part(part, out_dir, linear_deflection, angular_deflection_deg):
    src = part.asset.resolved
    shape = Part.read(str(src))
    record = {"part_id": part.id, "source": {"path": part.asset.path, "sha256": part.asset.sha256, "units": part.asset.units, "format": part.asset.format},
              "step": {}, "mesh": {}, "checks": {}}
    valid = shape.isValid()
    bb = shape.BoundBox
    record["step"] = {"valid": bool(valid), "solids": len(shape.Solids), "faces": len(shape.Faces),
                      "closed": all(s.isClosed() for s in shape.Solids) if shape.Solids else False,
                      "bounds_min": [bb.XMin, bb.YMin, bb.ZMin], "bounds_max": [bb.XMax, bb.YMax, bb.ZMax],
                      "extent": [bb.XLength, bb.YLength, bb.ZLength], "volume": shape.Volume}
    problems = []
    if not valid:
        problems.append("shape is not valid")
    if len(shape.Solids) < 1:
        problems.append("no solid in STEP")
    scale = T.unit_factor(part.asset.units, "m")
    ang = math.radians(angular_deflection_deg)
    positions, normals, indices, whole_facets = tessellate_part(shape, linear_deflection, ang)
    if not indices:
        problems.append("tessellation produced no triangles")
        record["checks"]["problems"] = problems
        return record, None
    sv = gltf.signed_volume(positions, indices)
    flipped = False
    if sv < 0:
        # inward winding: flip every triangle and every normal
        indices = [indices[k + j] for k in range(0, len(indices), 3) for j in (0, 2, 1)]
        normals = [(-x, -y, -z) for x, y, z in normals]
        sv = -sv; flipped = True
    deviation = abs(sv - shape.Volume) / shape.Volume if shape.Volume else float("inf")
    # normals should point the same way as their triangles: count disagreements
    disagree = 0
    for k in range(0, len(indices), 3):
        a, b, c = (positions[indices[k + i]] for i in range(3))
        n = ((b[1] - a[1]) * (c[2] - a[2]) - (b[2] - a[2]) * (c[1] - a[1]),
             (b[2] - a[2]) * (c[0] - a[0]) - (b[0] - a[0]) * (c[2] - a[2]),
             (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0]))
        for i in range(3):
            vn = normals[indices[k + i]]
            if n[0] * vn[0] + n[1] * vn[1] + n[2] * vn[2] < 0:
                disagree += 1
    mesh_bounds = gltf.bounds(positions)
    bounds_dev = max(abs(mesh_bounds[0][i] - record["step"]["bounds_min"][i]) for i in range(3))
    bounds_dev = max(bounds_dev, max(abs(mesh_bounds[1][i] - record["step"]["bounds_max"][i]) for i in range(3)))
    if deviation > 0.02:
        problems.append(f"mesh volume deviates {deviation:.1%} from the B-rep")
    if disagree > 0.001 * len(indices):
        problems.append(f"{disagree} vertex normals disagree with their triangles")
    if bounds_dev > linear_deflection * 2 + 1e-6:
        problems.append(f"mesh bounds deviate {bounds_dev:.4f} from the B-rep bounds")
    gl_pos = [gltf.to_gltf_frame(p, scale) for p in positions]
    gl_nrm = [gltf.to_gltf_frame(n, 1.0) for n in normals]
    out = Path(out_dir) / f"{part.id}.glb"
    extras = {"mechanical_docs": {"part_id": part.id, "source_sha256": part.asset.sha256, "source_units": part.asset.units,
                                  "source_up_axis": "+Z", "gltf_units": "m", "gltf_up_axis": "+Y",
                                  "conversion": "scene (x, y, z) -> glTF (x, z, -y) * unit factor", "unit_factor": scale}}
    gltf.write_glb(out, gl_pos, gl_nrm, indices, name=part.id, extras=extras)
    record["mesh"] = {"file": out.name, "sha256": receipts.sha256_file(out), "bytes": out.stat().st_size,
                      "vertices": len(positions), "triangles": len(indices) // 3, "whole_shape_triangles": whole_facets,
                      "linear_deflection": linear_deflection, "angular_deflection_deg": angular_deflection_deg,
                      "frame": extras["mechanical_docs"], "winding_flipped": flipped,
                      "signed_volume_source_units": sv, "bounds_min": mesh_bounds[0], "bounds_max": mesh_bounds[1]}
    record["checks"] = {"volume_deviation": deviation, "normal_disagreements": disagree, "bounds_deviation": bounds_dev,
                        "problems": problems, "passed": not problems}
    return record, out


def main(argv):
    if len(argv) < 2:
        raise SystemExit(__doc__)
    project_dir, out_dir = Path(argv[0]), Path(argv[1])
    linear = 0.05; angular = 10.0
    i = 2
    while i < len(argv):
        if argv[i] == "--linear-deflection":
            linear = float(argv[i + 1]); i += 2
        elif argv[i] == "--angular-deflection":
            angular = float(argv[i + 1]); i += 2
        else:
            raise SystemExit(f"unknown argument {argv[i]}")
    try:
        project = load_project(project_dir)
    except ManifestError as e:
        print(e, file=sys.stderr)
        return 2
    out_dir.mkdir(parents=True, exist_ok=True)
    sc = project.scene
    parts = {}
    all_ok = True
    for part in sc.parts.values():
        rec, path = mesh_part(part, out_dir, linear, angular)
        parts[part.id] = rec
        ok = rec["checks"].get("passed", False)
        all_ok &= ok
        st, me = rec["step"], rec.get("mesh", {})
        log(f"{part.id}: valid={st.get('valid')} solids={st.get('solids')} extent={[round(v, 4) for v in st.get('extent', [])]} {part.asset.units} "
            f"volume={st.get('volume', 0):.4f} -> {me.get('triangles', 0)} triangles, volume deviation {rec['checks'].get('volume_deviation', float('nan')):.3%}, "
            f"{'OK' if ok else 'PROBLEMS: ' + '; '.join(rec['checks'].get('problems', []))}")
    occurrences = [{"id": o.id, "part_id": o.part_id, "mesh": parts[o.part_id]["mesh"].get("file"), "parent_id": o.parent_id, "path": o.path,
                    "world": o.world, "world_translation": T.translation(o.world)} for o in sc.occurrences.values()]
    receipt = {
        "kind": "mechanical-docs-mesh-receipt", "generated_at_utc": receipts.utc_now(),
        "freecad_version": ".".join(str(v) for v in App.Version()[:3]), "python": sys.version.split()[0],
        "project_dir": str(project.dir), "scene_id": sc.id, "scene_units": sc.units,
        "input_hashes": project.input_hashes(),
        "tessellation": {"linear_deflection": linear, "angular_deflection_deg": angular, "method": "Part.Face.tessellate per face; area-weighted vertex normals within each face"},
        "parts": parts, "occurrences": occurrences,
        "all_checks_passed": all_ok,
        "checks": ["STEP read and isValid", "solid count", "B-rep bounds/volume", "mesh winding by signed volume", "mesh volume vs B-rep (<2%)",
                   "vertex normal orientation", "mesh bounds vs B-rep bounds"],
        "not_checked": ["interference between occurrences", "assembly path", "visual appearance"],
    }
    receipts.write_json(out_dir / "meshes.json", receipt)
    log(f"wrote {out_dir / 'meshes.json'}; all checks passed: {all_ok}")
    return 0 if all_ok else 1


# FreeCADCmd executes a script file in its own namespace, not as __main__, so
# run when executed by FreeCAD or as a script, and not when imported as a module.
if __name__ == "__main__" or not __name__.startswith("mechanical_docs"):
    # FreeCADCmd: sys.argv is ['FreeCADCmd', script, '--pass', ARG...]; plain python: [script, ARG...]
    if "--pass" in sys.argv:
        args = sys.argv[sys.argv.index("--pass") + 1:]
    else:
        args = [a for a in sys.argv[1:] if Path(a).resolve() != Path(__file__).resolve()]
    try:
        rc = main(args)
    except BaseException:
        import traceback
        traceback.print_exc()
        rc = 1
    print(f"[cad_mesh] exit status {rc}", flush=True)
    sys.exit(rc)
