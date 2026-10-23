"""Viewer export, run inside Blender (bpy): two GLBs and anchor data for a web model viewer.

    python mechanical_docs/viewer.py PROJECT_DIR MESHES_JSON RENDER_DIR [--budget N] [--sharp-angle DEG]

Reads the validated project, the CAD stage's meshes.json and the render receipt in
RENDER_DIR (the exploded view's recorded offsets) and writes RENDER_DIR/viewer/:

    assembled.glb        every occurrence at its installed pose
    exploded.glb         the same, with the receipt's exploded offsets on the top-level group nodes
    viewer-receipt.json  the triangle budget, per-part triangles before and after decimation, the
                         instanced totals per state, file hashes, the offsets used, and one anchor
                         per subassembly instance and for the root parts in both states: the
                         bounds centre projected onto the nearest surface with its outward normal

glTF conventions (gltf.py): metres, +Y up; one mesh per part shared by every occurrence
through nodes; node names are occurrence ids; one parent node per subassembly instance named
by its id, nested as in the scene; parts directly under the root under `root-parts`; no Draco,
no textures, one flat material. A part whose share of the triangle budget is smaller than its
mesh is decimated with Blender's collapse decimation (small parts are kept whole first);
normals are split at edges sharper than --sharp-angle so flat faces stay flat. Nothing here
changes identity, quantity or pose: installed poses come from the scene, exploded offsets from
the render receipt, and the receipt's scene/asset hashes must match the project.
"""
from __future__ import annotations

import math
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

from mechanical_docs import explode, geometry, gltf, receipts  # noqa: E402
from mechanical_docs import transforms as T  # noqa: E402
from mechanical_docs.manifest import ManifestError, load_project  # noqa: E402

import bpy  # noqa: E402  (only inside Blender)
from mathutils import Matrix, Vector  # noqa: E402

DEFAULT_BUDGET = 200000      # triangles per GLB before instancing; about 6 MB with normals
KEEP_WHOLE_BELOW = 1500      # parts this small are never decimated


def log(*a):
    print("[viewer]", *a, flush=True)


def allocate(tris, budget, keep_below=KEEP_WHOLE_BELOW):
    """Target triangle count per part: everything when the total fits; otherwise
    small parts whole and the rest scaled to the remaining budget."""
    total = sum(tris.values())
    if total <= budget:
        return dict(tris)
    small = {p: t for p, t in tris.items() if t <= keep_below}
    rest = {p: t for p, t in tris.items() if t > keep_below}
    left = max(budget - sum(small.values()), 0)
    ratio = left / max(sum(rest.values()), 1)
    out = dict(small)
    for p, t in rest.items():
        out[p] = max(int(t * ratio), min(t, keep_below))
    return out


def mesh_arrays(me, sharp_angle_deg):
    """(positions, normals, indices) in the glTF frame from a Blender mesh in
    metres, +Z up: one vertex per distinct (vertex, corner normal) so edges
    sharper than the angle stay crisp while curved faces stay smooth."""
    me.set_sharp_from_angle(angle=math.radians(sharp_angle_deg))
    me.calc_loop_triangles()
    verts = me.vertices; loops = me.loops; cn = me.corner_normals
    index_of = {}; positions = []; normals = []; indices = []
    for tri in me.loop_triangles:
        for li in tri.loops:
            vi = loops[li].vertex_index
            n = cn[li].vector
            key = (vi, round(n.x, 3), round(n.y, 3), round(n.z, 3))
            k = index_of.get(key)
            if k is None:
                k = len(positions); index_of[key] = k
                co = verts[vi].co
                positions.append(gltf.to_gltf_frame((co.x, co.y, co.z), 1.0))
                normals.append(gltf.to_gltf_frame((n.x, n.y, n.z), 1.0))
            indices.append(k)
    return positions, normals, indices


def import_part(path):
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=str(path), import_shading="NORMALS")
    new = [o for o in bpy.data.objects if o not in before and o.type == "MESH"]
    if len(new) != 1:
        raise SystemExit(f"{path}: expected one mesh object, imported {len(new)}")
    for other in [o for o in bpy.data.objects if o not in before and o is not new[0]]:
        bpy.data.objects.remove(other)
    return new[0]


def decimate(obj, target):
    """Replace the object's mesh by a collapse-decimated copy with about `target` triangles."""
    n = len(obj.data.polygons)
    if target >= n:
        return n
    mod = obj.modifiers.new("md_decimate", "DECIMATE")
    mod.decimate_type = "COLLAPSE"; mod.ratio = target / n; mod.use_collapse_triangulate = True
    bpy.context.view_layer.update()
    dg = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(obj.evaluated_get(dg), preserve_all_data_layers=False, depsgraph=dg)
    obj.modifiers.remove(mod)
    old = obj.data; obj.data = me; bpy.data.meshes.remove(old)
    return len(me.polygons)


