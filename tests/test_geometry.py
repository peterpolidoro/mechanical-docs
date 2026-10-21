import math

import pytest

from mechanical_docs import geometry, transforms as T
from mechanical_docs.manifest import load_project

PIN = {"bounds_min": [-5, -5, 0], "bounds_max": [5, 5, 30], "frame": {"unit_factor": 0.001}}   # a mm asset


def test_mesh_bounds_use_asset_units():
    assert geometry.mesh_bounds_m(PIN) == ([-0.005, -0.005, 0], [0.005, 0.005, 0.03])


def test_occurrence_corners_mix_asset_and_scene_units():
    # a cm scene: pin translated 12 cm in X, 4 cm up -> centre at (0.12, 0, 0.055) m
    world = T.translate(12, 0, 4)
    mn, mx = geometry.aabb(geometry.occurrence_corners_m(PIN, world, "cm"))
    assert mn == pytest.approx([0.115, -0.005, 0.04]) and mx == pytest.approx([0.125, 0.005, 0.07])


def test_rotated_nested_station_places_pins_off_axis():
    pr = load_project(__import__("pathlib").Path(__file__).resolve().parents[1] / "examples" / "two-bases-fixture")
    sc = pr.scene
    assert sc.units == "cm"
    assert T.translation(sc.occurrences["b-pin-1"].world) == pytest.approx([12, -2.5, 0])
    assert T.translation(sc.occurrences["b-pin-2"].world) == pytest.approx([12, 2.5, 0])
    assert T.translation(sc.occurrences["a-pin-1"].world) == pytest.approx([-2.5, 0, 0])
    corners = geometry.occurrence_corners_m(PIN, sc.occurrences["b-pin-1"].world, sc.units)
    mn, mx = geometry.aabb(corners)
    assert mn == pytest.approx([0.115, -0.03, 0.0]) and mx == pytest.approx([0.125, -0.02, 0.03])
    # the rotated base's long axis now runs along Y
    base = {"bounds_min": [-50, -30, 0], "bounds_max": [50, 30, 8], "frame": {"unit_factor": 0.001}}
    mn, mx = geometry.aabb(geometry.occurrence_corners_m(base, sc.occurrences["b-base"].world, sc.units))
    assert (mx[0] - mn[0], mx[1] - mn[1]) == pytest.approx((0.06, 0.10))
