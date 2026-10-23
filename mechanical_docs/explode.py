"""Exploded subassembly view: which top-level groups move, and by how much.

An exploded view is an illustration: every child assembly of the root (with
all its occurrences, any depth) and the parts directly under the root (the
`root-parts` group) move as rigid bodies away from the root's bounds centre.
The offsets are illustration transforms only, kept apart from the installed
poses, and imply no order. The default is radial: each group moves along the
line from the root bounds centre to its own bounds centre by `spread` times
that distance (at least its own width along the line; a large group centred
on the root stays as the reference, a small one lifts). A project may override
any group's offset in `render.json` (`exploded_view.groups[].offset_mm`); the
receipt records the offsets used and their source. Pure Python, shared by the
renderer, the viewer export and the tests.
"""
from __future__ import annotations

from . import geometry
from . import transforms as T

ROOT_PARTS = "root-parts"


def top_level_groups(scene):
    """[(group id, occurrence ids)] in scene order: one entry per child assembly
    of the root (its occurrences at any depth), then `root-parts` for the
    occurrences directly under the root, when there are any."""
    out = []
    for aid, asm in scene.assemblies.items():
        if asm.parent_id == scene.root_id:
            members = scene.members(aid)
            if members:
                out.append((aid, members))
    root_parts = [oid for oid, occ in scene.occurrences.items() if occ.parent_id == scene.root_id]
    if root_parts:
        out.append((ROOT_PARTS, root_parts))
    return out


def group_of(scene, occ_id):
    """The top-level group an occurrence moves with."""
    occ = scene.occurrences[occ_id]
    if occ.parent_id == scene.root_id:
        return ROOT_PARTS
    return occ.path[1] if len(occ.path) > 1 else ROOT_PARTS


def bounds_m(scene, meshes, occ_ids):
    pts = []
    for oid in occ_ids:
        rec = meshes["parts"][scene.occurrences[oid].part_id]["mesh"]
        pts += geometry.occurrence_corners_m(rec, scene.occurrences[oid].world, scene.units)
    return geometry.aabb(pts)


def centre(mn, mx):
    return [(a + b) / 2 for a, b in zip(mn, mx)]


def propose_offsets_mm(scene, meshes, spread):
    """Radial default, in millimetres: each group moves along the line from the
    root bounds centre to its own bounds centre by `spread` times that
    distance, but never by less than `spread` times its own width along that
    line, so a small group nested near the centre still clears what surrounds
    it. A group whose centre coincides with the root's (within a thousandth of
    the root diagonal) is the reference and stays when its box holds at least a
    quarter of the root box's volume (a frame); a small concentric group lifts
    along +Z instead."""
    groups = top_level_groups(scene)
    rmn, rmx = bounds_m(scene, meshes, list(scene.occurrences))
    rc = centre(rmn, rmx)
    rext = [b - a for a, b in zip(rmn, rmx)]
    diag = sum(e * e for e in rext) ** 0.5
    rvol = rext[0] * rext[1] * rext[2]
    out = {}
    for gid, members in groups:
        gmn, gmx = bounds_m(scene, meshes, members)
        gext = [b - a for a, b in zip(gmn, gmx)]
        d = [g - r for g, r in zip(centre(gmn, gmx), rc)]
        n = sum(v * v for v in d) ** 0.5
        if diag <= 0 or n <= 1e-3 * diag:
            if rvol <= 0 or gext[0] * gext[1] * gext[2] >= 0.25 * rvol:
                out[gid] = [0.0, 0.0, 0.0]
                continue
            u, n = [0.0, 0.0, 1.0], 0.0
        else:
            u = [v / n for v in d]
        width = sum(e * abs(c) for e, c in zip(gext, u))
        mag = spread * max(n, width)
        out[gid] = [round(c * mag * 1000.0, 3) for c in u]
    return out


def resolve(scene, meshes, settings):
    """The exploded-view plan from the settings: whether it is drawn, the groups
    with their offsets (mm) and the source of each offset. Unknown group ids
    in the overrides are an error."""
    ev = settings["exploded_view"]
    groups = top_level_groups(scene)
    ids = [g for g, _ in groups]
    for ov in ev["groups"]:
        if ov["id"] not in ids:
            raise ValueError(f"render.json: exploded_view.groups names {ov['id']!r}, which is not a child assembly of the root or {ROOT_PARTS!r}; known: {ids}")
    enabled = ev["enabled"] if ev["enabled"] != "auto" else len(groups) >= 2
    proposed = propose_offsets_mm(scene, meshes, ev["spread"])
    overrides = {ov["id"]: [float(v) for v in ov["offset_mm"]] for ov in ev["groups"]}
    plan = []
    for gid, members in groups:
        plan.append({"id": gid, "occurrence_ids": members, "offset_mm": overrides.get(gid, proposed[gid]),
                     "source": "project" if gid in overrides else "radial"})
    return {"enabled": bool(enabled), "spread": ev["spread"], "direction": ev["direction"], "fill": ev["fill"], "groups": plan,
            "offsets_mm": {g["id"]: g["offset_mm"] for g in plan}}


def exploded_world(scene, occ_id, offsets_mm):
    """The occurrence's world transform (scene units) displaced by its group's
    offset; the installed pose itself is never changed."""
    occ = scene.occurrences[occ_id]
    off = offsets_mm.get(group_of(scene, occ_id), [0.0, 0.0, 0.0])
    f = T.unit_factor("mm", scene.units)
    out = [list(r) for r in occ.world]
    for i in range(3):
        out[i][3] += off[i] * f
    return out
