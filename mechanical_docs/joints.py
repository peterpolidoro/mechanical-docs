"""The joints and poses of a scene: `motion.json`, and where a joint puts what it moves.

`motion.json` lies beside `scene.json`, as `finishes.json` does, and is derived
by `mechanical-cad` from a record a project keeps by hand. That record is a
draft there (2026-11-19) and no part of its layout yet, so this file's form may
still change. It is optional, nothing in a manual reads it, and it is no input
of a mesh or of a manual's views: only the `joint` and `pose` sequences of
motion.py and a still with `--pose` or `--at` (still.py) read it, and their
receipts pin it by its hash.

    {"schema_version": 1,
     "scene": "scene.json",
     "source": {"kind": "mechanical-cad-motion", "file": "motion.toml", "sha256": "…"},
     "joints": {"lever": {"kind": "revolute", "origin_mm": [0, 0, 12], "direction": [0, 1, 0],
                          "lower": -20.0, "upper": 35.0, "unit": "deg"},
                "slide": {"kind": "prismatic", "origin_mm": [40, 0, 12], "direction": [1, 0, 0],
                          "lower": 0.0, "upper": 12.0, "unit": "mm"},
                "pinion": {"kind": "revolute", "origin_mm": [0, 0, 40], "direction": [0, 1, 0],
                           "lower": -87.5, "upper": 50.0, "unit": "deg",
                           "follows": {"joint": "lever", "ratio": -2.5}}},
     "moved": {"lever-1": ["lever"], "lever-1/knob-1": ["lever", "slide"], "pinion-1": ["pinion"]},
     "poses": {"open": {"lever": 30.0}, "closed": {"lever": -20.0, "slide": 0.0}}}

A joint is a line in the scene and a range along or about it. `origin_mm` is a
point on the line, in millimetres whatever the scene's units, and `direction` a
unit vector along it, both in the frame the scene's own transforms are written
in (a scene declared +Y up is turned to +Z up once, and its joints with it).
A `revolute` joint turns what it moves about the line, by degrees, the way a
right-hand screw advances along `direction`; a `prismatic` joint slides it
along the line, by millimetres. `lower` and `upper` are the limits of that
value, and `unit` says which it is (`deg` or `mm`, as the kind has it). The
position the scene is flattened in is every joint's zero, whether or not zero
lies within its limits.

A joint may follow another, as a gear is driven by the gear it meshes with:
`follows` names that joint and gives the ratio, how far this one goes for one
degree or millimetre of it (negative for gears that mesh, which turn against
each other). Such a joint is always at the ratio times the value of the joint
it follows, whatever else is said: every other joint's value is worked out
first, zero or a pose or a place in a sequence, and the followers are set from
them. The joint it follows is in the file and follows nothing itself. Its own
limits are what the ratio makes of that joint's limits, so that it is within
them wherever that joint is within its own. No pose names a follower.

A joint of an assembly that the scene places several times is in the file once
for each place, named `NAME@WHERE` with the id of that place, so a joint's
name may hold `@`, `/`, `:` and spaces. `meant` takes the bare NAME for all of
them at once.

`moved` names every occurrence that moves, by its id in the scene, with the
joints that move it, outermost first: a joint further out carries the joints
further in with it. An occurrence that is not there stands still. With the
joints at the values v, the world transform of an occurrence is

    T(j1, v1) · T(j2, v2) · … · world

where `world` is its transform in the scene and T(j, v) the rotation or the
translation of joint j by v about or along its line as that line lies at zero.
The innermost joint is applied first, about its own line where the scene has
it, and each joint further out then carries the result.

A pose names joints and gives each a value within its limits; a joint it does
not name is at zero, and a follower is where the joint it follows puts it. The
file may hold no poses.

Nothing here needs Blender. A joint moved through its range is an
illustration, like every other moving picture: it shows where the record says
the parts can go, and says nothing of what they meet on the way.
"""
from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path

