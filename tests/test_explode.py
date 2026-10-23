"""Exploded-view planning: which groups move and by how much (pure Python)."""
import pytest

from mechanical_docs import explode
from mechanical_docs.manifest import load_project
from mechanical_docs.render_settings import load_settings


def fake_meshes(project):
    """A mesh receipt with bounds from the fixture's declared dimensions (metres via unit_factor)."""
    parts = {}
    for pid, p in project.scene.parts.items():
        d = p.identifying_dimensions_mm
        if "width" in d:
            mn, mx = [-d["width"] / 2, -d["depth"] / 2, 0.0], [d["width"] / 2, d["depth"] / 2, d["height"]]
        else:
            r = d["diameter"] / 2
            mn, mx = [-r, -r, 0.0], [r, r, d["length"]]
        parts[pid] = {"mesh": {"frame": {"unit_factor": 0.001}, "bounds_min": mn, "bounds_max": mx}}
    return {"parts": parts}


def test_top_level_groups_and_membership(fixture_dir):
    project = load_project(fixture_dir)
    groups = explode.top_level_groups(project.scene)
    assert groups == [("pin-pair", ["pin-a", "pin-b"]), ("root-parts", ["base-1"])]
    assert explode.group_of(project.scene, "pin-a") == "pin-pair" and explode.group_of(project.scene, "base-1") == "root-parts"


def test_radial_default_moves_nested_groups_apart(fixture_dir):
    project = load_project(fixture_dir)
    meshes = fake_meshes(project)
    off = explode.propose_offsets_mm(project.scene, meshes, 0.5)
    # the pins pass through the base, so the pin pair is centred on the root; it is small (a tenth of
    # the root box), so it lifts along +Z by spread x its own height; the base's centre lies 11 mm
    # below the root's, so it drops by spread x that distance
    assert off["pin-pair"] == pytest.approx([0.0, 0.0, 0.5 * 30.0], abs=1e-6)
    assert off["root-parts"] == pytest.approx([0.0, 0.0, -0.5 * 11.0], abs=1e-6)
    off = explode.propose_offsets_mm(project.scene, meshes, 1.0)
    assert off["pin-pair"][2] == pytest.approx(30.0, abs=1e-6) and off["root-parts"][2] == pytest.approx(-11.0, abs=1e-6)
    # the displaced world pose keeps the rotation and moves the translation only, in scene units
    w = explode.exploded_world(project.scene, "base-1", off)
    assert w[2][3] == pytest.approx(project.scene.occurrences["base-1"].world[2][3] - 11.0)
    assert w[0][3] == project.scene.occurrences["base-1"].world[0][3] and w[0][:3] == project.scene.occurrences["base-1"].world[0][:3]


def test_large_concentric_group_is_the_reference(fixture_dir):
    """A group centred on the root that fills most of it (a frame) stays; the others move away from it."""
    project = load_project(fixture_dir)
    meshes = fake_meshes(project)
    # make the pin pair as large as the root box: it becomes the reference and stays
    meshes["parts"]["pin"]["mesh"]["bounds_min"] = [-50.0, -30.0, 0.0]; meshes["parts"]["pin"]["mesh"]["bounds_max"] = [50.0, 30.0, 30.0]
    off = explode.propose_offsets_mm(project.scene, meshes, 0.5)
    assert off["pin-pair"] == [0.0, 0.0, 0.0] and off["root-parts"][2] < 0


def test_resolve_applies_overrides_and_rejects_unknown_groups(project_copy):
    project = load_project(project_copy.dir)
    meshes = fake_meshes(project)
    s, _ = load_settings(project_copy.dir)
    plan = explode.resolve(project.scene, meshes, s)
    assert plan["enabled"] is True and [g["id"] for g in plan["groups"]] == ["pin-pair", "root-parts"] and all(g["source"] == "radial" for g in plan["groups"])
    s["exploded_view"]["groups"] = [{"id": "root-parts", "offset_mm": [0, 0, -40]}]
    plan = explode.resolve(project.scene, meshes, s)
    assert plan["offsets_mm"]["root-parts"] == [0.0, 0.0, -40.0] and plan["groups"][1]["source"] == "project" and plan["groups"][0]["source"] == "radial"
    s["exploded_view"]["groups"] = [{"id": "base-1", "offset_mm": [0, 0, -40]}]
    with pytest.raises(ValueError, match="not a child assembly of the root"):
        explode.resolve(project.scene, meshes, s)
    s["exploded_view"]["groups"] = []; s["exploded_view"]["enabled"] = False
    assert explode.resolve(project.scene, meshes, s)["enabled"] is False
