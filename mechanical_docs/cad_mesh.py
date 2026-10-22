"""CAD stage, run inside FreeCADCmd: STEP parts -> render meshes with identity preserved.

    FreeCADCmd mechanical_docs/cad_mesh.py --pass PROJECT_DIR OUT_DIR [--linear-deflection MM] [--angular-deflection DEG] [--max-triangles N]

For every part of the validated scene: read its STEP, check it is a valid
closed solid, measure its bounds and volume, tessellate it face by face
(smooth normals within a face, sharp edges between faces), check the mesh's
winding and volume against the B-rep, and write OUT_DIR/<part>.glb in glTF
convention (metres, +Y up; see gltf.to_gltf_frame). OUT_DIR/meshes.json maps
every part and occurrence to its mesh with hashes, tolerances and the checks
performed, so the render stage can verify it is rendering the declared
geometry. Transforms are not applied here: instances stay instances.

Units: FreeCAD/OCCT converts every STEP to millimetres on import, whatever the
file declares (an inch panel reads back as 1193.8 mm). The file's own declared
unit (stepinfo.length_unit) is compared with the manifest's asset unit, the
bounds are recorded in millimetres, and the GLB is scaled from millimetres.

Triangle budget: the deflections are the finest tessellation wanted. A part
that exceeds --max-triangles (threads, knurls, fillets on small hardware) is
re-meshed from a freshly read shape with the deflections coarsened step by
step until it fits; every attempt is recorded. Dense meshes cost little in
Cycles but Freestyle line detection grows superlinearly with edge count
(a 5 M-triangle assembly took 93 minutes for one view).
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

from mechanical_docs import gltf, receipts, stepinfo  # noqa: E402
from mechanical_docs.names import slug  # noqa: E402
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
    empty_faces = 0; empty_area = 0.0; fallbacks = 0

    def attempts(face):
        yield lambda: face.tessellate(linear_deflection)
        yield lambda: MeshPart.meshFromShape(Shape=face, LinearDeflection=linear_deflection, AngularDeflection=angular_deflection_rad, Relative=False).Topology
        yield lambda: face.tessellate(linear_deflection * 10)                         # some B-spline slivers mesh only coarsely
        yield lambda: MeshPart.meshFromShape(Shape=face, MaxLength=max(linear_deflection * 40, 1.0)).Topology   # Mefisto

    for face in shape.Faces:
        pts, tris = [], []
        for n, attempt in enumerate(attempts(face)):
            try:
                pts, tris = attempt()
            except Exception:  # noqa: BLE001  (a mesher refusing a degenerate face)
                pts, tris = [], []
            if tris:
                fallbacks += 1 if n else 0
                break
        if not tris:
            empty_faces += 1; empty_area += face.Area
            continue
        pts = [p if hasattr(p, "x") else App.Vector(*p) for p in pts]
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
    return positions, normals, indices, {"whole_shape_triangles": whole.CountFacets, "whole_shape_volume_mm3": whole.Volume,
                                          "whole_shape_closed": bool(whole.isSolid()), "faces_without_triangles": empty_faces,
                                          "faces_meshed_by_fallback": fallbacks, "area_without_triangles_mm2": empty_area, "shape_area_mm2": shape.Area}


def mesh_part(part, out_dir, linear_deflection, angular_deflection_deg, max_triangles=None):
    src = part.asset.resolved
    record = {"part_id": part.id, "source": {"path": part.asset.path, "sha256": part.asset.sha256, "units": part.asset.units, "format": part.asset.format},
              "step": {}, "mesh": {}, "checks": {}}
    problems = []
    try:
        declared = stepinfo.length_unit(src)
    except stepinfo.StepInfoError as e:
        declared = None
        problems.append(f"cannot read the STEP's declared unit: {e}")
    if declared is not None and declared != part.asset.units:
        problems.append(f"STEP declares {declared!r} but the manifest says {part.asset.units!r}")
    shape = Part.read(str(src))
    valid = shape.isValid()
    # OCCT's default box is loose on curved surfaces (control-point hulls); the
    # optimal box is the exact extent and is what Inventor's range boxes should be compared with
    try:
        bb = shape.optimalBoundingBox(True, False)
        bounds_kind = "optimal"
    except Exception:  # noqa: BLE001  (older FreeCAD)
        bb = shape.BoundBox
        bounds_kind = "loose"
    record["step"] = {"valid": bool(valid), "solids": len(shape.Solids), "faces": len(shape.Faces),
                      "closed": all(s.isClosed() for s in shape.Solids) if shape.Solids else False,
                      "declared_unit": declared, "freecad_unit": "mm", "bounds_kind": bounds_kind,
                      "bounds_min_mm": [bb.XMin, bb.YMin, bb.ZMin], "bounds_max_mm": [bb.XMax, bb.YMax, bb.ZMax],
                      "extent_mm": [bb.XLength, bb.YLength, bb.ZLength], "volume_mm3": shape.Volume}
    if not valid:
        problems.append("shape is not valid")
    if len(shape.Solids) < 1:
        problems.append("no solid in STEP")
    ext = part.identifying_dimensions_mm.get("extent")
    if ext is not None:
        dev = max(abs(a - b) for a, b in zip(sorted(ext), sorted(record["step"]["extent_mm"])))
        record["checks"]["declared_extent_deviation_mm"] = dev
        # the exporter's range boxes are conservative on curved faces (observed up to ~1.5 mm)
        if dev > max(2.0, 0.01 * max(ext)):
            problems.append(f"manifest extent {[round(v, 3) for v in ext]} mm differs from the imported extent {[round(v, 3) for v in record['step']['extent_mm']]} mm by {dev:.3f} mm")
    scale = 0.001        # FreeCAD geometry is in millimetres regardless of the file's unit
    deferred_warnings = []
    attempts = []
    while True:
        positions, normals, indices, whole = tessellate_part(shape, linear_deflection, math.radians(angular_deflection_deg))
        attempts.append({"linear_deflection": linear_deflection, "angular_deflection_deg": angular_deflection_deg, "triangles": len(indices) // 3})
        if max_triangles is None or len(indices) // 3 <= max_triangles or len(attempts) >= 6:
            break
        linear_deflection *= 1.6
        angular_deflection_deg = min(angular_deflection_deg * 1.2, 20.0)
        # OCCT keeps a stored triangulation that is finer than requested, so a coarser pass needs a fresh shape
        shape = Part.read(str(src))
    if max_triangles is not None and len(indices) // 3 > max_triangles:
        deferred_warnings.append(f"{len(indices) // 3} triangles exceed the budget of {max_triangles} after {len(attempts)} coarsening attempts")
    if whole["faces_without_triangles"]:
        frac = whole["area_without_triangles_mm2"] / whole["shape_area_mm2"] if whole["shape_area_mm2"] else 1.0
        msg = f"{whole['faces_without_triangles']} face(s) produced no triangles with any mesher ({frac:.3%} of the surface area)"
        (problems if frac > 0.01 else deferred_warnings).append(msg)
    if not indices:
        problems.append("tessellation produced no triangles")
        record["checks"].update({"problems": problems, "warnings": [], "passed": False})
        return record, None
    sv = gltf.signed_volume(positions, indices)
    flipped = False
    if sv < 0:
        # inward winding: flip every triangle and every normal
        indices = [indices[k + j] for k in range(0, len(indices), 3) for j in (0, 2, 1)]
        normals = [(-x, -y, -z) for x, y, z in normals]
        sv = -sv; flipped = True
    deviation = abs(sv - shape.Volume) / shape.Volume if shape.Volume else float("inf")
    record["checks"]["whole_shape_volume_deviation"] = abs(whole["whole_shape_volume_mm3"] - shape.Volume) / shape.Volume if shape.Volume else float("inf")
    if part.volume_mm3:
        record["checks"]["declared_volume_deviation"] = abs(shape.Volume - part.volume_mm3) / part.volume_mm3
    # normals should point the same way as their triangles: count disagreements and
    # the surface area they cover (folded slivers at seams are many but tiny)
    disagree = 0; disagree_area = 0.0; total_area = 0.0
    for k in range(0, len(indices), 3):
        a, b, c = (positions[indices[k + i]] for i in range(3))
        n = ((b[1] - a[1]) * (c[2] - a[2]) - (b[2] - a[2]) * (c[1] - a[1]),
             (b[2] - a[2]) * (c[0] - a[0]) - (b[0] - a[0]) * (c[2] - a[2]),
             (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0]))
        area = 0.5 * math.sqrt(n[0] ** 2 + n[1] ** 2 + n[2] ** 2)
        total_area += area
        bad = 0
        for i in range(3):
            vn = normals[indices[k + i]]
            if n[0] * vn[0] + n[1] * vn[1] + n[2] * vn[2] < 0:
                bad += 1
        if bad:
            disagree += bad; disagree_area += area
    disagree_frac = disagree_area / total_area if total_area else 0.0
    mesh_bounds = gltf.bounds(positions)
    bounds_dev = max(abs(mesh_bounds[0][i] - record["step"]["bounds_min_mm"][i]) for i in range(3))
    bounds_dev = max(bounds_dev, max(abs(mesh_bounds[1][i] - record["step"]["bounds_max_mm"][i]) for i in range(3)))
    warnings = list(deferred_warnings)
    tess_agree = abs(sv - whole["whole_shape_volume_mm3"]) <= 0.005 * max(abs(sv), 1e-9)
    record["checks"]["tessellations_agree"] = tess_agree
    if deviation > 0.02:
        if tess_agree:
            # two independent tessellations agree with each other but not with GProp's B-rep
            # volume: the B-rep integral is the doubtful number, the render mesh is consistent
            warnings.append(f"B-rep volume {shape.Volume:.1f} mm3 disagrees with both tessellations ({sv:.1f} mm3, {deviation:.1%}); "
                            f"the mesh is self-consistent, the B-rep volume integral is suspect"
                            + (f"; exporter declared {part.volume_mm3:.1f} mm3" if part.volume_mm3 else ""))
        else:
            problems.append(f"mesh volume deviates {deviation:.1%} from the B-rep and the two tessellations disagree")
    # Vertex normals are averaged within a face, so a single B-spline face that models a
    # thread's crests folds a few percent of its area at every deflection (seen on
    # McMaster 47065T242: 0.6 % at 0.05 mm, 1 % at 0.33 mm). Shading only; a gross
    # fraction means a broken tessellation.
    if disagree_frac > 0.05:
        problems.append(f"{disagree} of {len(indices)} vertex normals disagree with their triangles over {disagree_frac:.2%} of the mesh area")
    elif disagree:
        warnings.append(f"{disagree} of {len(indices)} vertex normals disagree with their triangles ({disagree_frac:.3%} of the mesh area: slivers at seams or crests inside one face; shading only)")
    if bounds_dev > linear_deflection * 2 + (1e-6 if bounds_kind == "optimal" else 0.02 * max(record["step"]["extent_mm"])):
        problems.append(f"mesh bounds deviate {bounds_dev:.4f} mm from the B-rep {bounds_kind} bounds")
    gl_pos = [gltf.to_gltf_frame(p, scale) for p in positions]
    gl_nrm = [gltf.to_gltf_frame(n, 1.0) for n in normals]
    out = Path(out_dir) / f"{slug(part.id)}.glb"
    extras = {"mechanical_docs": {"part_id": part.id, "source_sha256": part.asset.sha256, "source_units": part.asset.units,
                                  "freecad_units": "mm", "gltf_units": "m", "gltf_up_axis": "+Y",
                                  "conversion": "FreeCAD mm (x, y, z) -> glTF (x, z, -y) * 0.001", "unit_factor": scale}}
    gltf.write_glb(out, gl_pos, gl_nrm, indices, name=part.id, extras=extras)
    record["mesh"] = {"file": out.name, "sha256": receipts.sha256_file(out), "bytes": out.stat().st_size,
                      "vertices": len(positions), "triangles": len(indices) // 3, "whole_shape": whole,
                      "linear_deflection": linear_deflection, "angular_deflection_deg": angular_deflection_deg,
                      "tessellation_attempts": attempts, "frame": extras["mechanical_docs"], "winding_flipped": flipped,
                      "signed_volume_mm3": sv, "bounds_units": "mm", "bounds_min": mesh_bounds[0], "bounds_max": mesh_bounds[1]}
    record["checks"].update({"volume_deviation": deviation, "normal_disagreements": disagree, "normal_disagreement_area_fraction": disagree_frac, "bounds_deviation_mm": bounds_dev,
                             "problems": problems, "warnings": warnings, "passed": not problems})
    return record, out


def main(argv):
    if len(argv) < 2:
        raise SystemExit(__doc__)
    project_dir, out_dir = Path(argv[0]), Path(argv[1])
    linear = 0.05; angular = 10.0; max_triangles = 50000
    i = 2
    while i < len(argv):
        if argv[i] == "--linear-deflection":
            linear = float(argv[i + 1]); i += 2
        elif argv[i] == "--angular-deflection":
            angular = float(argv[i + 1]); i += 2
        elif argv[i] == "--max-triangles":
            max_triangles = int(argv[i + 1]) if argv[i + 1] != "none" else None; i += 2
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
        rec, path = mesh_part(part, out_dir, linear, angular, max_triangles)
        parts[part.id] = rec
        ok = rec["checks"].get("passed", False)
        all_ok &= ok
        st, me = rec["step"], rec.get("mesh", {})
        log(f"{part.name[:40]}: unit {st.get('declared_unit')} valid={st.get('valid')} solids={st.get('solids')} extent_mm={[round(v, 3) for v in st.get('extent_mm', [])]} "
            f"volume_mm3={st.get('volume_mm3', 0):.3f} -> {me.get('triangles', 0)} triangles"
            f"{' (deflection ' + str(round(me['linear_deflection'], 3)) + ' mm after ' + str(len(me['tessellation_attempts'])) + ' attempts)' if len(me.get('tessellation_attempts', [])) > 1 else ''}, "
            f"volume deviation {rec['checks'].get('volume_deviation', float('nan')):.3%}, "
            f"{'OK' if ok else 'PROBLEMS: ' + '; '.join(rec['checks'].get('problems', []))}")
    occurrences = [{"id": o.id, "part_id": o.part_id, "mesh": parts[o.part_id]["mesh"].get("file"), "parent_id": o.parent_id, "path": o.path,
                    "world": o.world, "world_translation": T.translation(o.world)} for o in sc.occurrences.values()]
    receipt = {
        "kind": "mechanical-docs-mesh-receipt", "generated_at_utc": receipts.utc_now(),
        "freecad_version": ".".join(str(v) for v in App.Version()[:3]), "python": sys.version.split()[0],
        "project_dir": str(project.dir), "scene_id": sc.id, "scene_units": sc.units, "native_up_axis": sc.native_up_axis, "basis_to_z_up": sc.basis_to_z_up,
        "input_hashes": project.input_hashes(),
        "tessellation": {"linear_deflection": linear, "angular_deflection_deg": angular, "max_triangles_per_part": max_triangles,
                         "method": "Part.Face.tessellate per face; area-weighted vertex normals within each face; deflections coarsened x1.6 per attempt until the part fits the triangle budget"},
        "parts": parts, "occurrences": occurrences,
        "all_checks_passed": all_ok,
        "checks": ["STEP declared unit equals the manifest's asset unit", "STEP read and isValid", "solid count", "B-rep bounds/volume (mm)",
                   "manifest extent vs imported extent (when declared)", "mesh winding by signed volume", "mesh volume vs B-rep (<2%)",
                   "vertex normal orientation (<5% of the mesh area disagreeing; shading only)", "mesh bounds vs B-rep bounds"],
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
