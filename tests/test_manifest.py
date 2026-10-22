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
    assert len(pr.input_hashes()) == 6      # scene, instructions, inventory, supplement, two assets
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


def test_inventory_counted_is_not_data(project_copy):
    project_copy.edit("inventory.json", lambda d: d["items"][1].__setitem__("counted", "two"))
    assert "counted: the counted box is paper only and not a data field" in _problems(project_copy)


def test_review_state_enum(project_copy):
    project_copy.edit("instructions.json", lambda d: d.__setitem__("review_state", "approved"))
    assert "review_state: expected one of" in _problems(project_copy)


def test_instructions_must_reference_loaded_scene(project_copy):
    project_copy.edit("instructions.json", lambda d: d.__setitem__("scene", "other.json"))
    assert "is not the loaded scene" in _problems(project_copy)


def test_all_problems_reported_together(project_copy):
    def f(d):
        d["parts"][0]["id"] = "bad\nid"
        d["occurrences"][0]["transform"][3][3] = 2
    project_copy.edit("scene.json", f)
    p = _problems(project_copy)
    assert "identifier must be a non-empty string" in p and "last row" in p


# ---------------------------------------------------------------- production fields

import json as _json


def _production_scene(project_copy):
    """The fixture scene rewritten the way the Windows exporter writes one: Y up with a declared
    basis, Vault-style ids, provenance and BOM fields, a declared world matrix per occurrence."""
    def f(d):
        d["coordinate_system"] = {"handedness": "right", "up_axis": "+Y", "origin": "native origin",
                                  "note": "native Inventor frame", "basis_to_z_up": [[1, 0, 0, 0], [0, 0, -1, 0], [0, 1, 0, 0], [0, 0, 0, 1]]}
        d["source"] = {"kind": "autodesk-inventor-vault-snapshot", "vault_id": "28", "root_version_id": None, "occurrence_id_scope": "snapshot paths"}
        for part in d["parts"]:
            part["id"] = "DATA\\COMMON\\" + part["id"] + ".ipt|[Primary]"
            part.update({"model_state": "[Primary]", "bodies": {"surface_bodies": 1, "solid_bodies": 1, "visible_solid_bodies": 1},
                         "volume_mm3": 1.0, "bom_structure_default": "Normal",
                         "properties": {"part_number": "", "material": "Zinc", "vendor": None},
                         "source": {"vault_id": "28", "version_id": "953899", "native_sha256": "ab" * 32}})
            part["identifying_dimensions_mm"] = {"extent": [10, 10, 30]}
        d["assemblies"][1].update({"document": "C:\\x\\pin-pair.iam", "bom_structure": "Normal", "model_state": "[Primary]", "suppressed": False, "visible": True, "flexible": True})
        for o in d["occurrences"]:
            o["part_id"] = "DATA\\COMMON\\" + o["part_id"] + ".ipt|[Primary]"
            o["id"] = ("pin-pair:1/" if o["parent_id"] == "pin-pair" else "") + o["id"].upper() + ":1"
            o.update({"position_overridden_vs_definition": False, "parent_flexible": o["parent_id"] == "pin-pair", "visible": True,
                      "visible_effective": True, "suppressed": False, "grounded": False, "mirrored": False, "bom_structure": "Normal", "model_state": "[Primary]"})
        # native-frame world matrices: parent translation (10,0,0) + child
        for o in d["occurrences"]:
            tx = o["transform"][0][3] + (10 if o["parent_id"] == "pin-pair" else 0)
            o["transform_world"] = [[1, 0, 0, tx], [0, 1, 0, 0], [0, 0, 1, 0], [0, 0, 0, 1]]
    project_copy.edit("scene.json", f)
    (project_copy.dir / "instructions.json").unlink()
    (project_copy.dir / "supplement.json").unlink()      # its scene ids are the fixture's, not the production-style ones
    inv = _json.loads((project_copy.dir / "inventory.json").read_text())
    for row in inv["items"]:
        row["part_id"] = "DATA\\COMMON\\" + row["part_id"] + ".ipt|[Primary]"
    (project_copy.dir / "inventory.json").write_text(_json.dumps(inv))


def test_production_style_scene_loads_without_instructions(project_copy):
    _production_scene(project_copy)
    pr = load_project(project_copy.dir)
    assert pr.instructions is None and not pr.has_instructions
    sc = pr.scene
    assert sc.native_up_axis == "+Y"
    pin_a = sc.occurrences["pin-pair:1/PIN-A:1"]
    # native (x, y, z) -> z-up (x, -z, y): the pin's native translation (-25, 0, 0) stays on X
    assert T.translation(pin_a.world) == pytest.approx([-25, 0, 0])
    # a native +Y offset becomes +Z after the basis
    assert T.apply(sc.basis_to_z_up, [0, 5, 0]) == pytest.approx([0, 0, 5])
    assert sc.transform_world_check == {"checked": 3, "max_deviation": pytest.approx(0)}
    part = sc.parts["DATA\\COMMON\\pin.ipt|[Primary]"]
    assert part.model_state == "[Primary]" and part.properties["material"] == "Zinc" and part.identifying_dimensions_mm["extent"] == [10, 10, 30]
    assert sc.assemblies["pin-pair"].flexible is True and pin_a.parent_flexible is True
    assert "instructions.json" not in pr.input_hashes()