from . import transforms as T
from .manifest import sha256_file

FILE = "motion.json"
SCHEMA_VERSION = 1
FIELDS = {"schema_version", "scene", "source", "joints", "moved", "poses"}
JOINT_FIELDS = ("kind", "origin_mm", "direction", "lower", "upper", "unit")
FOLLOWS_FIELDS = {"joint", "ratio"}
UNITS = {"revolute": "deg", "prismatic": "mm"}
UNIT_TOL = 1e-6         # how far the length of a direction may be from 1
LIMIT_TOL = 1e-9        # how far beyond a limit a pose's value may be, for a number that went through text
FOLLOW_TOL = 1e-6       # how far a follower's limits may be from its ratio times its leader's, of their size


class MotionError(ValueError):
    def __init__(self, problems):
        self.problems = list(problems)
        super().__init__("\n".join([f"invalid {FILE}:"] + [f"  - {p}" for p in self.problems]))


class PoseError(ValueError):
    """A pose that was asked for by a name the file does not have."""


@dataclass
class Motion:
    source: dict
    joints: dict        # name -> {"kind", "origin_mm", "direction", "lower", "upper", "unit"}, as the file has them,
                        # and "follows": {"joint", "ratio"} for a joint that another one drives
    moved: dict         # occurrence id -> [joint names], outermost first
    poses: dict         # name -> {joint name: value}
    file: Path
    sha256: str


def _number(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v)


def _vec3(v):
    return isinstance(v, list) and len(v) == 3 and all(_number(c) for c in v)


