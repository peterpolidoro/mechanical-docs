"""Load and validate a draft-1 project: scene.json, instructions.json, inventory.json.

Only the fields the contract names are accepted; anything else is an error, so
a producer cannot silently rely on unsupported data. Every problem found is
reported together in one ManifestError rather than one at a time.

The validated result carries resolved world transforms in a +Z-up frame (a
declared +Y-up scene is rotated once, at the root, by its `basis_to_z_up`),
resolved asset paths and the SHA-256 of every input file.
"""
from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field
from pathlib import Path

from . import transforms as T
from .names import valid_identifier

SCHEMA_VERSION = "draft-1"
REVIEW_STATES = ("draft", "cad-reviewed", "physically-validated")
PROJECTIONS = ("orthographic", "perspective")
APPROACH_VALIDATIONS = ("unverified-render-hint",)
ASSET_FORMATS = ("step",)
UP_AXES = ("+Z", "+Y")
BOM_STRUCTURES = ("Normal", "Phantom", "Reference", "Purchased", "Inseparable", "Default")
NOT_INSTALLED_BOM = ("Reference",)      # geometry shown for context, never an installed or required part
SHA256 = re.compile(r"^[0-9a-f]{64}$")

SCENE_FIELDS = {"schema_version", "id", "title", "units", "coordinate_system", "source", "parts", "assemblies", "occurrences"}
COORD_FIELDS = {"handedness", "up_axis", "origin", "note", "basis_to_z_up"}
PART_FIELDS = {"id", "name", "asset", "identifying_dimensions_mm", "description",
               "model_state", "bodies", "volume_mm3", "bom_structure_default", "properties", "source"}
BODIES_FIELDS = {"surface_bodies", "solid_bodies", "visible_solid_bodies"}
ASSET_FIELDS = {"path", "format", "units", "sha256"}
ASSEMBLY_FIELDS = {"id", "parent_id", "transform", "name", "document", "bom_structure", "model_state", "suppressed", "visible", "flexible"}
OCCURRENCE_FIELDS = {"id", "part_id", "parent_id", "transform", "name", "transform_world", "position_overridden_vs_definition",
                     "parent_flexible", "visible", "visible_effective", "suppressed", "grounded", "mirrored", "bom_structure", "model_state"}
INSTRUCTION_FIELDS = {"schema_version", "scene", "id", "title", "review_state", "views", "steps"}
VIEW_FIELDS = {"id", "projection", "eye", "target", "up"}
STEP_FIELDS = {"id", "requires", "add", "view", "caption", "approach"}
APPROACH_FIELDS = {"occurrence_id", "start_offset", "end_offset", "validation"}
INVENTORY_FIELDS = {"schema_version", "scene", "status", "items"}
ITEM_FIELDS = {"part_id", "required", "unit", "counted"}
SCALAR = (str, int, float, bool, type(None))


class ManifestError(ValueError):
    def __init__(self, problems):
        self.problems = list(problems)
        super().__init__("\n".join(["invalid project:"] + [f"  - {p}" for p in self.problems]))


def sha256_file(path):
    import hashlib
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


@dataclass
class Asset:
    path: str
    format: str
    units: str
    sha256: str
    resolved: Path
    bytes: int = 0


@dataclass
class Part:
    id: str
    name: str
    asset: Asset
    identifying_dimensions_mm: dict = field(default_factory=dict)
    description: str = ""
    model_state: str | None = None
    bodies: dict | None = None
    volume_mm3: float | None = None
    bom_structure_default: str | None = None
    properties: dict = field(default_factory=dict)
    source: dict = field(default_factory=dict)


@dataclass
class Assembly:
    id: str
    parent_id: str | None
    transform: list
    name: str = ""
    world: list = field(default_factory=lambda: [list(r) for r in T.IDENTITY])
    depth: int = 0
    flexible: bool | None = None
    bom_structure: str | None = None
    suppressed: bool | None = None
    visible: bool | None = None
    model_state: str | None = None
    document: str | None = None


