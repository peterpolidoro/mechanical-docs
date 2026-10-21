import pytest

from mechanical_docs import transforms as T
from mechanical_docs.manifest import ManifestError, load_project


def test_fixture_loads_and_resolves_world_transforms(fixture_dir):
    pr = load_project(fixture_dir)
    sc = pr.scene
    assert set(sc.parts) == {"base", "pin"}
    assert list(sc.occurrences) == ["base-1", "pin-a", "pin-b"]
    assert sc.root_id == "root"
    assert T.translation(sc.occurrences["pin-a"].world) == [-25, 0, 0]
    assert T.translation(sc.occurrences["pin-b"].world) == [25, 0, 0]
    assert sc.occurrences["pin-a"].path == ["root", "pin-pair"]
    assert sc.assemblies["pin-pair"].depth == 1
    assert len(pr.input_hashes()) == 5
    assert pr.inventory.items[1].counted is None


def _problems(project):
    with pytest.raises(ManifestError) as ei:
        load_project(project.dir)
    return "\n".join(ei.value.problems)


def test_unknown_field_rejected(project_copy):
    project_copy.edit("scene.json", lambda d: d["parts"][0].__setitem__("color", "red"))
    assert "unsupported field(s) ['color']" in _problems(project_copy)


def test_wrong_schema_version(project_copy):
    project_copy.edit("scene.json", lambda d: d.__setitem__("schema_version", "draft-2"))
    assert "schema_version must be 'draft-1'" in _problems(project_copy)


def test_asset_hash_mismatch(project_copy):
    project_copy.edit("scene.json", lambda d: d["parts"][1]["asset"].__setitem__("sha256", "0" * 64))
    assert "SHA-256 mismatch" in _problems(project_copy)


def test_asset_path_escape_rejected(project_copy):
    project_copy.edit("scene.json", lambda d: d["parts"][1]["asset"].__setitem__("path", "../outside.step"))
    assert "escapes the project root" in _problems(project_copy)


def test_absolute_asset_path_rejected(project_copy):
    project_copy.edit("scene.json", lambda d: d["parts"][1]["asset"].__setitem__("path", "/etc/passwd"))
    assert "must be relative" in _problems(project_copy)


def test_missing_asset_file(project_copy):
    project_copy.edit("scene.json", lambda d: d["parts"][1]["asset"].__setitem__("path", "assets/nope.step"))
    assert "file not found" in _problems(project_copy)


def test_duplicate_occurrence_id(project_copy):
    project_copy.edit("scene.json", lambda d: d["occurrences"][2].__setitem__("id", "pin-a"))
    p = _problems(project_copy)
    assert "duplicate occurrence id 'pin-a'" in p


def test_unknown_part_and_parent(project_copy):
    def f(d):
        d["occurrences"][1]["part_id"] = "bolt"
        d["occurrences"][2]["parent_id"] = "nowhere"
    project_copy.edit("scene.json", f)
    p = _problems(project_copy)
    assert "unknown part_id 'bolt'" in p and "unknown parent_id 'nowhere'" in p


def test_hierarchy_cycle(project_copy):
    def f(d):
        d["assemblies"].append({"id": "a", "parent_id": "b", "transform": T.IDENTITY})
        d["assemblies"].append({"id": "b", "parent_id": "a", "transform": T.IDENTITY})
    project_copy.edit("scene.json", f)
    assert "hierarchy cycle" in _problems(project_copy)


def test_two_roots_rejected(project_copy):
    project_copy.edit("scene.json", lambda d: d["assemblies"][1].__setitem__("parent_id", None))
    assert "exactly one root" in _problems(project_copy)


def test_mirror_transform_rejected(project_copy):
    project_copy.edit("scene.json", lambda d: d["occurrences"][2]["transform"][0].__setitem__(0, -1))
    assert "reflection" in _problems(project_copy)


def test_scaled_transform_rejected(project_copy):
    project_copy.edit("scene.json", lambda d: d["assemblies"][1]["transform"][1].__setitem__(1, 2))
    assert "not orthonormal" in _problems(project_copy)


def test_assembly_group_cannot_be_installed(project_copy):
    project_copy.edit("instructions.json", lambda d: d["steps"][1].__setitem__("add", ["pin-pair"]))
    p = _problems(project_copy)
    assert "unknown occurrence 'pin-pair' (an assembly group is not an installed part)" in p
    assert "never installed: ['pin-a']" in p


def test_duplicate_installation_rejected(project_copy):
    project_copy.edit("instructions.json", lambda d: d["steps"][2].__setitem__("add", ["pin-a"]))
    p = _problems(project_copy)
    assert "installed again (first in step 'insert-pin-a')" in p
    assert "never installed: ['pin-b']" in p


def test_prerequisite_must_be_earlier(project_copy):
    project_copy.edit("instructions.json", lambda d: d["steps"][0].__setitem__("requires", ["insert-pin-b"]))
    assert "'insert-pin-b' is not an earlier step" in _problems(project_copy)


def test_self_prerequisite(project_copy):
    project_copy.edit("instructions.json", lambda d: d["steps"][1].__setitem__("requires", ["insert-pin-a"]))
    assert "a step cannot require itself" in _problems(project_copy)


def test_unknown_view_and_bad_approach(project_copy):
    def f(d):
        d["steps"][1]["view"] = "side"
        d["steps"][1]["approach"]["occurrence_id"] = "pin-b"
        d["steps"][2]["approach"]["end_offset"] = [0, 0, 5]
        d["steps"][2]["approach"]["validation"] = "verified"
    project_copy.edit("instructions.json", f)
    p = _problems(project_copy)
    assert "unknown view 'side'" in p
    assert "'pin-b' is not added by this step" in p
    assert "end_offset: must be zero" in p
    assert "validation: only" in p


def test_up_parallel_to_view_rejected(project_copy):
    def f(d):
        d["views"][0]["eye"] = [0, 0, 100]; d["views"][0]["target"] = [0, 0, 0]
    project_copy.edit("instructions.json", f)
    assert "parallel to the view direction" in _problems(project_copy)


def test_inventory_mismatch(project_copy):
    project_copy.edit("inventory.json", lambda d: d["items"][1].__setitem__("required", 3))
    assert "required 3 for 'pin' but the scene installs 2" in _problems(project_copy)


def test_inventory_missing_row_and_unknown_part(project_copy):
    project_copy.edit("inventory.json", lambda d: d["items"][0].__setitem__("part_id", "washer"))
    p = _problems(project_copy)
    assert "unknown part 'washer'" in p and "no row for part(s) ['base']" in p


def test_inventory_counted_must_be_null_or_int(project_copy):
    project_copy.edit("inventory.json", lambda d: d["items"][1].__setitem__("counted", "two"))
    assert "counted: expected null or a non-negative integer" in _problems(project_copy)


def test_review_state_enum(project_copy):
    project_copy.edit("instructions.json", lambda d: d.__setitem__("review_state", "approved"))
    assert "review_state: expected one of" in _problems(project_copy)


def test_instructions_must_reference_loaded_scene(project_copy):
    project_copy.edit("instructions.json", lambda d: d.__setitem__("scene", "other.json"))
    assert "is not the loaded scene" in _problems(project_copy)


def test_all_problems_reported_together(project_copy):
    def f(d):
        d["parts"][0]["id"] = "bad id!"
        d["occurrences"][0]["transform"][3][3] = 2
    project_copy.edit("scene.json", f)
    p = _problems(project_copy)
    assert "identifier must match" in p and "last row" in p