def load(path, scene):
    """Read and check `motion.json` against the scene it lies beside. Raises MotionError with every problem."""
    path = Path(path)
    wrong = []
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
    except FileNotFoundError:
        raise MotionError([f"file not found: {path}"]) from None
    except (OSError, ValueError) as e:
        raise MotionError([f"cannot parse {path}: {e}"]) from None
    if not isinstance(data, dict):
        raise MotionError(["top level must be an object"])
    sv = data.get("schema_version")
    if sv != SCHEMA_VERSION or isinstance(sv, bool):
        wrong.append(f"schema_version must be the integer {SCHEMA_VERSION}, got {sv!r}")
    extra = sorted(set(data) - FIELDS)
    if extra:
        wrong.append(f"unsupported field(s) {extra}; the file has {sorted(FIELDS)}")
    for key in ("scene", "joints", "moved"):
        if key not in data:
            wrong.append(f"missing field {key!r}")
    ref = data.get("scene")
    if not (isinstance(ref, str) and ref):
        wrong.append("scene: expected the scene file's relative path")
    elif (path.parent / ref).resolve() != scene.file.resolve():
        wrong.append(f"scene: {ref!r} is not the loaded scene {scene.file.name!r}")
    source = data.get("source", {})
    if not isinstance(source, dict) or any(isinstance(v, (dict, list)) for v in source.values()):
        wrong.append("source: expected an object of plain values")
        source = {}

    joints = {}
    raw = data.get("joints", {})
    if not isinstance(raw, dict):
        wrong.append("joints: expected an object of named joints")
        raw = {}
    for name, j in raw.items():
        where = f"joints[{name!r}]"
        if not isinstance(j, dict):
            wrong.append(f"{where}: expected an object")
            continue
        extra = sorted(set(j) - set(JOINT_FIELDS) - {"follows"})
        missing = [k for k in JOINT_FIELDS if k not in j]
        if extra:
            wrong.append(f"{where}: unsupported field(s) {extra}; a joint has {list(JOINT_FIELDS)}, and follows when another joint drives it")
        if missing:
            wrong.append(f"{where}: missing field(s) {missing}; every field of a joint is explicit")
            continue
        ok = True
        if j["kind"] not in UNITS:
            wrong.append(f"{where}.kind: expected one of {sorted(UNITS)}, got {j['kind']!r}")
            ok = False
        elif j["unit"] != UNITS[j["kind"]]:
            wrong.append(f"{where}.unit: a {j['kind']} joint is measured in {UNITS[j['kind']]!r}, got {j['unit']!r}")
            ok = False
        if not _vec3(j["origin_mm"]):
            wrong.append(f"{where}.origin_mm: expected three numbers, a point on the joint's line in millimetres, got {j['origin_mm']!r}")
            ok = False
        if not _vec3(j["direction"]):
            wrong.append(f"{where}.direction: expected three numbers, got {j['direction']!r}")
            ok = False
        elif abs(math.sqrt(sum(c * c for c in j["direction"])) - 1.0) > UNIT_TOL:
            wrong.append(f"{where}.direction: expected a unit vector, got {j['direction']!r} of length "
                         f"{math.sqrt(sum(c * c for c in j['direction'])):.9g}")
            ok = False
        if not (_number(j["lower"]) and _number(j["upper"])):
            wrong.append(f"{where}: lower and upper are numbers, got {j['lower']!r} and {j['upper']!r}")
            ok = False
        elif not j["lower"] < j["upper"]:
            wrong.append(f"{where}: lower must be below upper, got {j['lower']!r} and {j['upper']!r}")
            ok = False
        follows = None
        if "follows" in j:
            f = j["follows"]
            if not (isinstance(f, dict) and set(f) == FOLLOWS_FIELDS and isinstance(f["joint"], str)
                    and _number(f["ratio"]) and f["ratio"] != 0):
                wrong.append(f"{where}.follows: expected the joint it follows and the ratio, a number that is not 0: "
                             f'{{"joint": NAME, "ratio": NUMBER}}, got {f!r}')
                ok = False
            elif not isinstance(raw.get(f["joint"]), dict):
                wrong.append(f"{where}.follows: {f['joint']!r} is not among the joints of this file")
                ok = False
            elif "follows" in raw[f["joint"]]:
                wrong.append(f"{where}.follows: {f['joint']!r} follows a joint itself; a joint follows one that goes by itself")
                ok = False
            else:
                follows = {"joint": f["joint"], "ratio": float(f["ratio"])}
        if ok:
            joints[name] = {"kind": j["kind"], "origin_mm": [float(c) for c in j["origin_mm"]], "direction": [float(c) for c in j["direction"]],
                            "lower": float(j["lower"]), "upper": float(j["upper"]), "unit": j["unit"]}
            if follows is not None:
                joints[name]["follows"] = follows
    for name, j in joints.items():      # a follower's limits are what its ratio makes of its leader's: within them wherever the leader is
        leader = joints.get(j["follows"]["joint"]) if "follows" in j else None
        if leader is not None:
            ends = sorted(j["follows"]["ratio"] * leader[end] for end in ("lower", "upper"))
            if any(abs(have - want) > FOLLOW_TOL * max(1.0, abs(want)) for have, want in zip((j["lower"], j["upper"]), ends)):
                wrong.append(f"joints[{name!r}]: it follows {j['follows']['joint']!r} at {j['follows']['ratio']:g} to one, so its limits are "
                             f"{ends[0]:g} to {ends[1]:g} {j['unit']}, got {j['lower']:g} to {j['upper']:g}")
    defined = set(raw)

    moved = {}
    raw_moved = data.get("moved", {})
    if not isinstance(raw_moved, dict):
        wrong.append("moved: expected an object: an occurrence's id, and the joints that move it, outermost first")
        raw_moved = {}
    for oid, names in raw_moved.items():
        where = f"moved[{oid!r}]"
        if oid not in scene.occurrences:
            wrong.append(f"{where}: not an occurrence of the scene")
            continue
        if not (isinstance(names, list) and names and all(isinstance(n, str) for n in names)):
            wrong.append(f"{where}: expected the names of the joints that move it, outermost first, got {names!r}")
            continue
        unknown = [n for n in names if n not in defined]
        if unknown:
            wrong.append(f"{where}: {unknown} {'is' if len(unknown) == 1 else 'are'} not among the joints of this file")
        if len(set(names)) != len(names):
            wrong.append(f"{where}: a joint moves an occurrence once, got {names!r}")
        if not unknown and len(set(names)) == len(names):
            moved[oid] = list(names)

    poses = {}
    raw_poses = data.get("poses", {})
    if not isinstance(raw_poses, dict):
        wrong.append("poses: expected an object of named poses (may be empty)")
        raw_poses = {}
    for name, pose in raw_poses.items():
        where = f"poses[{name!r}]"
        if not isinstance(pose, dict):
            wrong.append(f"{where}: expected an object: a joint's name and its value")
            continue
        good = True
        for jname, value in pose.items():
            if jname not in defined:
                wrong.append(f"{where}: {jname!r} is not among the joints of this file")
                good = False
            elif isinstance(raw[jname], dict) and "follows" in raw[jname]:
                leader = raw[jname]["follows"].get("joint") if isinstance(raw[jname]["follows"], dict) else None
                wrong.append(f"{where}: {jname!r} follows {leader!r} and is where that joint puts it; a pose says where the joint it follows is")
                good = False
            elif not _number(value):
                wrong.append(f"{where}[{jname!r}]: expected a number, got {value!r}")
                good = False
            elif jname in joints and not joints[jname]["lower"] - LIMIT_TOL <= value <= joints[jname]["upper"] + LIMIT_TOL:
                wrong.append(f"{where}[{jname!r}]: {value!r} is outside the joint's limits, {joints[jname]['lower']:g} to "
                             f"{joints[jname]['upper']:g} {joints[jname]['unit']}")
                good = False
        if good:
            poses[name] = {jname: float(value) for jname, value in pose.items()}
    if wrong:
        raise MotionError(wrong)
    return Motion(dict(source), joints, moved, poses, path, sha256_file(path))