@dataclass
class Occurrence:
    id: str
    part_id: str
    parent_id: str
    transform: list
    name: str = ""
    world: list = field(default_factory=lambda: [list(r) for r in T.IDENTITY])   # +Z-up scene frame
    path: list = field(default_factory=list)       # assembly ids from the root down
    bom_structure: str | None = None
    visible: bool | None = None
    visible_effective: bool | None = None
    grounded: bool | None = None
    parent_flexible: bool | None = None
    position_overridden: bool | None = None
    model_state: str | None = None

    @property
    def installed(self):
        """Counts as an installed part (not reference-only geometry)."""
        return self.bom_structure not in NOT_INSTALLED_BOM


@dataclass
class Scene:
    id: str
    title: str
    units: str
    coordinate_system: dict
    source: dict
    parts: dict            # id -> Part
    assemblies: dict       # id -> Assembly
    occurrences: dict      # id -> Occurrence (insertion order preserved)
    root_id: str
    file: Path
    sha256: str
    native_up_axis: str = "+Z"
    basis_to_z_up: list = field(default_factory=lambda: [list(r) for r in T.IDENTITY])
    transform_world_check: dict | None = None     # when the exporter declared world matrices
    coincident: list = field(default_factory=list)   # [{"part_id", "occurrences": [a, b], "max_deviation"}]: same part, same world pose

    def coincident_of(self, part_id):
        return [c for c in self.coincident if c["part_id"] == part_id]

    def occurrences_of(self, part_id):
        return [o for o in self.occurrences.values() if o.part_id == part_id]

    def installed_occurrences_of(self, part_id):
        return [o for o in self.occurrences_of(part_id) if o.installed]


@dataclass
class View:
    id: str
    projection: str
    eye: list
    target: list
    up: list


@dataclass
class Approach:
    occurrence_id: str
    start_offset: list
    end_offset: list
    validation: str


@dataclass
class Step:
    id: str
    requires: list
    add: list
    view: str
    caption: str
    approach: Approach | None = None


@dataclass
class Instructions:
    id: str
    title: str
    review_state: str
    views: dict
    steps: list
    file: Path
    sha256: str


@dataclass
class InventoryItem:
    part_id: str
    required: int
    unit: str
    counted: int | None


@dataclass
class Inventory:
    status: str
    items: list
    file: Path
    sha256: str


@dataclass
class Project:
    dir: Path
    scene: Scene
    instructions: Instructions | None
    inventory: Inventory

    @property
    def has_instructions(self):
        return self.instructions is not None

    def input_hashes(self):
        h = {str(self.scene.file.relative_to(self.dir)): self.scene.sha256}
        if self.instructions is not None:
            h[str(self.instructions.file.relative_to(self.dir))] = self.instructions.sha256
        h[str(self.inventory.file.relative_to(self.dir))] = self.inventory.sha256
        for p in self.scene.parts.values():
            h[str(p.asset.resolved.relative_to(self.dir))] = p.asset.sha256
        return h


# ------------------------------------------------------------------ helpers

class _Check:
    def __init__(self):
        self.problems = []

    def __call__(self, cond, msg):
        if not cond:
            self.problems.append(msg)
        return bool(cond)

    def fields(self, obj, allowed, where):
        if not isinstance(obj, dict):
            self.problems.append(f"{where}: expected an object")
            return False
        extra = sorted(set(obj) - allowed)
        if extra:
            self.problems.append(f"{where}: unsupported field(s) {extra}; draft-1 accepts {sorted(allowed)}")
        return True

    def ident(self, value, where):
        ok = valid_identifier(value)
        if not ok:
            self.problems.append(f"{where}: identifier must be a non-empty string without control characters or surrounding whitespace, got {value!r}")
        return ok

    def vec3(self, value, where):
        ok = isinstance(value, list) and len(value) == 3 and all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in value)
        if not ok:
            self.problems.append(f"{where}: expected three numbers, got {value!r}")
            return None
        return [float(v) for v in value]

    def matrix(self, value, where):
        try:
            return T.check_matrix(value, where)
        except T.TransformError as e:
            self.problems.append(str(e))
            return None

    def opt_bool(self, obj, key, where):
        v = obj.get(key)
        self(v is None or isinstance(v, bool), f"{where}.{key}: expected true/false")
        return v if isinstance(v, bool) else None

    def opt_str(self, obj, key, where, choices=None):
        v = obj.get(key)
        self(v is None or isinstance(v, str), f"{where}.{key}: expected a string")
        if isinstance(v, str) and choices is not None:
            self(v in choices, f"{where}.{key}: expected one of {choices}, got {v!r}")
        return v if isinstance(v, str) else None

    def scalar_dict(self, obj, key, where):
        v = obj.get(key)
        if v is None:
            return {}
        if not self(isinstance(v, dict), f"{where}.{key}: expected an object of scalar values"):
            return {}
        for k, x in v.items():
            self(isinstance(x, SCALAR), f"{where}.{key}.{k}: expected a string, number, boolean or null (nested data is not accepted)")
        return dict(v)

    def raise_if_any(self):
        if self.problems:
            raise ManifestError(self.problems)


