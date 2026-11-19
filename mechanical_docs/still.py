"""A picture outside a manual, run inside Blender: a scene, or one subassembly of it, from a named side.

    blender -b --python mechanical_docs/still.py -- PROJECT_DIR MESHES_JSON OUT_DIR [--views iso,+x] [--direction X,Y,Z] [--up +y]
                                                    [--group ASSEMBLY_ID] [--size WxH] [--exposure STOPS] [--engine E]
                                                    [--preview] [--no-lines] [--outliner freestyle|line-art|mixed]
                                                    [--pose NAME] [--at "JOINT=VALUE,JOINT=VALUE"]

PROJECT_DIR needs a `scene.json` with its assets and nothing else: no
inventory and no instructions. `mechanical-cad`'s flatten step writes such a
directory from a project repository. MESHES_JSON is the CAD stage's receipt
for that scene (cad_mesh.py takes a directory that holds a scene alone). When
the directory also holds `finishes.json` and `render.json` they are used as
the render stage uses them: a part is drawn in the look render.json names for
it, else in its finish, else in the default look. Whatever else the directory
holds is not read.

A view says where the camera stands, in the scene's +Z-up frame, as a
direction from the middle of what is drawn. The names are the ones
mechanical-cad's tools/picture.py takes (views.py):

    iso         from +X, -Y and above          iso-back    from -X, +Y and above
    below       from +X, -Y and below          below-back  from -X, +Y and below
    +x -x +y -y +z -z                          from that side, looking along the axis

Straight along Z the picture is a plan: from above X runs to the right and Y
upwards. `--direction X,Y,Z` stands the camera anywhere else; its picture is
called `custom`. Without `--views` and `--direction` the view is `iso`.
`--up` names what points up in every picture of the run, as an axis (`+y`) or
as X,Y,Z, where Z is not wanted: for a scene that is declared Z up and stands
otherwise, or to lay a long thing across the picture.
`--group` draws one subassembly alone, every occurrence under it at its
canonical pose. The camera is orthographic and frames what is drawn; `--size`
gives the image's width and height in pixels where the settings' long side
and aspect are not wanted. The background is transparent, as in the render
stage (`film_transparent`); with Cycles a floor under the lowest point
catches the shadows, except for a camera at or below it.

Outlines are drawn as the render stage draws them (render.py, "Outlines"):
by Freestyle within its triangle budget and not at all above it, unless
render.json's `lines.outliner` or `--outliner` gives them to Line Art, which
draws a whole assembly.

`--pose NAME` draws the scene with its joints where a pose of its
`motion.json` puts them (joints.py; the file lies beside `scene.json`, and
`mechanical-cad` derives it from a record that is a draft there), and `--at`
with the joints it names at the values it gives, over the pose when both are
given. A joint that neither names is at zero, where the scene has everything;
a joint that follows another goes where that one takes it; a joint the scene
holds in several places may be given by its bare name. What a joint moves is
drawn where the values put it, and the camera frames it there. A scene
without the file refuses both options.

A still is exposed to show colours. The studio of the render stage is
high-key: a face that looks up is lit about seven times as brightly as its
colour, which makes a manual's parts light shapes with dark outlines and
turns a mid-grey finish white. A still is therefore exposed by the settings'
`still_exposure` (-2.5 stops unless render.json says otherwise), or by
`--exposure`, where the render stage uses `exposure`; at -2.5 a face that
looks up comes out about as its finish gives it, and other faces darker.

OUT_DIR gets `still-<view>.png` (`still-<group>-<view>.png` for a
subassembly, `+x` written as plus-x; `still-pose-<pose>-<view>.png` for a
pose, `still-at-<view>.png` for values given without one) and `stills.json`,
the receipt of this run: versions, engine, the settings' hash, the hashes of
the scene, the assets, the finishes and the meshes, the look every part was
drawn with, each picture with its hash, camera and what it shows, for moved
joints `motion.json` with its hash, the pose and every joint's value, and the
checks the render stage makes (mesh bounds against the CAD stage's, canonical
poses restored after every picture). A run describes the pictures it made;
pictures of an earlier run that lie in OUT_DIR are not in its receipt.

A picture is an illustration. It shows the CAD poses and the looks the
project gave its parts, and says nothing of sequence, fasteners or access. A
picture with joints moved shows where the record of the joints says the parts
can go; nothing is checked of what they meet there.
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

from mechanical_docs import joints, receipts, views  # noqa: E402
from mechanical_docs.manifest import ManifestError, load_scene_only  # noqa: E402
from mechanical_docs.names import slug  # noqa: E402
from mechanical_docs.render import Renderer, log, read_meshes  # noqa: E402  (imports bpy: only inside Blender)
from mechanical_docs.render_settings import OUTLINERS, load_settings  # noqa: E402

import bpy  # noqa: E402

CUSTOM = "custom"


def options(argv):
    """(project directory, mesh receipt, output directory, options) from the command line."""
    if len(argv) < 3:
        raise SystemExit(__doc__)
    opts = {"views": None, "direction": None, "group": None, "size": None, "exposure": None, "engine": None, "preview": False, "lines": True,
            "outliner": None, "pose": None, "at": None, "up": None}
    i = 3
    while i < len(argv):
        a = argv[i]
        if a == "--preview":
            opts["preview"] = True; i += 1
        elif a == "--no-lines":
            opts["lines"] = False; i += 1
        elif a in ("--views", "--direction", "--group", "--size", "--exposure", "--engine", "--outliner", "--pose", "--at", "--up") and i + 1 < len(argv):
            opts[a[2:]] = argv[i + 1]; i += 2
        else:
            raise SystemExit(f"unknown argument {a}")
    planned = []
    try:
        for name in [v for v in (opts["views"] or "").split(",") if v]:
            planned.append((name.lower(), *views.stands(name)))
        if opts["direction"] is not None:
            planned.append((CUSTOM, *views.direction(opts["direction"])))
        if not planned:
            planned.append(("iso", *views.stands("iso")))
        if opts["up"] is not None:
            planned = [(name, *views.turned((stands, up), views.up(opts["up"]))) for name, stands, up in planned]
    except views.ViewError as e:
        raise SystemExit(str(e))
    if len({name for name, _, _ in planned}) != len(planned):
        raise SystemExit("--views: a view is named twice")
    if opts["outliner"] is not None and opts["outliner"] not in OUTLINERS:
        raise SystemExit(f"--outliner: one of {', '.join(OUTLINERS)}, not {opts['outliner']!r}")
    opts["planned"] = planned
    try:
        opts["at"] = joints.given(opts["at"]) or None
    except joints.PoseError as e:
        raise SystemExit(f"--at: {e}")
    if opts["exposure"] is not None:
        try:
            opts["exposure"] = float(opts["exposure"])
        except ValueError:
            raise SystemExit(f"--exposure: expected a number of stops, got {opts['exposure']!r}")
    if opts["size"] is not None:
        size = opts["size"].lower().split("x")
        if len(size) != 2 or not all(s.isdigit() and int(s) > 0 for s in size):
            raise SystemExit(f"--size: expected WIDTHxHEIGHT in pixels, got {opts['size']!r}")
        opts["size"] = (int(size[0]), int(size[1]))
    return Path(argv[0]), Path(argv[1]), Path(argv[2]), opts


def main(argv):
    project_dir, meshes_path, out_dir, opts = options(argv)
    try:
        project = load_scene_only(project_dir)
    except ManifestError as e:
        print(e, file=sys.stderr)
        return 2
    group = opts["group"]
    if group is not None:
        if group not in project.scene.assemblies:
            raise SystemExit(f"--group: {group!r} is not an assembly id in the scene; its assemblies: {', '.join(project.scene.assemblies)}")
        if group == project.scene.root_id:
            group = None            # the root is the whole scene
    motion = at = worlds = None
    if opts["pose"] is not None or opts["at"]:
        if not (project.dir / joints.FILE).is_file():
            raise SystemExit(f"--pose and --at move the joints of a scene, and {project_dir} has no {joints.FILE} beside its scene.json")
        try:
            motion = joints.load(project.dir / joints.FILE, project.scene)
        except joints.MotionError as e:
            print(e, file=sys.stderr)
            return 2
        try:
            at = joints.where(motion, opts["pose"], opts["at"])
        except joints.PoseError as e:
            raise SystemExit(f"{'--pose' if opts['pose'] is not None and not opts['at'] else '--pose, --at'}: {e}")
        # what a joint has taken from where the scene has it; an occurrence whose joints are all at zero stays put
        worlds = {oid: world for oid, world in joints.worlds(motion, project.scene, at).items()
                  if any(at[j] for j in motion.moved[oid])}
    meshes = read_meshes(meshes_path, project)
    settings, settings_path = load_settings(project.dir)
    # a still is exposed for its colours, not as a manual's high-key pictures are
    settings["exposure"] = opts["exposure"] if opts["exposure"] is not None else settings["still_exposure"]
    t0 = time.time()
    r = Renderer(project, meshes, settings, out_dir, opts["preview"], opts["engine"], opts["lines"], opts["outliner"])
    r.out.mkdir(parents=True, exist_ok=True)
    stem = "still-" + (slug(group) + "-" if group is not None else "")
    if motion is not None:
        stem += f"pose-{slug(opts['pose'])}-" if opts["pose"] is not None else "at-"
    pictures = []
    for name, stands, up in opts["planned"]:
        rec = r.render_still(stem + views.file_name(name), stands, up, group, opts["size"], worlds)
        rec["view"] = name
        pictures.append(rec)
        log(f"{rec['id']}: {rec['width']}x{rec['height']} in {rec['seconds']}s" + ("" if rec["framed"] else "  WARNING: content clipped"))
        if not rec["framed"]:
            r.checks["problems"].append(f"{rec['id']}: what is drawn does not fit the image")
    receipt = {
        "kind": "mechanical-docs-stills-receipt", "generated_at_utc": receipts.utc_now(),
        "blender": bpy.app.version_string, "python": sys.version.split()[0], "engine": r.engine, "denoiser": r.denoiser,
        "preview": opts["preview"], "samples": r.samples(), "exposure": settings["exposure"], "floor_shadow_catcher": r.floor is not None,
        "lines": r.lines_enabled, "outliner": r.outliner, "lines_max_triangles": settings["lines"]["preview_max_triangles" if opts["preview"] else "max_triangles"],
        "settings_file": str(settings_path.relative_to(project.dir)) if settings_path else None,
        "settings_sha256": receipts.sha256_text(json.dumps(settings, sort_keys=True)),
        "project_dir": str(project.dir), "scene_id": project.scene.id, "scene_units": project.scene.units, "unit_factor_to_m": r.factor,
        "native_up_axis": project.scene.native_up_axis, "occurrences": len(project.scene.occurrences), "parts": len(project.scene.parts),
        "input_hashes": project.input_hashes(), "meshes_json_sha256": receipts.sha256_file(meshes_path),
        "mesh_hashes": {pid: rec["mesh"]["sha256"] for pid, rec in meshes["parts"].items()},
        "part_looks": r.looks, "group": group,
        **({"motion": {"file": joints.FILE, "sha256": motion.sha256, "source": motion.source}, "pose": opts["pose"],
            "joint_values_given": opts["at"] or {}, "joint_values": {j: round(v, 6) + 0.0 for j, v in sorted(at.items())},
            "moved_occurrences": sorted(worlds)}
           if motion is not None else {}),
        "views": pictures, "checks": r.checks, "warnings": r.warnings,
        "all_checks_passed": not r.checks["problems"] and all(c["passed"] for c in r.checks["mesh_bounds_match"]) and all(c["passed"] for c in r.checks["restoration"]),
        "not_checked": ["image legibility (inspect the PNGs)", "insertion path or tool access", "physical assembly"],
        "seconds": round(time.time() - t0, 1),
    }
    receipts.write_json(out_dir / "stills.json", receipt)
    log(f"wrote {out_dir / 'stills.json'}: {len(pictures)} picture(s) in {receipt['seconds']}s; checks passed: {receipt['all_checks_passed']}")
    for w in r.warnings:
        log("WARNING:", w)
    return 0 if receipt["all_checks_passed"] else 1


if __name__ == "__main__":
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
    sys.exit(main(argv))