def node_tree(scene, factor, offsets_mm=None):
    """glTF nodes for the scene: one per subassembly instance (nested as in the
    scene, identity matrices except a top-level group's exploded offset), one per
    occurrence (its installed world pose), `root-parts` for the root's own parts."""
    nodes = []; index = {}
    f_mm = T.unit_factor("mm", "m")

    def add(name, mesh=None, matrix=None):
        nodes.append({"name": name, "mesh": mesh, "matrix": matrix, "children": []})
        return len(nodes) - 1

    def offset_matrix(gid):
        if not offsets_mm or gid not in offsets_mm:
            return None
        o = offsets_mm[gid]
        tr = T.translate(o[0] * f_mm, o[1] * f_mm, o[2] * f_mm)
        return gltf.frame_matrix_gltf(tr)

    for aid, asm in scene.assemblies.items():
        if aid == scene.root_id or not scene.members(aid):
            continue
        top = asm.parent_id == scene.root_id
        index[aid] = add(aid, matrix=offset_matrix(aid) if top else None)
    roots = []
    for aid, asm in scene.assemblies.items():
        if aid not in index:
            continue
        if asm.parent_id == scene.root_id:
            roots.append(index[aid])
        elif asm.parent_id in index:
            nodes[index[asm.parent_id]]["children"].append(index[aid])
    root_parts = [oid for oid, occ in scene.occurrences.items() if occ.parent_id == scene.root_id]
    if root_parts:
        index[explode.ROOT_PARTS] = add(explode.ROOT_PARTS, matrix=offset_matrix(explode.ROOT_PARTS)); roots.append(index[explode.ROOT_PARTS])
    return nodes, roots, index