def _load_json(path, chk, where):
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8-sig"))   # a UTF-8 BOM (PowerShell) is tolerated
    except FileNotFoundError:
        chk(False, f"{where}: file not found: {path}")
        return None
    except (OSError, ValueError) as e:
        chk(False, f"{where}: cannot parse {path}: {e}")
        return None
    if not isinstance(data, dict):
        chk(False, f"{where}: top level must be an object")
        return None
    if data.get("schema_version") != SCHEMA_VERSION:
        chk(False, f"{where}: schema_version must be {SCHEMA_VERSION!r}, got {data.get('schema_version')!r}")
    return data


def _resolve_inside(root: Path, base: Path, rel: str, chk, where):
    """`rel` resolved from `base`, required to stay inside `root`."""
    if not isinstance(rel, str) or not rel or os.path.isabs(rel) or rel.startswith(("\\", "//")) or ":" in rel.split("/")[0][:2]:
        chk(False, f"{where}: path must be relative, got {rel!r}")
        return None
    cand = (base / rel).resolve()
    try:
        cand.relative_to(root.resolve())
    except ValueError:
        chk(False, f"{where}: path {rel!r} escapes the project root {root}")
        return None
    return cand


def _dims(dims, chk, where):
    if dims is None:
        return {}
    if not chk(isinstance(dims, dict), f"{where}: expected an object"):
        return {}
    out = {}
    for k, v in dims.items():
        if k == "extent":
            vec = chk.vec3(v, f"{where}.extent")
            if vec is not None and chk(all(x > 0 for x in vec), f"{where}.extent: expected three positive numbers"):
                out[k] = vec
        elif chk(isinstance(v, (int, float)) and not isinstance(v, bool) and v > 0, f"{where}.{k}: expected a positive number"):
            out[k] = v
    return out


# -------------------------------------------------------------------- scene