def settled(motion, at):
    """Every joint's value, from the values of the joints that go by themselves: {joint name: value}. A joint
    that `at` does not name is at zero; a joint that follows another is at its ratio times where that one is,
    whatever `at` says of it."""
    out = {name: float(at.get(name, 0.0)) for name in motion.joints}
    for name, joint in motion.joints.items():
        if "follows" in joint:
            out[name] = joint["follows"]["ratio"] * out[joint["follows"]["joint"]] + 0.0     # a zero is written 0.0, never -0.0
    return out


def values(motion, pose=None):
    """The value of every joint in a named pose, or with every joint at zero: {joint name: value}."""
    if pose is not None and pose not in motion.poses:
        raise PoseError(f"no pose {pose!r}; {FILE} has {', '.join(sorted(motion.poses)) or 'none'}")
    return settled(motion, motion.poses[pose] if pose is not None else {})


def given(text):
    """What `JOINT=VALUE,JOINT=VALUE` on a command line says: {joint: value}. Raises PoseError."""
    out = {}
    for item in filter(None, (t.strip() for t in (text or "").split(","))):
        name, _, value = item.rpartition("=")
        try:
            out[name.strip()] = float(value)
        except ValueError:
            raise PoseError(f"{item!r}: expected JOINT=VALUE with a number") from None
        if not name.strip():
            raise PoseError(f"{item!r}: expected JOINT=VALUE with a number")
    return out