def main(argv):
    if len(argv) < 3:
        raise SystemExit(__doc__)
    project_dir, meshes_path, render_dir = Path(argv[0]), Path(argv[1]), Path(argv[2])
    budget = DEFAULT_BUDGET; sharp = 30.0; i = 3
    while i < len(argv):
        if argv[i] == "--budget":
            budget = int(argv[i + 1]); i += 2
        elif argv[i] == "--sharp-angle":
            sharp = float(argv[i + 1]); i += 2
        else:
            raise SystemExit(f"unknown argument {argv[i]}")
    try:
        project = load_project(project_dir)
    except ManifestError as e:
        print(e, file=sys.stderr)
        return 2
    scene = project.scene
    meshes = receipts.read_json(meshes_path)
    if meshes.get("kind") != "mechanical-docs-mesh-receipt":
        raise SystemExit(f"{meshes_path}: not a mesh receipt")
    stale = {k: v for k, v in project.geometry_input_hashes().items() if meshes["input_hashes"].get(k) != v}
    if stale:
        raise SystemExit(f"{meshes_path} was made from different geometry inputs ({sorted(stale)}); re-run the CAD stage")
    rp = render_dir / "render-receipt.json"
    if not rp.is_file():
        raise SystemExit(f"no render receipt at {rp}")
    rr = receipts.read_json(rp)
    skip = project.non_render_inputs()
    if {k: v for k, v in rr.get("input_hashes", {}).items() if k not in skip} != project.render_input_hashes():
        raise SystemExit(f"{rp} was made from a different scene, assets or instructions; render first")
    if rr.get("mesh_hashes") != {pid: rec["mesh"]["sha256"] for pid, rec in meshes["parts"].items()}:
        raise SystemExit(f"{rp} was rendered from different meshes")
    exploded = next((v for v in rr["views"] if v.get("kind") == "exploded"), None)
    offsets_mm = exploded["offsets_mm"] if exploded else None
    if exploded is None:
        log("the render receipt has no exploded view: only assembled.glb is written")
    out = render_dir / "viewer"; out.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    bpy.ops.wm.read_factory_settings(use_empty=True)
    factor = T.unit_factor(scene.units, "m")
    mdir = meshes_path.resolve().parent
    objs = {}; original = {}
    for pid, rec in meshes["parts"].items():
        path = mdir / rec["mesh"]["file"]
        if receipts.sha256_file(path) != rec["mesh"]["sha256"]:
            raise SystemExit(f"{path}: SHA-256 differs from meshes.json; re-run the CAD stage")
        o = import_part(path)
        objs[pid] = o; original[pid] = len(o.data.polygons)
    targets = allocate(original, budget)
    decimated = {}
    for pid, o in objs.items():
        decimated[pid] = decimate(o, targets[pid])
        if decimated[pid] != original[pid]:
            log(f"{pid[-40:]}: {original[pid]} -> {decimated[pid]} triangles")
    mesh_list = []; mesh_index = {}
    for pid, o in objs.items():
        pos, nrm, idx = mesh_arrays(o.data, sharp)
        mesh_index[pid] = len(mesh_list)
        mesh_list.append({"name": pid, "positions": pos, "normals": nrm, "indices": idx})
    occurrence_counts = {}
    for occ in scene.occurrences.values():
        occurrence_counts[occ.part_id] = occurrence_counts.get(occ.part_id, 0) + 1
    instanced = sum(decimated[pid] * n for pid, n in occurrence_counts.items())
    # anchors: per subassembly instance and for the root parts, in both states
    anchors = {}
    groups = [(aid, scene.members(aid)) for aid in scene.assemblies if aid != scene.root_id and scene.members(aid)]
    root_parts = [oid for oid, occ in scene.occurrences.items() if occ.parent_id == scene.root_id]
    if root_parts:
        groups.append((explode.ROOT_PARTS, root_parts))
    for gid, members in groups:
        mn, mx = explode.bounds_m(scene, meshes, members)
        ctr = Vector(explode.centre(mn, mx))
        best = None
        for oid in members:
            occ = scene.occurrences[oid]
            M = Matrix(T.scaled_translation(occ.world, factor))
            ok, loc, nrm, _ = objs[occ.part_id].closest_point_on_mesh(M.inverted() @ ctr)
            if not ok:
                continue
            wp = M @ loc; wn = (M.to_3x3() @ nrm).normalized()
            d = (wp - ctr).length
            if best is None or d < best[0]:
                best = (d, wp, wn, oid)
        if best is None:
            raise SystemExit(f"{gid}: no surface point found for its anchor")
        _, wp, wn, oid = best
        off = Vector(offsets_mm.get(explode.group_of(scene, members[0]) if gid != explode.ROOT_PARTS else explode.ROOT_PARTS, [0, 0, 0])) * 0.001 if offsets_mm else Vector((0, 0, 0))
        anchors[gid] = {"on_occurrence": oid, "bounds_centre_m": [round(v, 5) for v in ctr],
                        "assembled": {"position_m": [round(v, 5) for v in gltf.to_gltf_frame(tuple(wp), 1.0)], "normal": [round(v, 4) for v in gltf.to_gltf_frame(tuple(wn), 1.0)]},
                        "exploded": {"position_m": [round(v, 5) for v in gltf.to_gltf_frame(tuple(wp + off), 1.0)], "normal": [round(v, 4) for v in gltf.to_gltf_frame(tuple(wn), 1.0)]} if offsets_mm else None}
    files = {}
    for state, offs in (("assembled", None), ("exploded", offsets_mm)):
        if state == "exploded" and offs is None:
            continue
        nodes, roots, index = node_tree(scene, factor, offs)
        for oid, occ in scene.occurrences.items():
            k = len(nodes)
            nodes.append({"name": oid, "mesh": mesh_index[occ.part_id], "matrix": gltf.frame_matrix_gltf(T.scaled_translation(occ.world, factor)), "children": []})
            parent = explode.ROOT_PARTS if occ.parent_id == scene.root_id else occ.parent_id
            nodes[index[parent]]["children"].append(k)
        path = out / f"{state}.glb"
        size = gltf.write_scene_glb(path, mesh_list, nodes, roots,
                                    extras={"scene_id": scene.id, "state": state, "frame": "metres, +Y up; node names are occurrence ids",
                                            "offsets_mm": offs or {}, "triangle_budget": budget, "generator": "mechanical-docs viewer.py"})
        files[state] = {**receipts.file_entry(path, render_dir), "nodes": len(nodes), "triangles_instanced": instanced}
        log(f"{path.name}: {size / 1e6:.2f} MB, {len(nodes)} nodes, {instanced} instanced triangles")
    receipt = {
        "kind": "mechanical-docs-viewer-receipt", "generated_at_utc": receipts.utc_now(), "blender": bpy.app.version_string, "python": sys.version.split()[0],
        "project_dir": str(project.dir), "scene_id": scene.id, "scene_units": scene.units, "unit_factor_to_m": factor,
        "input_hashes": project.input_hashes(), "render_receipt": receipts.file_entry(rp), "meshes_json_sha256": receipts.sha256_file(meshes_path),
        "frame": f"glTF: metres, +Y up; scene (+Z up, {scene.units}) via gltf.to_gltf_frame",
        "triangle_budget": budget, "keep_whole_below": KEEP_WHOLE_BELOW, "sharp_angle_deg": sharp,
        "triangles": {"original_total": sum(original.values()), "decimated_total": sum(decimated.values()), "instanced_total": instanced,
                      "parts": {pid: {"original": original[pid], "decimated": decimated[pid], "occurrences": occurrence_counts.get(pid, 0)} for pid in objs}},
        "offsets_mm": offsets_mm, "exploded_view_present": exploded is not None,
        "files": files, "anchors": anchors, "material": "one flat material (gltf.FLAT_MATERIAL); no textures; no Draco",
        "not_checked": ["appearance in a browser (model-viewer)", "anchor visibility from every orbit"],
        "seconds": round(time.time() - t0, 1),
    }
    receipts.write_json(out / "viewer-receipt.json", receipt)
    log(f"wrote {out / 'viewer-receipt.json'}: budget {budget}, {sum(original.values())} -> {sum(decimated.values())} triangles over {len(objs)} meshes, {len(anchors)} anchors, {receipt['seconds']} s")
    return 0


if __name__ == "__main__":
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
    sys.exit(main(argv))