def load_scene(path, root=None, chk=None):
    own = chk is None
    chk = chk or _Check()
    path = Path(path)
    root = Path(root) if root else path.parent
    data = _load_json(path, chk, "scene")
    if data is None:
        chk.raise_if_any()
    chk.fields(data, SCENE_FIELDS, "scene")
    for key in ("id", "title", "units", "coordinate_system", "source", "parts", "assemblies", "occurrences"):
        chk(key in data, f"scene: missing field {key!r}")
    sid = data.get("id")
    chk.ident(sid, "scene.id")
    units = data.get("units")
    chk(units in T.UNIT_TO_MM, f"scene.units: unsupported {units!r}; known {sorted(T.UNIT_TO_MM)}")
    cs = data.get("coordinate_system", {})
    basis = [list(r) for r in T.IDENTITY]
    up_axis = "+Z"
    if chk.fields(cs, COORD_FIELDS, "scene.coordinate_system"):
        chk(cs.get("handedness") == "right", f"scene.coordinate_system.handedness: only 'right' is supported, got {cs.get('handedness')!r}")
        up_axis = cs.get("up_axis")
        if chk(up_axis in UP_AXES, f"scene.coordinate_system.up_axis: expected one of {UP_AXES}, got {up_axis!r}"):
            if up_axis == "+Y":
                if chk("basis_to_z_up" in cs, "scene.coordinate_system: a '+Y' up axis requires 'basis_to_z_up' (the rigid matrix taking native coordinates to the +Z-up scene frame)"):
                    m = chk.matrix(cs["basis_to_z_up"], "scene.coordinate_system.basis_to_z_up")
                    if m is not None:
                        up = T.apply(m, [0, 1, 0])
                        chk(all(abs(a - b) < 1e-9 for a, b in zip(up, [0, 0, 1])) and all(abs(v) < 1e-9 for v in T.translation(m)),
                            f"scene.coordinate_system.basis_to_z_up: must map native +Y to +Z with no translation, maps it to {up}")
                        basis = m
            else:
                chk("basis_to_z_up" not in cs or T.close(T.check_matrix(cs["basis_to_z_up"]) if isinstance(cs["basis_to_z_up"], list) else T.IDENTITY, T.IDENTITY),
                    "scene.coordinate_system.basis_to_z_up: must be identity (or absent) for a '+Z' up axis")
        chk(isinstance(cs.get("note", ""), str), "scene.coordinate_system.note: expected a string")
    src = data.get("source", {})
    if chk(isinstance(src, dict), "scene.source: expected an object"):
        for k, v in src.items():
            chk(isinstance(v, SCALAR), f"scene.source.{k}: expected a string, number, boolean or null")

    parts = {}
    for i, p in enumerate(data.get("parts") or []):
        where = f"scene.parts[{i}]"
        if not chk.fields(p, PART_FIELDS, where):
            continue
        pid = p.get("id")
        if not chk.ident(pid, where + ".id"):
            continue
        if not chk(pid not in parts, f"{where}: duplicate part id {pid!r}"):
            continue
        a = p.get("asset")
        if not chk.fields(a, ASSET_FIELDS, where + ".asset"):
            continue
        for k in ASSET_FIELDS:
            chk(k in a, f"{where}.asset: missing field {k!r}")
        chk(a.get("format") in ASSET_FORMATS, f"{where}.asset.format: only {ASSET_FORMATS} supported, got {a.get('format')!r}")
        chk(a.get("units") in T.UNIT_TO_MM, f"{where}.asset.units: unsupported {a.get('units')!r}")
        digest = a.get("sha256", "")
        chk(isinstance(digest, str) and SHA256.match(digest or ""), f"{where}.asset.sha256: expected 64 hex characters")
        resolved = _resolve_inside(root, path.parent, a.get("path"), chk, where + ".asset.path")
        nbytes = 0
        if resolved is not None:
            if chk(resolved.is_file(), f"{where}.asset.path: file not found: {a.get('path')!r}"):
                actual = sha256_file(resolved)
                nbytes = resolved.stat().st_size
                chk(actual == digest, f"{where}.asset: SHA-256 mismatch for {a.get('path')!r}: manifest {digest[:12]}…, file {actual[:12]}…")
        dims = _dims(p.get("identifying_dimensions_mm"), chk, where + ".identifying_dimensions_mm")
        name = p.get("name", pid)
        chk(isinstance(name, str) and name.strip(), f"{where}.name: expected a non-empty string")
        bodies = p.get("bodies")
        if bodies is not None and chk.fields(bodies, BODIES_FIELDS, where + ".bodies"):
            for k, v in bodies.items():
                chk(isinstance(v, int) and not isinstance(v, bool) and v >= 0, f"{where}.bodies.{k}: expected a non-negative integer")
        vol = p.get("volume_mm3")
        chk(vol is None or (isinstance(vol, (int, float)) and not isinstance(vol, bool) and vol >= 0), f"{where}.volume_mm3: expected a non-negative number")
        parts[pid] = Part(pid, name, Asset(a.get("path", ""), a.get("format", ""), a.get("units", ""), digest, resolved or Path(), nbytes),
                          dims, str(p.get("description", "")), chk.opt_str(p, "model_state", where),
                          dict(bodies) if isinstance(bodies, dict) else None, vol,
                          chk.opt_str(p, "bom_structure_default", where, BOM_STRUCTURES),
                          chk.scalar_dict(p, "properties", where), chk.scalar_dict(p, "source", where))
    chk(bool(parts), "scene.parts: at least one part is required")

    assemblies = {}
    for i, a in enumerate(data.get("assemblies") or []):
        where = f"scene.assemblies[{i}]"
        if not chk.fields(a, ASSEMBLY_FIELDS, where):
            continue
        aid = a.get("id")
        if not chk.ident(aid, where + ".id"):
            continue
        if not chk(aid not in assemblies, f"{where}: duplicate assembly id {aid!r}"):
            continue
        chk("parent_id" in a, f"{where}: missing field 'parent_id' (null for the root)")
        m = chk.matrix(a.get("transform"), where + ".transform")
        asm = Assembly(aid, a.get("parent_id"), m or [list(r) for r in T.IDENTITY], str(a.get("name", "")))
        asm.flexible = chk.opt_bool(a, "flexible", where); asm.suppressed = chk.opt_bool(a, "suppressed", where)
        asm.visible = chk.opt_bool(a, "visible", where)
        asm.bom_structure = chk.opt_str(a, "bom_structure", where, BOM_STRUCTURES)
        asm.model_state = chk.opt_str(a, "model_state", where); asm.document = chk.opt_str(a, "document", where)
        chk(asm.suppressed is not True, f"{where}: suppressed assemblies are not accepted; the adapter must omit them or the contract be extended")
        assemblies[aid] = asm
    roots = [a for a in assemblies.values() if a.parent_id is None]
    chk(len(roots) == 1, f"scene.assemblies: exactly one root (parent_id null) is required, found {len(roots)}")
    for a in assemblies.values():
        if a.parent_id is not None:
            chk(a.parent_id in assemblies, f"scene.assemblies[{a.id!r}]: unknown parent_id {a.parent_id!r}")
    # native-frame world transforms, detecting cycles; the basis is applied once at the root
    native_world = {}

    def resolve(aid, trail):
        if aid in native_world:
            return native_world[aid]
        if aid in trail:
            chk(False, f"scene.assemblies: hierarchy cycle through {' -> '.join(trail + [aid])}")
            return None
        a = assemblies[aid]
        if a.parent_id is None:
            w = a.transform
        else:
            if a.parent_id not in assemblies:
                return None
            pw = resolve(a.parent_id, trail + [aid])
            if pw is None:
                return None
            w = T.multiply(pw, a.transform)
        native_world[aid] = w
        return w

    for aid in assemblies:
        w = resolve(aid, [])
        if w is not None:
            assemblies[aid].world = T.multiply(basis, w)
            d = 0; cur = assemblies[aid]
            while cur.parent_id is not None and cur.parent_id in assemblies and d < len(assemblies):
                d += 1; cur = assemblies[cur.parent_id]
            assemblies[aid].depth = d

    occurrences = {}
    tw_checked = 0; tw_worst = 0.0
    for i, o in enumerate(data.get("occurrences") or []):
        where = f"scene.occurrences[{i}]"
        if not chk.fields(o, OCCURRENCE_FIELDS, where):
            continue
        oid = o.get("id")
        if not chk.ident(oid, where + ".id"):
            continue
        if not chk(oid not in occurrences, f"{where}: duplicate occurrence id {oid!r}"):
            continue
        chk(oid not in assemblies, f"{where}: occurrence id {oid!r} collides with an assembly id; ids share one namespace")
        chk(o.get("part_id") in parts, f"{where}: unknown part_id {o.get('part_id')!r}")
        chk(o.get("parent_id") in assemblies, f"{where}: unknown parent_id {o.get('parent_id')!r}")
        m = chk.matrix(o.get("transform"), where + ".transform")
        occ = Occurrence(oid, o.get("part_id"), o.get("parent_id"), m or [list(r) for r in T.IDENTITY], str(o.get("name", "")))
        occ.bom_structure = chk.opt_str(o, "bom_structure", where, BOM_STRUCTURES)
        occ.visible = chk.opt_bool(o, "visible", where); occ.visible_effective = chk.opt_bool(o, "visible_effective", where)
        occ.grounded = chk.opt_bool(o, "grounded", where); occ.parent_flexible = chk.opt_bool(o, "parent_flexible", where)
        occ.position_overridden = chk.opt_bool(o, "position_overridden_vs_definition", where)
        occ.model_state = chk.opt_str(o, "model_state", where)
        chk(chk.opt_bool(o, "suppressed", where) is not True, f"{where}: suppressed occurrences are not accepted; the adapter must omit them or the contract be extended")
        chk(chk.opt_bool(o, "mirrored", where) is not True, f"{where}: mirrored occurrences must be exported as an explicitly mirrored geometry variant")
        if m is not None and occ.parent_id in native_world:
            nw = T.multiply(native_world[occ.parent_id], m)
            occ.world = T.multiply(basis, nw)
            if "transform_world" in o:
                tw = chk.matrix(o["transform_world"], where + ".transform_world")
                if tw is not None:
                    dev = max(abs(a - b) for ra, rb in zip(nw, tw) for a, b in zip(ra, rb))
                    tw_checked += 1; tw_worst = max(tw_worst, dev)
                    chk(dev < 1e-6 * max(1.0, max(abs(v) for v in T.translation(tw))),
                        f"{where}.transform_world: differs from the composed parent chain by {dev:.3g} {units}")
            trail = []; cur = occ.parent_id
            while cur is not None and cur in assemblies and len(trail) <= len(assemblies):
                trail.append(cur); cur = assemblies[cur].parent_id
            occ.path = list(reversed(trail))
        occurrences[oid] = occ
    chk(bool(occurrences), "scene.occurrences: at least one occurrence is required")
    unused = sorted(set(parts) - {o.part_id for o in occurrences.values()})
    chk(not unused, f"scene.parts: part(s) with no occurrence: {unused}")
    # Two occurrences of one part at the same world pose are a CAD ambiguity, not a
    # validation error: the source instances are kept and counted, and the finding is
    # recorded so documents can say the count needs review before it becomes stock.
    coincident = []
    by_part = {}
    for o in occurrences.values():
        by_part.setdefault(o.part_id, []).append(o)
    tol = 1e-6 * max(1.0, max((abs(v) for o in occurrences.values() for v in T.translation(o.world)), default=1.0))
    for pid, occs in by_part.items():
        for i in range(len(occs)):
            for j in range(i + 1, len(occs)):
                dev = max(abs(a - b) for ra, rb in zip(occs[i].world, occs[j].world) for a, b in zip(ra, rb))
                if dev < tol:
                    coincident.append({"part_id": pid, "occurrences": [occs[i].id, occs[j].id], "max_deviation": dev})

    if own:
        chk.raise_if_any()
    scene = Scene(sid or "", str(data.get("title", "")), units or "", dict(cs or {}), dict(src or {}), parts, assemblies, occurrences,
                  roots[0].id if roots else "", path, sha256_file(path) if path.is_file() else "",
                  up_axis or "+Z", basis,
                  {"checked": tw_checked, "max_deviation": tw_worst} if tw_checked else None, coincident)
    return scene


