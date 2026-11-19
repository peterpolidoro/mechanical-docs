"""A moving picture outside a manual, run inside Blender: a turntable, an exploded sequence, the steps of a project,
a joint taken through its range, or one pose going over into another.

    blender -b --python mechanical_docs/motion.py -- PROJECT_DIR MESHES_JSON OUT_DIR turntable [--group ASSEMBLY_ID]
                                                     [--frames 72] [--elevation DEG] [--start DEG]
    blender -b --python mechanical_docs/motion.py -- PROJECT_DIR MESHES_JSON OUT_DIR exploded [--frames 36] [--hold 12] [--return]
                                                     [--view iso | --direction X,Y,Z]
    blender -b --python mechanical_docs/motion.py -- PROJECT_DIR MESHES_JSON OUT_DIR steps [--frames 18] [--hold 8]
                                                     [--view iso | --direction X,Y,Z]
    blender -b --python mechanical_docs/motion.py -- PROJECT_DIR MESHES_JSON OUT_DIR joint NAME [--pose POSE] [--frames 36] [--hold 12]
                                                     [--view iso | --direction X,Y,Z] [--group ASSEMBLY_ID]
    blender -b --python mechanical_docs/motion.py -- PROJECT_DIR MESHES_JSON OUT_DIR pose FROM TO [--and-back] [--frames 36] [--hold 12]
                                                     [--view iso | --direction X,Y,Z] [--group ASSEMBLY_ID]
    the four whose camera stands still also with  [--up +y]
    each with  [--fps 24] [--size WxH] [--exposure STOPS] [--engine E] [--preview] [--lines] [--outliner freestyle|line-art|mixed]
               [--webm] [--frames-only]

PROJECT_DIR and MESHES_JSON are what still.py takes: a directory with a
`scene.json` and its assets, and the CAD stage's receipt for it; `finishes.json`
and `render.json` are used when they are there, and every part is drawn in its
look as a still draws it, with a still's exposure (`still_exposure`, or
`--exposure`). `steps` also needs the project's `instructions.json` with its
`inventory.json`, and follows the build scope when there is one. `joint` and
`pose` need the scene's `motion.json` (joints.py), which nothing else reads.

**turntable.** The whole scene, or one subassembly with `--group`, at its
canonical poses. The camera goes once round the vertical axis through the
middle of what is drawn, starting where the view `iso` stands (`--start`, in
degrees from +X towards +Y) at that view's height (`--elevation`, degrees above
the horizontal), counter-clockwise as seen from above, in `--frames` frames.
The picture has one scale, the one that holds everything at every frame, so it
does not breathe, and the studio's lights turn with the camera, so that what
the camera sees is lit from the same side all the way round. Played again and
again it closes.

**exploded.** The top-level groups of the scene, every child assembly of the
root with all that is under it and the parts directly under the root, move
apart as rigid bodies from where they are installed to the offsets of the
exploded view (explode.py; `exploded_view` in render.json overrides a group's
offset), in `--frames` frames that start and end slowly, with `--hold` frames
at rest before and after. `--return` brings them together again. The camera
stands still, where `exploded_view.direction` or `overview_direction` puts it
unless `--view` or `--direction` says otherwise, and frames both ends.

**steps.** In the order of the instructions, what a step adds arrives at its
seat in `--frames` frames and rests there for `--hold` frames, while what
earlier steps added stays and what later steps add is not there yet. An
occurrence starts from the start offset of the step's approach hint when the
hint is for it; else from where its top-level group is in the exploded view;
else from straight above, by a third of the scene's diagonal. A step whose
additions are all outside the build scope is shown and then taken away again,
as the manual's own step image shows it. The camera is the first step's
instruction view, as the manual's overview has it, unless `--view` or
`--direction` says otherwise, and frames every pose of the sequence.

**joint.** The joint NAME of `motion.json` goes from its lower limit to its
upper one in `--frames` frames that start and end slowly, rests there for
`--hold` frames, comes back the same way and rests again; played again and
again it closes. What the joint moves turns about its line or slides along it,
and what joints further in move goes with it. A joint that follows it, as a
gear follows the gear it meshes with, goes with it at its ratio; such a joint
cannot be asked for by itself. A joint that the scene holds in several places
(`NAME@WHERE`) goes in all of them at once when the bare NAME is given. The
other joints are at zero, where the scene has everything, or where `--pose`
puts them.

**pose.** Every joint goes from its value in the pose FROM to its value in the
pose TO, all of them in step, so that each has come the same share of its way
at every frame, with `--hold` frames at rest before and after; `--and-back`
brings them back. A joint that a pose does not name is at zero in it.

For both, the camera stands still where `overview_direction` puts it unless
`--view` or `--direction` says otherwise, and frames everything the sequence
draws: what stands still, and what moves at every place it comes to. `--group`
draws one subassembly alone, as a turntable does, where the rest of the scene
would stand in front of what moves; what the joints move outside it is then
not drawn.

`--up` names what points up in the picture of a camera that stands still, as
an axis (`+y`) or as X,Y,Z, where Z is not wanted (views.py). A steps sequence
that takes its camera from the instructions takes its up from them too, so
there `--up` goes with `--view` or `--direction`.

Frames are drawn without outlines unless `--lines` asks for them (Freestyle
costs far more than the picture on real geometry, for every frame; what draws
them is render.json's `lines.outliner`, or `--outliner`, as in the render
stage, and Line Art draws a whole assembly in seconds) and without
the shadow-catcher floor, which costs Cycles a second pass for every frame (add
`turntable`, `exploded-sequence`, `steps-sequence`, `joint-sequence` or
`pose-sequence` to `floor.views` in render.json for it; the manual's own
exploded view is the kind `exploded`).
OUT_DIR gets

    <name>-frames/frame-0001.png ...     the frames, on a transparent background as the render stage draws them
    <name>.mp4                           the frames over white, H.264 (`--webm`: <name>.webm, VP9)
    <name>.json                          the receipt of this run

where <name> is `turntable`, `turntable-<group>`, `exploded`, `steps`,
`joint-<joint>` or `pose-<from>-to-<to>`, the last two with `-<group>` after
them for a subassembly alone. A video of an earlier run under the
same name that this run does not write again is taken away. The
video is written by Blender's own FFmpeg, which both the Guix Blender and the
`bpy` wheel have, from the frames as they lie on disk; `--frames-only` stops
before it. The receipt records versions, engine, exposure, the settings' hash,
the hashes of the scene, the assets, the finishes and the meshes, the look
every part was drawn with, what is shown, the camera, each frame with its
hash and what places it (the angle turned, how far apart, the step and how far
its additions have come, the value of every joint), the offsets the parts moved
by and where each came from, for a joint or a pose `motion.json` with its hash
and the joints as it has them, the video with its hash and what Blender reads
back of it (frames, size, rate), and the checks: mesh bounds against the CAD
stage's, canonical poses restored after every frame, a turntable's lights where
they were in the camera's picture at every frame, the video's frame count and
size.

A moving picture is an illustration. An exploded sequence moves groups by
offsets chosen to show them and implies no order; a steps sequence shows the
order the instructions state and nothing else: where a part comes from in it is
no insertion path, and no fastener, tool or access is implied. A joint or a
pose shows where the record of the joints says the parts can go; nothing is
checked on the way, and parts may pass through each other.
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

from mechanical_docs import explode, joints, receipts, timeline, views  # noqa: E402
from mechanical_docs import transforms as T  # noqa: E402
from mechanical_docs.manifest import ManifestError, load_project, load_scene_only  # noqa: E402
from mechanical_docs.names import slug  # noqa: E402
from mechanical_docs.render import Renderer, aabb_of, log, read_meshes  # noqa: E402  (imports bpy: only inside Blender)
from mechanical_docs.render_settings import OUTLINERS, load_settings  # noqa: E402

import bpy  # noqa: E402
from mathutils import Vector  # noqa: E402

SEQUENCES = ("turntable", "exploded", "steps", "joint", "pose")
NAMED = {"joint": 1, "pose": 2}     # what follows the sequence's own name: a joint; the pose it starts in and the pose it ends in
DEFAULT_FRAMES = {"turntable": 72, "exploded": 36, "steps": 18, "joint": 36, "pose": 36}
DEFAULT_HOLD = {"turntable": 0, "exploded": 12, "steps": 8, "joint": 12, "pose": 12}
DEFAULT_FPS = 24
LIFT_OF_DIAGONAL = 1.0 / 3.0        # where a part without an approach hint or an exploded offset comes from: straight above
BACKGROUND = (1.0, 1.0, 1.0)        # what the frames lie over in the video
CONTAINERS = {"mp4": ("MPEG4", "H264"), "webm": ("WEBM", "WEBM")}
# what a frame of each sequence is called where the settings name kinds of views (`floor.views`): not the
# manual's own `exploded` and `step`, so that what a project set for its manual does not reach into a video
KINDS = {"turntable": "turntable", "exploded": "exploded-sequence", "steps": "steps-sequence", "joint": "joint-sequence",
         "pose": "pose-sequence"}
LIGHTS_TOL = 1e-5                   # of a light's distance from the turntable's axis: how far it may stray in the camera's picture


def options(argv):
    """(project directory, mesh receipt, output directory, sequence, options) from the command line."""
    if len(argv) < 4 or argv[3] not in SEQUENCES:
        raise SystemExit(__doc__)
    sequence = argv[3]
    named = argv[4:4 + NAMED.get(sequence, 0)]
    if len(named) < NAMED.get(sequence, 0) or any(n.startswith("--") for n in named):
        raise SystemExit("joint: name the joint, as motion.json has it" if sequence == "joint" else
                         "pose: name two poses of motion.json, the one the sequence starts in and the one it ends in")
    opts = {"group": None, "frames": None, "hold": None, "fps": str(DEFAULT_FPS), "elevation": None, "start": None, "view": None,
            "direction": None, "size": None, "exposure": None, "engine": None, "pose": None, "outliner": None, "up": None, "preview": False,
            "lines": False, "return": False, "and-back": False, "webm": False, "frames-only": False}
    flags = ("preview", "lines", "return", "and-back", "webm", "frames-only")
    i = 4 + len(named)
    while i < len(argv):
        a = argv[i]
        if a.startswith("--") and a[2:] in flags:
            opts[a[2:]] = True; i += 1
        elif a.startswith("--") and a[2:] in opts and i + 1 < len(argv):
            opts[a[2:]] = argv[i + 1]; i += 2
        else:
            raise SystemExit(f"unknown argument {a}")
    still = ("exploded", "steps", "joint", "pose")          # the sequences whose camera stands still
    for name, sequences in (("group", ("turntable", "joint", "pose")), ("elevation", ("turntable",)), ("start", ("turntable",)), ("return", ("exploded",)),
                            ("pose", ("joint",)), ("and-back", ("pose",)), ("view", still), ("direction", still), ("hold", still),
                            ("up", still)):
        if opts[name] not in (None, False) and sequence not in sequences:
            raise SystemExit(f"--{name} belongs to {', '.join(sequences[:-1]) + ' and ' + sequences[-1] if len(sequences) > 1 else sequences[0]}, "
                             f"not to {sequence}")
    opts["named"] = named
    if opts["outliner"] is not None and opts["outliner"] not in OUTLINERS:
        raise SystemExit(f"--outliner: one of {', '.join(OUTLINERS)}, not {opts['outliner']!r}")
    if opts["outliner"] is not None and not opts["lines"]:
        raise SystemExit("--outliner says what draws the outlines, and a moving picture has none unless --lines asks for them")

    def whole(name, default, least):
        value = opts[name]
        if value is None:
            return default
        if not str(value).isdigit() or int(value) < least:
            raise SystemExit(f"--{name}: expected a whole number of at least {least}, got {value!r}")
        return int(value)

    def number(name):
        if opts[name] is None:
            return None
        try:
            return float(opts[name])
        except ValueError:
            raise SystemExit(f"--{name}: expected a number, got {opts[name]!r}")

    opts["frames"] = whole("frames", DEFAULT_FRAMES[sequence], 1)
    opts["hold"] = whole("hold", DEFAULT_HOLD[sequence], 1 if sequence == "steps" else 0)
    opts["fps"] = whole("fps", DEFAULT_FPS, 1)
    for name in ("elevation", "start", "exposure"):
        opts[name] = number(name)
    if opts["view"] is not None and opts["direction"] is not None:
        raise SystemExit("--view names where the camera stands and --direction gives it: one or the other")
    try:
        opts["stands"] = (views.stands(opts["view"]) if opts["view"] is not None else
                          views.direction(opts["direction"]) if opts["direction"] is not None else None)
        if opts["up"] is not None:
            opts["up"] = views.up(opts["up"])
            if opts["stands"] is not None:
                opts["stands"] = views.turned(opts["stands"], opts["up"])
            elif sequence == "steps":
                raise SystemExit("--up turns a camera that --view or --direction places; without them a steps sequence takes "
                                 "its camera, and what is up in it, from the instructions")
    except views.ViewError as e:
        raise SystemExit(str(e))
    if opts["size"] is not None:
        size = opts["size"].lower().split("x")
        if len(size) != 2 or not all(s.isdigit() and int(s) > 0 for s in size):
            raise SystemExit(f"--size: expected WIDTHxHEIGHT in pixels, got {opts['size']!r}")
        opts["size"] = (int(size[0]), int(size[1]))
    return Path(argv[0]), Path(argv[1]), Path(argv[2]), sequence, opts


def encode(frames_dir, names, size, fps, out_path, container):
    """Write the frames as one video with Blender's own FFmpeg: an image strip over white in a scene of its own,
    so that the frames go into the file as they lie on disk and are not drawn again."""
    scn = bpy.data.scenes.new("md_video")
    scn.render.resolution_x, scn.render.resolution_y = size
    scn.render.resolution_percentage = 100
    scn.render.fps = fps
    scn.render.fps_base = 1.0
    scn.frame_start, scn.frame_end = 1, len(names)
    scn.view_settings.view_transform = "Standard"
    scn.view_settings.look = "None"
    scn.view_settings.exposure = 0.0
    scn.view_settings.gamma = 1.0
    editor = scn.sequence_editor_create()
    strips = editor.strips if hasattr(editor, "strips") else editor.sequences       # Blender 4.4 renamed them
    try:
        under = strips.new_effect("background", "COLOR", 1, 1, length=len(names))
    except TypeError:                                                                # before 4.4 a strip has an end, not a length
        under = strips.new_effect("background", "COLOR", 1, 1, frame_end=len(names) + 1)
    under.color = BACKGROUND
    strip = strips.new_image("frames", str(frames_dir / names[0]), 2, 1)
    for name in names[1:]:
        strip.elements.append(name)
    strip.blend_type = "ALPHA_OVER"
    scn.render.image_settings.file_format = "FFMPEG"
    scn.render.ffmpeg.format, scn.render.ffmpeg.codec = CONTAINERS[container]
    scn.render.ffmpeg.constant_rate_factor = "HIGH"
    scn.render.ffmpeg.ffmpeg_preset = "GOOD"
    scn.render.ffmpeg.gopsize = max(1, fps)
    scn.render.ffmpeg.audio_codec = "NONE"
    scn.render.use_file_extension = False
    scn.render.filepath = str(out_path)
    if out_path.exists():
        out_path.unlink()
    bpy.ops.render.render(animation=True, scene=scn.name)
    bpy.data.scenes.remove(scn)
    if not out_path.is_file() or out_path.stat().st_size == 0:
        raise SystemExit(f"{out_path}: Blender's FFmpeg wrote no video; the frames are in {frames_dir} (--frames-only stops there)")


def read_back(path):
    """What Blender reads of a video it is given: frames, size, rate. Its own check of what it wrote."""
    clip = bpy.data.movieclips.load(str(path))
    try:
        return {"frames": int(clip.frame_duration), "width": int(clip.size[0]), "height": int(clip.size[1]), "fps": round(float(clip.fps), 4)}
    finally:
        bpy.data.movieclips.remove(clip)


def main(argv):
    project_dir, meshes_path, out_dir, sequence, opts = options(argv)
    try:
        if sequence == "steps":
            if not (project_dir / "instructions.json").is_file():
                raise SystemExit(f"steps follows a project's instructions, and {project_dir} has no instructions.json; "
                                 "a scene alone has a turntable and an exploded sequence")
            project = load_project(project_dir, require_instructions=True)
        else:
            project = load_scene_only(project_dir)
    except ManifestError as e:
        print(e, file=sys.stderr)
        return 2
    scene = project.scene
    motion = posed = None
    if sequence in NAMED:
        if not (project.dir / joints.FILE).is_file():
            raise SystemExit(f"{sequence} moves the joints of a scene, and {project_dir} has no {joints.FILE} beside its scene.json; "
                             "a scene alone has a turntable and an exploded sequence")
        try:
            motion = joints.load(project.dir / joints.FILE, scene)
        except joints.MotionError as e:
            print(e, file=sys.stderr)
            return 2
        try:
            if sequence == "joint":
                swept = joints.meant(motion, opts["named"][0])
                if not swept:
                    raise SystemExit(f"joint: {opts['named'][0]!r} is not a joint of {joints.FILE}; it has {', '.join(sorted(motion.joints)) or 'none'}")
                led = [j for j in swept if "follows" in motion.joints[j]]
                if led:
                    leader = motion.joints[led[0]]["follows"]["joint"]
                    raise SystemExit(f"joint: {led[0]!r} follows {leader!r} and goes where that joint takes it; ask for {leader!r}, "
                                     "which moves it too")
                if not any(joints.moved_by(motion, j) for s in swept for j in [s] + joints.followers(motion, s)):
                    raise SystemExit(f"joint: {opts['named'][0]!r} moves no occurrence of the scene; there is nothing to draw moving")
                others = joints.values(motion, opts["pose"])
                # each joint through its own range, all of them at once; what follows them is set from them
                ways = [timeline.joint_values(motion.joints[j]["lower"], motion.joints[j]["upper"], opts["frames"], opts["hold"]) for j in swept]
                posed = [joints.settled(motion, dict(others, **dict(zip(swept, now)))) for now in zip(*ways)]
            else:
                posed = [joints.settled(motion, at) for at in
                         timeline.pose_values(joints.values(motion, opts["named"][0]), joints.values(motion, opts["named"][1]),
                                              opts["frames"], opts["hold"], opts["and-back"])]
        except (joints.PoseError, timeline.TimelineError) as e:
            raise SystemExit(f"{sequence}: {e}")
    group = opts["group"]
    if group is not None:
        if group not in scene.assemblies:
            raise SystemExit(f"--group: {group!r} is not an assembly id in the scene; its assemblies: {', '.join(scene.assemblies)}")
        if group == scene.root_id:
            group = None
    meshes = read_meshes(meshes_path, project)
    settings, settings_path = load_settings(project.dir)
    settings["exposure"] = opts["exposure"] if opts["exposure"] is not None else settings["still_exposure"]
    name = sequence + ("-" + slug(group) if group is not None else "")
    if sequence in NAMED:
        name = sequence + "-" + "-to-".join(slug(n) for n in opts["named"]) + ("-" + slug(group) if group is not None else "")
    frames_dir = out_dir / f"{name}-frames"
    container = "webm" if opts["webm"] else "mp4"
    if opts["size"] is not None and not opts["frames-only"] and container == "mp4" and (opts["size"][0] % 2 or opts["size"][1] % 2):
        raise SystemExit(f"--size: H.264 takes even numbers of pixels, got {opts['size'][0]}x{opts['size'][1]}; "
                         "give even ones, or --webm, or --frames-only")
    t0 = time.time()
    r = Renderer(project, meshes, settings, frames_dir, opts["preview"], opts["engine"], opts["lines"], opts["outliner"])
    if frames_dir.is_dir():
        for stale in frames_dir.glob("frame-*.png"):       # a shorter run must not leave frames of a longer one behind
            stale.unlink()
    frames_dir.mkdir(parents=True, exist_ok=True)
    for other in CONTAINERS:                               # nor a video that this run does not write again: the receipt would lie beside it
        if (opts["frames-only"] or other != container) and (out_dir / f"{name}.{other}").is_file():
            (out_dir / f"{name}.{other}").unlink()
    if opts["size"] is None:
        r.set_resolution(r.long_side(), settings["aspect"])
    else:
        r.scn.render.resolution_x, r.scn.render.resolution_y = opts["size"]
        r.scn.render.resolution_percentage = 100
    size = (r.scn.render.resolution_x, r.scn.render.resolution_y)
    if not opts["frames-only"] and container == "mp4" and (size[0] % 2 or size[1] % 2):
        raise SystemExit(f"the settings give a picture of {size[0]}x{size[1]} pixels and H.264 takes even numbers; give --size, or --webm, or --frames-only")
    to_m = T.unit_factor("mm", "m")

    def corners(oid, offset_mm=None):
        pts = r.occurrence_corners(oid)
        off = Vector(offset_mm) * to_m if offset_mm is not None else None
        return [p + off for p in pts] if off is not None else pts

    def name_of(n):
        return f"frame-{n:04d}"

    frames = []
    described = {"sequence": sequence, "group": group}
    if sequence == "turntable":
        members = r.group_members(group) if group is not None else list(r.obj_of)
        if not members:
            raise SystemExit(f"--group: assembly {group!r} has no occurrences")
        pts = [p for oid in members for p in corners(oid)]
        mn, mx = aabb_of(pts)
        target = (mn + mx) / 2
        try:
            path = timeline.turntable(opts["frames"], timeline.ISO_ELEVATION_DEG if opts["elevation"] is None else opts["elevation"],
                                      timeline.ISO_AZIMUTH_DEG if opts["start"] is None else opts["start"])
            scale = timeline.ortho_scale([tuple(p) for p in pts], tuple(target), [(stands, timeline.UP) for _, stands in path],
                                         size[0], size[1], settings["fill"])
        except timeline.TimelineError as e:
            raise SystemExit(str(e))
        reach = (mx - mn).length
        r.turn_lights()
        rest = [lo.location.copy() for lo in r.lights]
        first, strayed = None, 0.0
        for n, (turned, stands) in enumerate(path, 1):
            r.turn_lights(turned, target)                 # round the camera's axis, not the scene's
            r.frame_camera(stands, timeline.UP, target, scale, reach)
            # where each light is in the camera's own frame: the same at every frame, or the lighting changes on the way round
            seen = [r.cam.matrix_world.inverted() @ lo.location for lo in r.lights]
            first = first or seen
            strayed = max([strayed] + [(a - b).length for a, b in zip(seen, first)])
            frames.append(r.render_frame(name_of(n), members, kind=KINDS[sequence], turned_deg=round(turned * 180.0 / 3.141592653589793, 4),
                                         stands=[round(v, 6) for v in stands]))
            log(f"{name} {n}/{len(path)}: {frames[-1]['seconds']}s")
        r.turn_lights()
        allowed = LIGHTS_TOL * max([(Vector((at.x - target.x, at.y - target.y, 0.0))).length for at in rest] + [1e-3])
        if strayed > allowed:
            r.checks["problems"].append(f"{name}: a light strays {strayed:.6f} m in the camera's picture during the turn; the lighting changes on the way round")
        described.update({"shown": members, "camera": {"type": "ORTHO", "target_m": [round(v, 6) for v in target], "ortho_scale_m": scale,
                                                        "elevation_deg": timeline.ISO_ELEVATION_DEG if opts["elevation"] is None else opts["elevation"],
                                                        "start_deg": timeline.ISO_AZIMUTH_DEG if opts["start"] is None else opts["start"],
                                                        "turns": 1.0, "lights_turn_with_the_camera": True,
                                                        "lights_stray_in_the_camera_s_frame_m": round(strayed, 9), "lights_may_stray_m": round(allowed, 9)}})
    else:
        members = r.group_members(group) if group is not None else list(r.obj_of)
        if not members:
            raise SystemExit(f"--group: assembly {group!r} has no occurrences")
        plan, moves, placed = None, {}, {}
        if motion is None:
            try:
                plan = explode.resolve(scene, meshes, settings)
            except ValueError as e:
                raise SystemExit(str(e))
            offsets_mm = plan["offsets_mm"]
        if motion is not None:
            # where everything that a joint moves is at each set of values the sequence comes to, worked out once for each
            drawn = set(members)
            for at in posed:
                key = tuple(sorted(at.items()))
                if key not in placed:
                    placed[key] = {oid: world for oid, world in joints.worlds(motion, scene, at).items() if oid in drawn}
            timed = [("joints", at) for at in posed]
            varying = sorted(j for j in motion.joints if len({at[j] for at in posed}) > 1)
            if group is not None and not any(set(names) & set(varying) for oid, names in motion.moved.items() if oid in drawn):
                raise SystemExit(f"--group: nothing of {group!r} moves in this sequence; there is nothing to draw moving")
            described.update({"motion": {"file": joints.FILE, "sha256": motion.sha256, "source": motion.source}, "joints": motion.joints,
                              "varying_joints": varying,
                              "moving_occurrences": [oid for oid, names in motion.moved.items() if set(names) & set(varying) and oid in drawn],
                              **({"joint": opts["named"][0], "joints_swept": swept, "other_joints_at": opts["pose"] or "zero"}
                                 if sequence == "joint" else
                                 {"from_pose": opts["named"][0], "to_pose": opts["named"][1], "returns": opts["and-back"]})})
        elif sequence == "exploded":
            moves = {oid: offsets_mm[g["id"]] for g in plan["groups"] for oid in g["occurrence_ids"]}
            if not any(any(abs(v) > 1e-9 for v in off) for off in moves.values()):
                raise SystemExit("exploded: no top-level group of this scene moves in its exploded view; there is nothing to draw apart")
            try:
                fractions = timeline.exploded_fractions(opts["frames"], opts["hold"], opts["return"])
            except timeline.TimelineError as e:
                raise SystemExit(str(e))
            timed = [(None, f) for f in fractions]
            sources = None
            described.update({"offsets_mm": offsets_mm,
                              "groups": [{"id": g["id"], "offset_mm": g["offset_mm"], "source": g["source"], "occurrences": len(g["occurrence_ids"])}
                                         for g in plan["groups"]], "returns": opts["return"]})
        else:
            pts_now = [p for oid in members for p in corners(oid)]
            mn, mx = aabb_of(pts_now)
            lift_mm = (mx - mn).length * LIFT_OF_DIAGONAL / to_m
            starts = timeline.step_starts(scene, r.states, offsets_mm, lift_mm)
            moves = {oid: off for oid, (off, _) in starts.items()}
            sources = {oid: source for oid, (_, source) in starts.items()}
            try:
                timed = timeline.step_frames(len(r.states), opts["frames"], opts["hold"])
            except timeline.TimelineError as e:
                raise SystemExit(str(e))
            described.update({"steps": [{"index": st.index, "id": st.step.id, "adds": st.added, "deferred": st.deferred} for st in r.states],
                              "starts": [{"occurrence_id": oid, "offset_mm": [round(v, 3) for v in moves[oid]], "source": sources[oid]}
                                         for st in r.states for oid in st.added]})
        # one camera for the whole sequence, framing every pose of it: seated, and as far out as anything goes;
        # for joints, what stands still and what moves at every place it comes to
        if motion is not None:
            pts = ([p for oid in members if oid not in motion.moved for p in corners(oid)]
                   + [p for worlds in placed.values() for oid, world in worlds.items() for p in r.occurrence_corners(oid, world)])
        else:
            pts = [p for oid in members for p in corners(oid)] + [p for oid, off in moves.items() for p in corners(oid, off)]
        mn, mx = aabb_of(pts)
        first_view = project.instructions.views[project.instructions.steps[0].view] if sequence == "steps" and opts["stands"] is None else None
        if first_view is not None:
            r.aim(Vector(first_view.eye) * r.factor, Vector(first_view.target) * r.factor, Vector(first_view.up))
            framed = r.fit(pts, first_view.projection, settings["fill"])
            camera = {"from": f"instruction view {first_view.id!r}", "projection": first_view.projection}
        else:
            if opts["stands"] is not None:
                stands, up = opts["stands"]
            else:
                stands, up = (plan["direction"] if plan else None) or settings["overview_direction"], timeline.UP
                if opts["up"] is not None:
                    try:
                        stands, up = views.turned((stands, up), opts["up"])
                    except views.ViewError as e:
                        raise SystemExit(str(e))
            d = Vector(stands).normalized()
            ctr = (mn + mx) / 2
            r.aim(ctr + d * max(r.scene_radius * 4, (mx - mn).length * 4, 1e-3), ctr, Vector(up))
            framed = r.fit(pts, "orthographic", settings["fill"])
            camera = {"from": opts["view"] or ("--direction" if opts["direction"] is not None else "settings"),
                      "projection": "orthographic", "stands": [round(v, 6) for v in d], "up": [float(v) for v in up]}
        if not framed:
            r.checks["problems"].append(f"{name}: what is drawn does not fit the picture")
        camera.update({"type": r.cam.data.type, "ortho_scale_m": r.cam.data.ortho_scale if r.cam.data.type == "ORTHO" else None,
                       "location_m": list(r.cam.matrix_world.translation)})
        described["camera"] = camera
        for n, (step, fraction) in enumerate(timed, 1):
            if step == "joints":                          # a joint or a pose: what the joints move, where these values put it
                at = fraction
                frames.append(r.render_frame(name_of(n), members, kind=KINDS[sequence], worlds=placed[tuple(sorted(at.items()))],
                                             values={j: round(v, 6) for j, v in sorted(at.items())}))
                log(f"{name} {n}/{len(timed)}: {frames[-1]['seconds']}s")
                continue
            if step is None:                              # exploded: every group that far out
                shown = members
                offsets_m = {oid: [v * fraction * to_m for v in off] for oid, off in moves.items()} if fraction else None
                extra = {"apart": round(fraction, 6)}
            else:                                         # steps: what is installed, and this step's additions on their way in
                st = r.states[step]
                shown = st.before + st.added
                offsets_m = {oid: [v * (1.0 - fraction) * to_m for v in moves[oid]] for oid in st.added} if fraction < 1.0 else None
                extra = {"step": st.index, "step_id": st.step.id, "arrived": round(fraction, 6)}
            frames.append(r.render_frame(name_of(n), shown, offsets_m, kind=KINDS[sequence], **extra))
            log(f"{name} {n}/{len(timed)}: {frames[-1]['seconds']}s")
        described["shown"] = members
    video = None
    if not opts["frames-only"]:
        out_path = out_dir / f"{name}.{container}"
        encode(frames_dir, [f["file"] for f in frames], size, opts["fps"], out_path, container)
        seen = read_back(out_path)
        ok = seen["frames"] == len(frames) and (seen["width"], seen["height"]) == size
        ffmpeg = bpy.app.ffmpeg
        video = {"file": out_path.name, "sha256": receipts.sha256_file(out_path), "bytes": out_path.stat().st_size,
                 "container": container, "codec": {"mp4": "H.264", "webm": "VP9"}[container], "background": list(BACKGROUND),
                 "encoder": {"name": "Blender's FFmpeg output", "blender": bpy.app.version_string,
                             "avcodec": ffmpeg.avcodec_version_string, "avformat": ffmpeg.avformat_version_string},
                 "read_back": seen, "passed": ok}
        if not ok:
            r.checks["problems"].append(f"{out_path.name}: Blender reads {seen} of it, and {len(frames)} frames of {size[0]}x{size[1]} went in")
    receipt = {
        "kind": "mechanical-docs-motion-receipt", "generated_at_utc": receipts.utc_now(),
        "blender": bpy.app.version_string, "python": sys.version.split()[0], "engine": r.engine, "denoiser": r.denoiser,
        "preview": opts["preview"], "samples": r.samples(), "exposure": settings["exposure"],
        "floor_shadow_catcher": r.floor is not None and KINDS[sequence] in settings["floor"]["views"],
        "lines": r.lines_enabled, "outliner": r.outliner if r.lines_enabled else None,
        "lines_max_triangles": settings["lines"]["preview_max_triangles" if opts["preview"] else "max_triangles"],
        "settings_file": str(settings_path.relative_to(project.dir)) if settings_path else None,
        "settings_sha256": receipts.sha256_text(json.dumps(settings, sort_keys=True)),
        "project_dir": str(project.dir), "scene_id": scene.id, "scene_units": scene.units, "unit_factor_to_m": r.factor,
        "native_up_axis": scene.native_up_axis, "occurrences": len(scene.occurrences), "parts": len(scene.parts),
        "input_hashes": project.input_hashes(), "meshes_json_sha256": receipts.sha256_file(meshes_path),
        "mesh_hashes": {pid: rec["mesh"]["sha256"] for pid, rec in meshes["parts"].items()},
        "part_looks": r.looks, **described,
        "width": size[0], "height": size[1], "fps": opts["fps"], "frame_count": len(frames),
        "duration_s": round(timeline.duration_s(len(frames), opts["fps"]), 4),
        "frames_dir": frames_dir.name, "frames": frames, "video": video,
        "checks": r.checks, "warnings": r.warnings,
        "all_checks_passed": not r.checks["problems"] and all(c["passed"] for c in r.checks["mesh_bounds_match"]) and all(c["passed"] for c in r.checks["restoration"]),
        "note": "an illustration: offsets are chosen to show the parts and are no insertion paths; no order beyond the instructions', "
                "no fastener, tool or access is implied",
        "not_checked": ["image legibility (look at the frames)", "insertion path or tool access", "physical assembly"],
        "seconds": round(time.time() - t0, 1),
    }
    receipts.write_json(out_dir / f"{name}.json", receipt)
    log(f"wrote {out_dir / (name + '.json')}: {len(frames)} frame(s), {receipt['duration_s']} s at {opts['fps']} a second, in {receipt['seconds']}s; "
        f"video: {video['file'] if video else 'none (--frames-only)'}; checks passed: {receipt['all_checks_passed']}")
    for w in r.warnings:
        log("WARNING:", w)
    return 0 if receipt["all_checks_passed"] else 1


if __name__ == "__main__":
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
    sys.exit(main(argv))
