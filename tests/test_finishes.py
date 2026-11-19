"""finishes.json: what a picture draws each part with. The loader, the look a part gets, and what the manual stage refuses."""
import json
from pathlib import Path

import pytest

from mechanical_docs import document, looks, views
from mechanical_docs.manifest import ManifestError, load_finishes, load_project, load_scene_only
from mechanical_docs.render_settings import DEFAULTS, load_settings

TWO_BASES = Path(__file__).resolve().parents[1] / "examples" / "two-bases-fixture"
GOOD = {"schema_version": 1, "scene": "scene.json",
        "source": {"kind": "mechanical-cad-finishes", "file": "finishes.toml", "sha256": "a" * 64},
        "finishes": {"black-anodized": {"color": "#18181A", "metallic": 0.6, "roughness": 0.42, "opacity": 1.0},
                     "smoked-acrylic": {"color": "#404850", "metallic": 0.0, "roughness": 0.1, "opacity": 0.4}},
        "parts": {"base": "black-anodized", "pin": None}}


def write(project_copy, change=None):
    """The three-part fixture with a finishes.json: GOOD, or GOOD after `change` has had its way with it."""
    data = json.loads(json.dumps(GOOD))
    if change is not None:
        change(data)
    (project_copy.dir / "finishes.json").write_text(json.dumps(data, indent=2))
    return project_copy


def problems(project_copy, change):
    with pytest.raises(ManifestError) as ei:
        load_project(write(project_copy, change).dir)
    return "\n".join(ei.value.problems)


# ------------------------------------------------------------------ the loader

def test_a_project_without_the_file_is_as_it_was(fixture_dir):
    pr = load_project(fixture_dir)
    assert pr.finishes is None and "finishes.json" not in pr.input_hashes()
    assert len(pr.input_hashes()) == 7


def test_the_file_is_loaded_and_is_a_render_input_but_not_a_geometry_input(project_copy):
    pr = load_project(write(project_copy).dir)
    f = pr.finishes
    assert f.parts == {"base": "black-anodized", "pin": None}
    assert f.finishes["black-anodized"] == {"color": "#18181a", "metallic": 0.6, "roughness": 0.42, "opacity": 1.0}      # the hex in lower case
    assert f.source["file"] == "finishes.toml" and f.file.name == "finishes.json" and len(f.sha256) == 64
    assert f.of("base") == ("black-anodized", f.finishes["black-anodized"]) and f.of("pin") is None and f.of("nothing") is None
    assert pr.input_hashes()["finishes.json"] == f.sha256
    assert "finishes.json" in pr.render_input_hashes()          # a changed finish changes pictures
    assert "finishes.json" not in pr.non_render_inputs()
    assert set(pr.geometry_input_hashes()) == {"scene.json", "assets/base.step", "assets/pin.step"}      # and no mesh


def test_the_fixture_with_finishes_loads():
    pr = load_project(TWO_BASES)
    assert pr.finishes.parts == {"base": "clear-acrylic", "pin": "brass"}
    assert pr.finishes.finishes["clear-acrylic"]["opacity"] == 0.35
    assert sorted(pr.input_hashes()) == ["assets/base.step", "assets/pin.step", "finishes.json", "instructions.json", "inventory.json", "scene.json"]


def test_schema_version_is_the_integer_one(project_copy):
    for bad in ("1", 2, 1.5, None):
        assert "finishes: schema_version must be 1" in problems(project_copy, lambda d, bad=bad: d.__setitem__("schema_version", bad))
    assert "must be the integer 1" in problems(project_copy, lambda d: d.__setitem__("schema_version", True))


def test_unknown_and_missing_fields_are_refused(project_copy):
    assert "finishes: unsupported field(s) ['default']" in problems(project_copy, lambda d: d.__setitem__("default", "black-anodized"))
    for key in ("scene", "finishes", "parts"):
        assert f"finishes: missing field {key!r}" in problems(project_copy, lambda d, key=key: d.pop(key))
    write(project_copy, lambda d: d.pop("source"))               # the source is optional
    assert load_project(project_copy.dir).finishes.source == {}
    assert "finishes.source.where: expected a string, number, boolean or null" in problems(project_copy, lambda d: d["source"].__setitem__("where", {"a": 1}))


def test_the_scene_named_must_be_the_one_loaded(project_copy):
    assert "finishes.scene: 'other.json' is not the loaded scene 'scene.json'" in problems(project_copy, lambda d: d.__setitem__("scene", "other.json"))
    assert "finishes.scene: expected the scene file's relative path" in problems(project_copy, lambda d: d.__setitem__("scene", 3))


