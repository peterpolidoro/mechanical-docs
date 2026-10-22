"""Pure geometry helpers shared by the render stage and its tests.

Mesh bounds in meshes.json are in the CAD stage's units (millimetres, with the
factor to metres recorded beside them), while occurrence transforms are in the
*scene's* units. Each is converted to metres with its own factor, exactly once,
before they are combined.
"""
from __future__ import annotations

from . import transforms as T


def box_corners(mn, mx):
    return [(x, y, z) for x in (mn[0], mx[0]) for y in (mn[1], mx[1]) for z in (mn[2], mx[2])]


def mesh_bounds_m(mesh_record):
    """(min, max) of a part mesh in metres, from its meshes.json record."""
    f = mesh_record["frame"]["unit_factor"]
    return [v * f for v in mesh_record["bounds_min"]], [v * f for v in mesh_record["bounds_max"]]


def occurrence_corners_m(mesh_record, world, scene_units):
    """The eight bounding-box corners of a part placed by `world` (a scene-unit
    transform), in metres: mesh-unit corners scaled by the recorded factor, then
    transformed by the pose with its translation scaled by the scene factor."""
    mn, mx = mesh_bounds_m(mesh_record)
    M = T.scaled_translation(world, T.unit_factor(scene_units, "m"))
    return [tuple(T.apply(M, c)) for c in box_corners(mn, mx)]


def aabb(points):
    mn = [min(p[i] for p in points) for i in range(3)]
    mx = [max(p[i] for p in points) for i in range(3)]
    return mn, mx