def test_y_up_requires_a_correct_basis(project_copy):
    project_copy.edit("scene.json", lambda d: d["coordinate_system"].__setitem__("up_axis", "+Y"))
    assert "requires 'basis_to_z_up'" in _problems(project_copy)
    project_copy.edit("scene.json", lambda d: d["coordinate_system"].__setitem__("basis_to_z_up", T.IDENTITY))
    assert "must map native +Y to +Z" in _problems(project_copy)


def test_declared_world_matrix_must_match_hierarchy(project_copy):
    project_copy.edit("scene.json", lambda d: d["occurrences"][1].__setitem__("transform_world", T.translate(-24, 0, 0)))
    assert "transform_world: differs from the composed parent chain" in _problems(project_copy)


def test_suppressed_and_mirrored_flags_rejected(project_copy):
    def f(d):
        d["occurrences"][1]["suppressed"] = True
        d["occurrences"][2]["mirrored"] = True
        d["assemblies"][1]["suppressed"] = True
    project_copy.edit("scene.json", f)
    p = _problems(project_copy)
    assert "suppressed occurrences are not accepted" in p and "mirrored occurrences must be exported" in p and "suppressed assemblies are not accepted" in p


def test_reference_geometry_is_not_installed(project_copy):
    project_copy.edit("scene.json", lambda d: d["occurrences"][2].__setitem__("bom_structure", "Reference"))
    p = _problems(project_copy)
    assert "required 2 for 'pin' but the scene installs 1" in p and "reference-only occurrences do not count" in p
    assert "'pin-b' is reference-only geometry" in p
    project_copy.edit("inventory.json", lambda d: d["items"][1].__setitem__("required", 1))
    (project_copy.dir / "instructions.json").unlink()
    pr = load_project(project_copy.dir)
    assert [o.id for o in pr.scene.installed_occurrences_of("pin")] == ["pin-a"]


def test_nested_source_values_rejected(project_copy):
    project_copy.edit("scene.json", lambda d: d["parts"][0].__setitem__("properties", {"x": {"nested": 1}}))
    assert "nested data is not accepted" in _problems(project_copy)


def test_inventory_template(fixture_dir):
    from mechanical_docs.manifest import inventory_template, load_scene
    sc = load_scene(fixture_dir / "scene.json")
    t = inventory_template(sc)
    assert t["items"] == [{"part_id": "base", "required": 1, "unit": "each"}, {"part_id": "pin", "required": 2, "unit": "each"}]
    assert "not a purchase list" in t["status"]


def test_require_instructions_flag(project_copy):
    (project_copy.dir / "instructions.json").unlink()
    with pytest.raises(ManifestError, match="instructions: file not found"):
        load_project(project_copy.dir, require_instructions=True)


def test_coincident_occurrences_are_a_finding_not_an_error(project_copy):
    """Two pins at the same world pose: kept, counted, and reported for review."""
    project_copy.edit("scene.json", lambda d: d["occurrences"][2].__setitem__("transform", d["occurrences"][1]["transform"]))
    pr = load_project(project_copy.dir)          # inventory still requires 2 pins: both instances count
    sc = pr.scene
    assert len(sc.coincident) == 1
    assert sc.coincident[0]["part_id"] == "pin" and sorted(sc.coincident[0]["occurrences"]) == ["pin-a", "pin-b"]
    assert sc.coincident[0]["max_deviation"] == 0
    assert sc.coincident_of("base") == []
    assert len(load_project(FIXTURE_DIR_FOR_COINCIDENT()).scene.coincident) == 0


def FIXTURE_DIR_FOR_COINCIDENT():
    from pathlib import Path
    return Path(__file__).resolve().parents[1] / "examples" / "three-part-fixture"


def test_render_input_hashes_exclude_inventory_and_supplement(fixture_dir):
    """A stock record or a supplement row never changes an image, so --reuse compares only the rest."""
    pr = load_project(fixture_dir)
    assert set(pr.input_hashes()) - set(pr.render_input_hashes()) == {"inventory.json", "supplement.json"}
    assert set(pr.render_input_hashes()) == {"scene.json", "instructions.json", "assets/base.step", "assets/pin.step"}
    assert pr.non_render_inputs() == {"inventory.json", "supplement.json"}
    # meshes depend on geometry only: scene and assets
    assert set(pr.geometry_input_hashes()) == {"scene.json", "assets/base.step", "assets/pin.step"}