def test_a_finish_has_a_plain_name_and_exactly_its_four_fields(project_copy):
    def rename(new):
        return lambda d: (d["finishes"].__setitem__(new, d["finishes"].pop("black-anodized")), d["parts"].__setitem__("base", new))
    for bad in ("Black Anodized", "black--anodized", "black_anodized", "-black", ""):
        assert "a finish's name is lower-case letters and digits in groups joined by single hyphens" in problems(project_copy, rename(bad))
    said = problems(project_copy, lambda d: d["finishes"]["black-anodized"].pop("opacity"))
    assert "missing field(s) ['opacity']; every field of a finish is explicit" in said
    assert "unsupported field(s) ['note']" in problems(project_copy, lambda d: d["finishes"]["black-anodized"].__setitem__("note", "x"))
    assert "finishes.finishes['black-anodized']: expected an object" in problems(project_copy, lambda d: d["finishes"].__setitem__("black-anodized", "#000000"))
    assert "finishes.finishes: expected an object of named finishes" in problems(project_copy, lambda d: d.__setitem__("finishes", []))


def test_a_colour_is_six_hex_digits_and_the_numbers_lie_between_nought_and_one(project_copy):
    for bad in ("red", "#fff", "#gggggg", "18181a", "#18181a00", [0.1, 0.1, 0.1], None):
        assert "color: expected an sRGB colour as #rrggbb" in problems(project_copy, lambda d, bad=bad: d["finishes"]["black-anodized"].__setitem__("color", bad))
    for field in ("metallic", "roughness"):
        for bad in (-0.1, 1.5, "0.5", True, None):
            said = problems(project_copy, lambda d, bad=bad, field=field: d["finishes"]["black-anodized"].__setitem__(field, bad))
            assert f"{field}: expected a number from 0 to 1, got {bad!r}" in said
        write(project_copy, lambda d, field=field: d["finishes"]["black-anodized"].__setitem__(field, 0))        # nought is a value
        assert load_project(project_copy.dir).finishes.finishes["black-anodized"][field] == 0.0
    for bad in (0, 0.0, 1.01, -1, False):
        said = problems(project_copy, lambda d, bad=bad: d["finishes"]["black-anodized"].__setitem__("opacity", bad))
        assert f"opacity: expected a number from 0 to 1, above 0, got {bad!r}" in said


def test_every_part_of_the_scene_has_an_entry_and_no_other(project_copy):
    assert "finishes.parts: no entry for ['pin']; every part of the scene has one" in problems(project_copy, lambda d: d["parts"].pop("pin"))
    assert "finishes.parts['washer']: not a part of the scene" in problems(project_copy, lambda d: d["parts"].__setitem__("washer", None))
    said = problems(project_copy, lambda d: d["parts"].__setitem__("pin", "chrome"))
    assert "finishes.parts['pin']: expected the name of a finish defined in this file, or null when nobody has said, got 'chrome'" in said
    assert "got 3" in problems(project_copy, lambda d: d["parts"].__setitem__("pin", 3))
    assert "finishes.parts: expected an object with an entry for every part of the scene" in problems(project_copy, lambda d: d.__setitem__("parts", ["base"]))
    # an occurrence or an assembly is not a part
    assert "finishes.parts['pin-a']: not a part of the scene" in problems(project_copy, lambda d: d["parts"].__setitem__("pin-a", None))


def test_every_problem_is_reported_together(project_copy):
    def spoil(d):
        d["finishes"]["black-anodized"]["color"] = "black"
        d["finishes"]["smoked-acrylic"]["opacity"] = 0
        d["parts"]["washer"] = None
        d["extra"] = 1
    said = problems(project_copy, spoil)
    for piece in ("unsupported field(s) ['extra']", "color: expected an sRGB colour", "opacity: expected a number", "'washer']: not a part"):
        assert piece in said
    assert "finishes.parts['base']" not in said          # one finding per fault: the base's finish is named, and spoilt


def test_a_finish_nothing_uses_and_a_part_without_one_are_both_fine(project_copy):
    pr = load_project(write(project_copy, lambda d: d["parts"].update(base=None, pin=None)).dir)
    assert pr.finishes.parts == {"base": None, "pin": None} and set(pr.finishes.finishes) == {"black-anodized", "smoked-acrylic"}
    pr = load_project(write(project_copy, lambda d: (d.__setitem__("finishes", {}), d["parts"].update(base=None))).dir)
    assert pr.finishes.finishes == {}