# ------------------------------------------------------------- instructions

def load_instructions(path, scene: Scene, chk=None):
    own = chk is None
    chk = chk or _Check()
    path = Path(path)
    data = _load_json(path, chk, "instructions")
    if data is None:
        chk.raise_if_any()
    chk.fields(data, INSTRUCTION_FIELDS, "instructions")
    for key in ("scene", "id", "title", "review_state", "views", "steps"):
        chk(key in data, f"instructions: missing field {key!r}")
    chk.ident(data.get("id"), "instructions.id")
    ref = data.get("scene")
    if chk(isinstance(ref, str), "instructions.scene: expected a relative path"):
        chk((path.parent / ref).resolve() == scene.file.resolve(), f"instructions.scene: {ref!r} is not the loaded scene {scene.file.name!r}")
    chk(data.get("review_state") in REVIEW_STATES, f"instructions.review_state: expected one of {REVIEW_STATES}, got {data.get('review_state')!r}")

    views = {}
    for i, v in enumerate(data.get("views") or []):
        where = f"instructions.views[{i}]"
        if not chk.fields(v, VIEW_FIELDS, where):
            continue
        vid = v.get("id")
        if not chk.ident(vid, where + ".id") or not chk(vid not in views, f"{where}: duplicate view id {vid!r}"):
            continue
        chk(v.get("projection") in PROJECTIONS, f"{where}.projection: expected one of {PROJECTIONS}, got {v.get('projection')!r}")
        eye = chk.vec3(v.get("eye"), where + ".eye"); target = chk.vec3(v.get("target"), where + ".target")
        up = chk.vec3(v.get("up", [0, 0, 1]), where + ".up")
        if eye and target and up:
            d = [t - e for e, t in zip(eye, target)]
            dl = sum(x * x for x in d) ** 0.5; ul = sum(x * x for x in up) ** 0.5
            chk(dl > 1e-9, f"{where}: eye and target coincide")
            chk(ul > 1e-9, f"{where}.up: zero vector")
            if dl > 1e-9 and ul > 1e-9:
                cosang = abs(sum(a * b for a, b in zip(d, up))) / (dl * ul)
                chk(cosang < 0.999, f"{where}: up vector is parallel to the view direction")
        views[vid] = View(vid, v.get("projection", ""), eye or [0, 0, 0], target or [0, 0, 0], up or [0, 0, 1])
    chk(bool(views), "instructions.views: at least one view is required")

    steps = []
    seen_steps = {}          # step id -> index
    first_install = {}       # occurrence id -> step id that installs it
    for i, s in enumerate(data.get("steps") or []):
        where = f"instructions.steps[{i}]"
        if not chk.fields(s, STEP_FIELDS, where):
            continue
        stid = s.get("id")
        if not chk.ident(stid, where + ".id"):
            continue
        chk(stid not in seen_steps, f"{where}: duplicate step id {stid!r}")
        req = s.get("requires", [])
        if chk(isinstance(req, list), f"{where}.requires: expected a list of step ids"):
            for r in req:
                chk(r in seen_steps, f"{where}.requires: {r!r} is not an earlier step" + (" (a step cannot require itself)" if r == stid else ""))
        add = s.get("add")
        if chk(isinstance(add, list) and add, f"{where}.add: expected a non-empty list of occurrence ids"):
            chk(len(set(add)) == len(add), f"{where}.add: repeated occurrence within the step")
            for oid in add:
                hint = " (an assembly group is not an installed part)" if oid in scene.assemblies else ""
                if not chk(oid in scene.occurrences, f"{where}.add: unknown occurrence {oid!r}{hint}"):
                    continue
                chk(scene.occurrences[oid].installed, f"{where}.add: occurrence {oid!r} is reference-only geometry (bom_structure {scene.occurrences[oid].bom_structure}) and cannot be installed")
                if oid in first_install:
                    chk(False, f"{where}.add: occurrence {oid!r} is installed again (first in step {first_install[oid]!r})")
                else:
                    first_install[oid] = stid
        chk(s.get("view") in views, f"{where}.view: unknown view {s.get('view')!r}")
        chk(isinstance(s.get("caption", ""), str), f"{where}.caption: expected a string")
        approach = None
        ap = s.get("approach")
        if ap is not None and chk.fields(ap, APPROACH_FIELDS, where + ".approach"):
            for k in APPROACH_FIELDS:
                chk(k in ap, f"{where}.approach: missing field {k!r}")
            chk(ap.get("occurrence_id") in (add or []), f"{where}.approach.occurrence_id: {ap.get('occurrence_id')!r} is not added by this step")
            so = chk.vec3(ap.get("start_offset"), where + ".approach.start_offset")
            eo = chk.vec3(ap.get("end_offset"), where + ".approach.end_offset")
            chk(ap.get("validation") in APPROACH_VALIDATIONS, f"{where}.approach.validation: only {APPROACH_VALIDATIONS} is accepted, got {ap.get('validation')!r}")
            if eo is not None:
                chk(all(abs(v) < 1e-9 for v in eo), f"{where}.approach.end_offset: must be zero; the final pose is the canonical placement")
            approach = Approach(ap.get("occurrence_id", ""), so or [0, 0, 0], eo or [0, 0, 0], ap.get("validation", ""))
        seen_steps[stid] = i
        steps.append(Step(stid, list(req or []), list(add or []), s.get("view", ""), str(s.get("caption", "")), approach))
    chk(bool(steps), "instructions.steps: at least one step is required")
    never = [oid for oid, occ in scene.occurrences.items() if occ.installed and oid not in first_install]
    chk(not never, f"instructions.steps: occurrence(s) never installed: {never}")
    if own:
        chk.raise_if_any()
    return Instructions(data.get("id", ""), str(data.get("title", "")), data.get("review_state", ""), views, steps, path, sha256_file(path) if path.is_file() else "")


