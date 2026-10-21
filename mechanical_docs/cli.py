"""Command line entry point: python3 -m mechanical_docs <command> ...

    inspect PROJECT_DIR [--json OUT]   validate the manifests, report parts,
                                       occurrences, world transforms and hashes
    manual  PROJECT_DIR --renders DIR --out DIR [--render-receipt FILE] [--meshes FILE]
                                       build manual.json, the HTML manual and the
                                       Typst source; compile the PDF when typst is found
    check   OUT_DIR                    compare HTML, PDF and manual.json; verify links/images

The CAD and render stages run inside their host applications:

    FreeCADCmd mechanical_docs/cad_mesh.py PROJECT_DIR OUT_DIR
    blender -b --python mechanical_docs/render.py -- PROJECT_DIR MESHES_JSON OUT_DIR [--preview]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import receipts
from . import transforms as T
from .manifest import ManifestError, load_project
from .procedure import approach_pose, derive_states


def inspect_report(project):
    sc, ins, inv = project.scene, project.instructions, project.inventory
    states = derive_states(ins, sc)
    parts = []
    for p in sc.parts.values():
        parts.append({
            "id": p.id, "name": p.name, "asset": p.asset.path, "format": p.asset.format, "asset_units": p.asset.units,
            "bytes": p.asset.bytes, "sha256": p.asset.sha256,
            "identifying_dimensions_mm": p.identifying_dimensions_mm,
            "occurrences": [o.id for o in sc.occurrences_of(p.id)],
        })
    assemblies = [{"id": a.id, "parent_id": a.parent_id, "depth": a.depth, "transform": a.transform, "world": a.world} for a in sc.assemblies.values()]
    occurrences = []
    for o in sc.occurrences.values():
        occurrences.append({"id": o.id, "part_id": o.part_id, "parent_id": o.parent_id, "path": o.path,
                            "transform": o.transform, "world": o.world, "world_translation": T.translation(o.world)})
    steps = []
    for st in states:
        ap = approach_pose(sc, st)
        steps.append({"index": st.index, "id": st.step.id, "requires": st.step.requires, "add": st.added, "view": st.step.view,
                      "installed_before": st.before, "installed_after": st.after, "hidden": st.hidden,
                      "parts_needed": st.parts_needed, "caption": st.step.caption,
                      "approach": None if ap is None else {"occurrence_id": ap[0], "start_world_translation": T.translation(ap[1]),
                                                           "end_world_translation": T.translation(ap[2]),
                                                           "validation": st.step.approach.validation}})
    inventory = [{"part_id": it.part_id, "required": it.required, "unit": it.unit, "counted": it.counted,
                  "installed_occurrences": len(sc.occurrences_of(it.part_id))} for it in inv.items]
    return {
        "kind": "mechanical-docs-inspect-report", "generated_at_utc": receipts.utc_now(), **receipts.python_info(),
        "project_dir": str(project.dir), "scene": {"id": sc.id, "title": sc.title, "units": sc.units, "coordinate_system": sc.coordinate_system,
                                                   "source": sc.source, "root_assembly": sc.root_id},
        "instructions": {"id": ins.id, "title": ins.title, "review_state": ins.review_state, "views": {v.id: vars(v) for v in ins.views.values()}},
        "inventory_status": inv.status,
        "counts": {"part_types": len(sc.parts), "assemblies": len(sc.assemblies), "occurrences": len(sc.occurrences), "steps": len(ins.steps)},
        "parts": parts, "assemblies": assemblies, "occurrences": occurrences, "steps": steps, "inventory": inventory,
        "input_hashes": project.input_hashes(),
        "checks_passed": ["schema fields", "asset paths inside root", "asset SHA-256", "unique ids", "hierarchy acyclic with one root",
                          "rigid transforms (det +1, no scale/shear)", "steps: prerequisites ordered, each occurrence installed exactly once",
                          "inventory required quantities equal installed occurrences"],
        "not_checked": ["STEP geometry validity (see cad_mesh.py receipt)", "insertion path or tool access", "physical assembly"],
    }


def print_report(rep, out=sys.stdout):
    w = out.write
    w(f"scene {rep['scene']['id']!r}: {rep['scene']['title']} [{rep['scene']['units']}, {rep['scene']['coordinate_system'].get('up_axis')} up]\n")
    c = rep["counts"]
    w(f"{c['part_types']} part type(s), {c['assemblies']} assembl(ies), {c['occurrences']} occurrence(s), {c['steps']} step(s); review state {rep['instructions']['review_state']}\n")
    w("parts:\n")
    for p in rep["parts"]:
        dims = ", ".join(f"{k} {v}" for k, v in p["identifying_dimensions_mm"].items())
        w(f"  {p['id']:12s} {p['name']:16s} {dims}  [{p['asset']} {p['bytes']} B sha256 {p['sha256'][:12]}…] x{len(p['occurrences'])}\n")
    w("occurrences (world translation in scene units):\n")
    for o in rep["occurrences"]:
        t = o["world_translation"]
        w(f"  {o['id']:10s} part {o['part_id']:8s} under {'/'.join(o['path']) or o['parent_id']:14s} -> ({t[0]:g}, {t[1]:g}, {t[2]:g})\n")
    w("steps:\n")
    for s in rep["steps"]:
        ap = s["approach"]
        hint = f"  approach from {tuple(round(v, 3) for v in ap['start_world_translation'])} ({ap['validation']})" if ap else ""
        w(f"  {s['index']}. {s['id']:14s} +{s['add']}  needs {s['parts_needed']}  requires {s['requires']}{hint}\n")
    w("inventory:\n")
    for it in rep["inventory"]:
        w(f"  {it['part_id']:10s} required {it['required']} {it['unit']}, counted {it['counted'] if it['counted'] is not None else 'not counted'}, installed {it['installed_occurrences']}\n")
    w("input hashes:\n")
    for k, v in rep["input_hashes"].items():
        w(f"  {v}  {k}\n")


def cmd_inspect(args):
    try:
        project = load_project(args.project_dir, root=args.root)
    except ManifestError as e:
        print(e, file=sys.stderr)
        return 2
    rep = inspect_report(project)
    print_report(rep)
    if args.json:
        receipts.write_json(args.json, rep)
        print(f"wrote {args.json}")
    return 0


def cmd_manual(args):
    from . import document
    return document.build(args)


def cmd_check(args):
    from . import checks
    return checks.run(args)


def main(argv=None):
    ap = argparse.ArgumentParser(prog="mechanical_docs", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="command", required=True)
    p = sub.add_parser("inspect", help="validate a project and report its contents")
    p.add_argument("project_dir"); p.add_argument("--json", help="also write the report here"); p.add_argument("--root", help="asset root (default: project dir)")
    p.set_defaults(func=cmd_inspect)
    p = sub.add_parser("manual", help="build manual.json, HTML, Typst and (when typst is present) the PDF")
    p.add_argument("project_dir"); p.add_argument("--renders", required=True, help="render output directory (render-receipt.json inside)")
    p.add_argument("--out", required=True, help="manual output directory"); p.add_argument("--meshes", help="meshes.json from the CAD stage, for the receipt")
    p.add_argument("--no-pdf", action="store_true"); p.add_argument("--embed-images", action="store_true", help="inline images into the HTML as data URIs")
    p.set_defaults(func=cmd_manual)
    p = sub.add_parser("check", help="verify the built manual: HTML/PDF/manual.json agreement, links, images")
    p.add_argument("out_dir"); p.add_argument("--json", help="write the check report here")
    p.set_defaults(func=cmd_check)
    args = ap.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