def test_load_finishes_alone_raises_what_it_finds(project_copy):
    scene = load_project(project_copy.dir).scene
    write(project_copy, lambda d: d["parts"].pop("pin"))
    with pytest.raises(ManifestError, match="no entry for"):
        load_finishes(project_copy.dir / "finishes.json", scene)
    with pytest.raises(ManifestError, match="file not found"):
        load_finishes(project_copy.dir / "none.json", scene)


def test_a_scene_alone_loads_with_its_finishes_and_without_the_rest(project_copy):
    write(project_copy)
    (project_copy.dir / "inventory.json").write_text("this is not read")
    pr = load_scene_only(project_copy.dir)
    assert pr.inventory is None and pr.instructions is None and pr.supplement is None and pr.build_scope is None
    assert pr.finishes.parts["base"] == "black-anodized"
    assert sorted(pr.input_hashes()) == ["assets/base.step", "assets/pin.step", "finishes.json", "scene.json"]
    assert sorted(pr.render_input_hashes()) == sorted(pr.input_hashes())
    assert sorted(pr.geometry_input_hashes()) == ["assets/base.step", "assets/pin.step", "scene.json"]
    (project_copy.dir / "finishes.json").unlink()
    assert load_scene_only(project_copy.dir).finishes is None
    write(project_copy, lambda d: d["parts"].pop("pin"))
    with pytest.raises(ManifestError, match="no entry for"):
        load_scene_only(project_copy.dir)


# ------------------------------------------------------------------ the look of a part

def test_srgb_to_linear():
    assert looks.hex_to_linear("#000000") == [0.0, 0.0, 0.0]
    assert looks.hex_to_linear("#ffffff") == pytest.approx([1.0, 1.0, 1.0])
    assert looks.hex_to_linear("#808080") == pytest.approx([0.21586050011389923] * 3)       # mid grey is a fifth, not a half
    assert looks.hex_to_linear("#0A141E") == pytest.approx([10 / 255 / 12.92, 0.006995410187265387, 0.012983032342173012])     # below and above the knee
    assert looks.hex_to_srgb("#ff8000") == pytest.approx([1.0, 128 / 255, 0.0])
    for bad in ("ff8000", "#ff80", "#ff80zz", None, 3):
        with pytest.raises(looks.LookError):
            looks.hex_to_linear(bad)


def settings(**over):
    s = json.loads(json.dumps(DEFAULTS))
    s.update(over)
    return s


def test_render_json_holds_then_the_finish_then_the_default(project_copy):
    f = load_project(write(project_copy, lambda d: d["parts"].update(pin="smoked-acrylic")).dir).finishes
    # nothing said in render.json: each part in its finish
    got = looks.resolve(["base", "pin"], settings(), f)
    assert got["base"] == {"look": "black-anodized", "source": "finishes.json", "base": pytest.approx([0.009134, 0.009134, 0.010330], abs=1e-6),
                           "metallic": 0.6, "roughness": 0.42, "opacity": 1.0}
    assert got["pin"]["look"] == "smoked-acrylic" and got["pin"]["opacity"] == 0.4 and got["pin"]["source"] == "finishes.json"
    # render.json names a look for the base: that holds, and the pin keeps its finish
    got = looks.resolve(["base", "pin"], settings(looks={"base": "aluminium"}), f)
    assert got["base"] == {"look": "aluminium", "source": "render.json", "base": [0.62, 0.63, 0.65], "metallic": 0.8, "roughness": 0.55, "opacity": 1.0}
    assert got["pin"]["source"] == "finishes.json"
    # a part whose finish is null, and a project without the file, get the default look
    none = load_project(write(project_copy).dir).finishes
    assert looks.resolve(["pin"], settings(), none)["pin"] == {"look": "grey-plastic", "source": "default", "base": [0.30, 0.31, 0.33],
                                                                "metallic": 0.0, "roughness": 0.55, "opacity": 1.0}
    assert looks.resolve(["base", "pin"], settings(default_look="brass"), None) == {
        pid: {"look": "brass", "source": "default", "base": [0.78, 0.56, 0.20], "metallic": 1.0, "roughness": 0.35, "opacity": 1.0} for pid in ("base", "pin")}