# ---------------------------------------------------------------- inventory

def load_inventory(path, scene: Scene, chk=None):
    own = chk is None
    chk = chk or _Check()
    path = Path(path)
    data = _load_json(path, chk, "inventory")
    if data is None:
        chk.raise_if_any()
    chk.fields(data, INVENTORY_FIELDS, "inventory")
    for key in ("scene", "status", "items"):
        chk(key in data, f"inventory: missing field {key!r}")
    ref = data.get("scene")
    if chk(isinstance(ref, str), "inventory.scene: expected a relative path"):
        chk((path.parent / ref).resolve() == scene.file.resolve(), f"inventory.scene: {ref!r} is not the loaded scene {scene.file.name!r}")
    items = []
    seen = set()
    for i, it in enumerate(data.get("items") or []):
        where = f"inventory.items[{i}]"
        if not chk.fields(it, ITEM_FIELDS, where):
            continue
        for k in ITEM_FIELDS:
            chk(k in it, f"{where}: missing field {k!r} (counted may be null)")
        pid = it.get("part_id")
        chk(pid in scene.parts, f"{where}.part_id: unknown part {pid!r}")
        chk(pid not in seen, f"{where}: duplicate inventory row for {pid!r}")
        seen.add(pid)
        req = it.get("required")
        chk(isinstance(req, int) and not isinstance(req, bool) and req >= 0, f"{where}.required: expected a non-negative integer")
        cnt = it.get("counted")
        chk(cnt is None or (isinstance(cnt, int) and not isinstance(cnt, bool) and cnt >= 0), f"{where}.counted: expected null or a non-negative integer")
        chk(isinstance(it.get("unit"), str) and it.get("unit"), f"{where}.unit: expected a string such as 'each'")
        if pid in scene.parts and isinstance(req, int):
            n = len(scene.installed_occurrences_of(pid))
            chk(req == n, f"{where}: required {req} for {pid!r} but the scene installs {n} occurrence(s)" + (" (reference-only occurrences do not count)" if n != len(scene.occurrences_of(pid)) else ""))
        items.append(InventoryItem(pid, req if isinstance(req, int) else 0, str(it.get("unit", "")), cnt if isinstance(cnt, int) else None))
    missing = sorted(set(scene.parts) - seen)
    chk(not missing, f"inventory.items: no row for part(s) {missing}")
    if own:
        chk.raise_if_any()
    return Inventory(str(data.get("status", "")), items, path, sha256_file(path) if path.is_file() else "")