def where(motion, pose=None, at=None):
    """Every joint's value for a picture: zero, or what the named pose says, or what `at` ({joint: value}) says
    over both. A joint that the scene holds in several places may be given by its bare NAME, for all of them.
    Raises PoseError for a pose or a joint the file does not have, for a value given to a joint that follows
    another, and for a value outside a joint's limits."""
    if pose is not None and pose not in motion.poses:
        raise PoseError(f"no pose {pose!r}; {FILE} has {', '.join(sorted(motion.poses)) or 'none'}")
    out = dict(motion.poses[pose]) if pose is not None else {}
    for name, value in (at or {}).items():
        names = meant(motion, name)
        if not names:
            raise PoseError(f"{name!r} is not a joint of {FILE}; it has {', '.join(sorted(motion.joints)) or 'none'}")
        for j in names:
            joint = motion.joints[j]
            if "follows" in joint:
                raise PoseError(f"{j!r} follows {joint['follows']['joint']!r} and is where that joint puts it; say where that joint is")
            if not joint["lower"] - LIMIT_TOL <= value <= joint["upper"] + LIMIT_TOL:
                raise PoseError(f"{j} = {value:g} {joint['unit']} is outside the joint's limits, {joint['lower']:g} to {joint['upper']:g}")
            out[j] = float(value)
    return settled(motion, out)


def meant(motion, name):
    """The joints a name stands for: the joint of that name, or, for a joint the scene holds in several places
    (`NAME@WHERE`), all of them by the bare NAME. Empty when there is none."""
    return [name] if name in motion.joints else [j for j in motion.joints if j.split("@", 1)[0] == name]


def followers(motion, joint):
    """The joints that follow a joint."""
    return [name for name, j in motion.joints.items() if j.get("follows", {}).get("joint") == joint]


def moved_by(motion, joint):
    """The occurrences a joint moves, in the order the file names them."""
    return [oid for oid, names in motion.moved.items() if joint in names]


def _line(scene, joint):
    """(a point on the joint's line in the scene's units, the unit vector along it), in the +Z-up frame the
    loaded scene's world transforms are in."""
    f = T.unit_factor("mm", scene.units)
    basis = scene.basis_to_z_up
    origin = T.apply(basis, [c * f for c in joint["origin_mm"]])
    direction = [sum(basis[r][c] * joint["direction"][c] for c in range(3)) for r in range(3)]
    return origin, direction


def transform(scene, joint, value):
    """T(j, v): what a joint at `value` does to what it moves, as a rigid 4x4 in the scene's frame and units.
    A revolute joint turns by `value` degrees about its line, right-handed along its direction; a prismatic
    joint slides by `value` millimetres along it."""
    origin, u = _line(scene, joint)
    if joint["kind"] == "prismatic":
        d = value * T.unit_factor("mm", scene.units)
        return T.translate(u[0] * d, u[1] * d, u[2] * d)
    a = math.radians(value)
    c, s = math.cos(a), math.sin(a)
    x, y, z = u
    R = [[c + x * x * (1 - c), x * y * (1 - c) - z * s, x * z * (1 - c) + y * s],
         [y * x * (1 - c) + z * s, c + y * y * (1 - c), y * z * (1 - c) - x * s],
         [z * x * (1 - c) - y * s, z * y * (1 - c) + x * s, c + z * z * (1 - c)]]
    # p' = R (p - o) + o
    t = [origin[r] - sum(R[r][k] * origin[k] for k in range(3)) for r in range(3)]
    return [R[0] + [t[0]], R[1] + [t[1]], R[2] + [t[2]], [0.0, 0.0, 0.0, 1.0]]


def world(motion, scene, occ_id, at):
    """The world transform of an occurrence, in the scene's units, with the joints at the values `at`
    ({joint name: value}; a joint that is not there is at zero, and a follower is where the joint it follows
    puts it). An occurrence no joint moves is where the scene has it."""
    at = settled(motion, at)
    out = scene.occurrences[occ_id].world
    for name in reversed(motion.moved.get(occ_id, ())):      # the innermost first; each one further out carries it
        value = at.get(name, 0.0)
        if value:
            out = T.multiply(transform(scene, motion.joints[name], value), out)
    return out


def worlds(motion, scene, at):
    """Where every occurrence that some joint moves is with the joints at `at`: {occurrence id: world transform}."""
    return {oid: world(motion, scene, oid, at) for oid in motion.moved}