def test_an_unknown_look_is_refused_and_a_coat_is_carried():
    with pytest.raises(looks.LookError, match="unknown look 'chrome-ish' for part 'base'"):
        looks.resolve(["base"], settings(looks={"base": "chrome-ish"}), None)
    with pytest.raises(looks.LookError, match="unknown look 'nothing'"):
        looks.resolve(["base"], settings(default_look="nothing"), None)
    s = settings(looks={"base": "lacquer"})
    s["palette"]["lacquer"] = {"base": [0.5, 0.1, 0.1], "coat": 1.0}
    assert looks.resolve(["base"], s, None)["base"] == {"look": "lacquer", "source": "render.json", "base": [0.5, 0.1, 0.1], "metallic": 0.0,
                                                        "roughness": 0.5, "opacity": 1.0, "coat": 1.0, "coat_roughness": 0.1}


def test_a_finish_and_a_palette_entry_of_one_name_are_two_materials(project_copy):
    f = load_project(write(project_copy, lambda d: (d["finishes"].__setitem__("brass", d["finishes"].pop("black-anodized")),
                                                    d["parts"].update(base="brass"))).dir).finishes
    got = looks.resolve(["base", "pin"], settings(looks={"pin": "brass"}), f)
    assert looks.material_key(got["base"]) == "finish:brass" and looks.material_key(got["pin"]) == "look:brass"
    assert got["base"]["base"] != got["pin"]["base"]


def test_the_fixture_draws_the_base_in_its_finish_and_the_pin_as_render_json_says():
    pr = load_project(TWO_BASES)
    s, _ = load_settings(pr.dir)
    got = looks.resolve(pr.scene.parts, s, pr.finishes)
    assert (got["base"]["look"], got["base"]["source"], got["base"]["opacity"]) == ("clear-acrylic", "finishes.json", 0.35)
    assert (got["pin"]["look"], got["pin"]["source"]) == ("red-plastic", "render.json")      # its finish is brass; render.json holds
    assert json.loads(json.dumps(got)) == got                    # what a receipt reads back is what is computed again


# ------------------------------------------------------------------ where a still's camera stands

def test_another_axis_may_be_up_in_the_picture():
    """A scene declared Z up that stands otherwise, or a long thing that should lie across the picture."""
    assert views.up("+y") == (0.0, 1.0, 0.0) and views.up("-X") == (-1.0, 0.0, 0.0) and views.up("0, 2,1") == (0.0, 2.0, 1.0)
    for wrong in ("up", "0,0,0", "1,2"):
        with pytest.raises(views.ViewError, match="--up: expected an axis"):
            views.up(wrong)
    assert views.turned(views.stands("iso"), views.up("+y")) == ((1.0, -1.0, 0.8), (0.0, 1.0, 0.0))
    assert views.turned(views.direction("0.4,1,0.3"), views.up("-x")) == ((0.4, 1.0, 0.3), (-1.0, 0.0, 0.0))
    # a camera cannot look along what is to be up in its picture
    with pytest.raises(views.ViewError, match="looks along .* which cannot be up in its picture"):
        views.turned(views.stands("+y"), views.up("+y"))
    with pytest.raises(views.ViewError, match="cannot be up in its picture"):
        views.turned(views.stands("-z"), views.up("0,0,5"))


# ------------------------------------------------------------------ the viewer's models

def test_a_project_that_chose_nothing_keeps_one_flat_material():
    flat = {"name": "flat"}
    nothing = looks.resolve(["base", "pin"], settings(), None)
    assert looks.chosen(nothing) is False
    assert looks.viewer_materials(nothing, flat) == ([flat], {"base": 0, "pin": 0})


def test_a_chosen_look_is_a_material_of_the_viewer_s_model():
    pr = load_project(TWO_BASES)
    s, _ = load_settings(pr.dir)
    resolved = looks.resolve(pr.scene.parts, s, pr.finishes)
    assert looks.chosen(resolved)
    flat = {"name": "flat"}
    materials, of = looks.viewer_materials(resolved, flat)
    assert materials[0] is flat and [m["name"] for m in materials[1:]] == ["clear-acrylic", "red-plastic"]
    assert of == {"base": 1, "pin": 2}
    acrylic, red = materials[1], materials[2]
    # the base's finish: its colour as light adds up, its opacity as the alpha, and blended, since it lets light through
    assert acrylic["pbrMetallicRoughness"]["baseColorFactor"] == resolved["base"]["base"] + [0.35]
    assert acrylic["alphaMode"] == "BLEND" and acrylic["extras"] == {"source": "finishes.json"} and acrylic["doubleSided"] is True
    assert (acrylic["pbrMetallicRoughness"]["metallicFactor"], acrylic["pbrMetallicRoughness"]["roughnessFactor"]) == (0.0, 0.15)
    # the pin as render.json says, opaque: no alpha mode is said, which is opaque
    assert red["extras"] == {"source": "render.json"} and "alphaMode" not in red and red["pbrMetallicRoughness"]["baseColorFactor"][3] == 1.0