# ------------------------------------------------------------------ project

def load_project(project_dir, scene="scene.json", instructions="instructions.json", inventory="inventory.json", root=None,
                 require_instructions=False) -> Project:
    """Load and validate a project directory: scene and inventory always, the
    instructions when the file exists (a project without a reviewed sequence
    still yields a parts inventory). Raises ManifestError listing every problem.
    `root` is the directory asset paths may not escape; it defaults to the
    project directory.
    """
    d = Path(project_dir).resolve()
    chk = _Check()
    sc = load_scene(d / scene, root or d, chk)
    chk.raise_if_any()   # the other two cannot be checked against a broken scene
    ins = None
    if (d / instructions).exists():
        ins = load_instructions(d / instructions, sc, chk)
    elif require_instructions:
        chk(False, f"instructions: file not found: {d / instructions}")
    inv = load_inventory(d / inventory, sc, chk)
    chk.raise_if_any()
    return Project(d, sc, ins, inv)


def inventory_template(scene: Scene):
    """A draft inventory.json for a scene: required = installed occurrences per
    part (reference-only geometry excluded), nothing counted. Required means
    installed quantity, not purchased quantity or stock."""
    items = [{"part_id": pid, "required": len(scene.installed_occurrences_of(pid)), "unit": "each", "counted": None} for pid in scene.parts]
    return {"schema_version": SCHEMA_VERSION, "scene": scene.file.name,
            "status": "draft: required = installed occurrences in the CAD scene (reference-only geometry excluded); "
                      "not a purchase list, kits not reconciled; physical stock not counted",
            "items": items}