def test_parts_of_one_look_share_a_material_and_the_default_stays_flat(project_copy):
    f = load_project(write(project_copy).dir).finishes
    resolved = looks.resolve(["base", "pin", "washer", "nut"], settings(looks={"washer": "brass", "nut": "brass"}), f)
    materials, of = looks.viewer_materials(resolved, {"name": "flat"})
    # base has a finish, the pin has none and is in the default look, washer and nut share a palette entry
    assert [m["name"] for m in materials] == ["flat", "black-anodized", "brass"]
    assert of == {"base": 1, "pin": 0, "washer": 2, "nut": 2}
    # a finish and a palette entry of one name stay two materials
    twice = looks.resolve(["base", "pin"], settings(looks={"pin": "black-anodized"}), f)
    materials, of = looks.viewer_materials(twice, {"name": "flat"})
    assert [m["name"] for m in materials] == ["flat", "black-anodized", "black-anodized"] and of == {"base": 1, "pin": 2}
    assert [m["extras"]["source"] for m in materials[1:]] == ["finishes.json", "render.json"]


def test_named_views_are_those_of_mechanical_cad_picture():
    assert views.stands("iso") == ((1.0, -1.0, 0.8), views.Z_UP)
    assert views.stands("iso-back") == ((-1.0, 1.0, 0.8), views.Z_UP)
    assert views.stands("below") == ((1.0, -1.0, -0.8), views.Z_UP)
    assert views.stands("below-back") == ((-1.0, 1.0, -0.8), views.Z_UP)
    assert views.stands("+X") == ((1.0, 0.0, 0.0), views.Z_UP) and views.stands("-y") == ((0.0, -1.0, 0.0), views.Z_UP)
    # straight along Z the picture is a plan: Y is up, so that from above X runs to the right
    assert views.stands("+z") == ((0.0, 0.0, 1.0), views.Y_UP) and views.stands("-z") == ((0.0, 0.0, -1.0), views.Y_UP)
    with pytest.raises(views.ViewError, match="unknown view 'front'; known: iso, iso-back, below, below-back"):
        views.stands("front")
    assert [views.file_name(v) for v in ("iso", "+x", "-Z", "below-back")] == ["iso", "plus-x", "minus-z", "below-back"]


def test_a_plan_from_above_has_x_to_the_right_and_y_upwards():
    def cross(a, b):
        return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])
    for view, right_wanted in (("+z", (1.0, 0.0, 0.0)), ("-z", (-1.0, 0.0, 0.0))):
        stands, up = views.stands(view)
        forward = tuple(-c for c in stands)                      # the camera looks at the middle
        right = cross(forward, up)
        assert right == right_wanted and cross(right, forward) == (0.0, 1.0, 0.0)


def test_a_direction_given_in_numbers():
    assert views.direction("1,-2,0.5") == ((1.0, -2.0, 0.5), views.Z_UP)
    assert views.direction("0,0,-3") == ((0.0, 0.0, -3.0), views.Y_UP)
    for bad in ("1,2", "0,0,0", "a,b,c", ""):
        with pytest.raises(views.ViewError):
            views.direction(bad)


# ------------------------------------------------------------------ the manual stage

def receipt_for(project):
    return {"kind": "mechanical-docs-render-receipt", "input_hashes": project.input_hashes(), "views": [], "partial": False, "all_checks_passed": True}


def refused(project, receipt):
    """What the manual stage says of the receipt's inputs, or None when it takes them. The fake receipt has no
    views, which the stage says next; that is another matter."""
    with pytest.raises(document.DocumentError) as ei:
        document.build_model(project, receipt)
    return str(ei.value) if "render receipt was made from" in str(ei.value) else None


def test_the_manual_stage_refuses_renders_made_with_other_finishes(project_copy):
    without = load_project(project_copy.dir)
    with_finishes = load_project(write(project_copy).dir)
    changed = load_project(write(project_copy, lambda d: d["finishes"]["black-anodized"].__setitem__("color", "#202020")).dir)
    wanted = "different scene, assets, instructions or finishes: ['finishes.json']"
    assert refused(with_finishes, receipt_for(with_finishes)) is None
    assert refused(without, receipt_for(without)) is None
    assert wanted in refused(changed, receipt_for(with_finishes))               # a finish changed after the render
    assert wanted in refused(with_finishes, receipt_for(without))               # the file came after the render
    assert wanted in refused(without, receipt_for(with_finishes))               # the file went after the render
