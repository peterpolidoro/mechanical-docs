"""Per-view staleness of reused renders under changed settings."""
from mechanical_docs.reuse import look_reason, shown_in_look, stale_reason

SPEC = {"joint-a": {"occurrence_ids": ["x", "y"], "context": ["G"], "context_style": "faded", "direction": [1.0, -1.2, 0.8]}}
OLD = {"id": "joint-a", "kind": "joint", "occurrence_ids": ["x", "y"], "context_assembly": "G", "context_style": "faded",
       "direction": [0.5698, -0.6838, 0.4558], "direction_from_settings": True, "visible_triangles": 500000, "lines": False}


def test_unchanged_joint_view_is_reusable():
    assert stale_reason(OLD, SPEC, True, 400000) is None
    # float32 rounding of the recorded unit vector must not count as a change
    assert stale_reason({**OLD, "direction": [-0.3754, -0.3754, 0.8479]}, {"joint-a": {**SPEC["joint-a"], "direction": [-0.375, -0.375, 0.848]}}, True, 400000) is None


def test_joint_specification_changes_are_detected():
    assert stale_reason(OLD, {"joint-a": {**SPEC["joint-a"], "direction": [0, -1, 0.3]}}, True, 400000) == "joint direction changed"
    assert stale_reason(OLD, {"joint-a": {**SPEC["joint-a"], "context": ["root"]}}, True, 400000) == "joint context changed"
    assert stale_reason({**OLD, "context_ids": ["G", "o1"]}, SPEC, True, 400000) == "joint context changed"
    assert stale_reason({**OLD, "context_ids": ["G"]}, SPEC, True, 400000) is None
    assert stale_reason(OLD, {"joint-a": {**SPEC["joint-a"], "context_style": "hidden"}}, True, 400000) == "joint context style changed"
    assert stale_reason(OLD, {"joint-a": {**SPEC["joint-a"], "occurrence_ids": ["x"]}}, True, 400000) == "joint occurrences changed"
    assert stale_reason(OLD, {}, True, 400000) == "joint view no longer configured"
    # a direction left to the default after being explicit, and the reverse, both re-render
    assert stale_reason(OLD, {"joint-a": {**SPEC["joint-a"], "direction": None}}, True, 400000) == "joint direction no longer set"
    assert stale_reason({**OLD, "direction_from_settings": False}, SPEC, True, 400000) == "joint direction changed"


def test_newly_affordable_outlines_make_a_copy_stale_but_a_lower_cap_does_not():
    group = {"id": "group-g", "kind": "group", "visible_triangles": 546280, "lines": False}
    assert stale_reason(group, {}, True, 400000) is None
    assert stale_reason(group, {}, True, 600000).startswith("line art is now within the budget")
    # an outlined image stays valid under a lower cap or --no-lines: the budget caps cost, it is not a look
    assert stale_reason({**group, "lines": True}, {}, True, 400000) is None
    assert stale_reason({**group, "lines": True}, {}, False, 600000) is None
    outlined_overview = {"id": "overview", "kind": "overview", "visible_triangles": 2436488, "lines": True}
    assert stale_reason(outlined_overview, {}, True, 600000) is None
    assert stale_reason({**outlined_overview, "lines": False}, {}, True, 600000) is None
    assert stale_reason({"id": "part-x", "kind": "part-thumbnail"}, {}, True, 600000) is None      # no record of lines: reusable


def test_exploded_view_staleness():
    old = {"id": "exploded", "kind": "exploded", "offsets_mm": {"A": [0, 0, 100.0], "root-parts": [0, 0, -100.0]}, "direction": [0.5698, -0.6838, 0.4558],
           "direction_from_settings": False, "lines": True, "visible_triangles": 10}
    same = {"enabled": True, "offsets_mm": {"A": [0, 0, 100.0], "root-parts": [0, 0, -100.0]}, "direction": None}
    assert stale_reason(old, {}, True, 1000, same) is None
    assert stale_reason(old, {}, True, 1000, None) == "exploded view no longer configured"
    assert stale_reason(old, {}, True, 1000, dict(same, enabled=False)) == "exploded view no longer configured"
    assert stale_reason(old, {}, True, 1000, dict(same, offsets_mm={"A": [0, 0, 120.0], "root-parts": [0, 0, -100.0]})) == "exploded offsets changed"
    assert stale_reason(old, {}, True, 1000, dict(same, offsets_mm={"A": [0, 0, 100.0]})) == "exploded offsets changed"
    assert stale_reason(old, {}, True, 1000, dict(same, direction=[1, -1.2, 0.8])) == "exploded direction changed"
    assert stale_reason(dict(old, direction_from_settings=True), {}, True, 1000, dict(same, direction=[1, -1.2, 0.8])) is None
    assert stale_reason(dict(old, direction_from_settings=True), {}, True, 1000, same) == "exploded direction no longer set"


# ------------------------------------------------------------------ looks: a view is stale when a part it shows in its look has another

PART_OF = {"base-1": "base", "pin-a": "pin", "pin-b": "pin"}
ACRYLIC = {"look": "clear-acrylic", "source": "finishes.json", "base": [0.52, 0.77, 0.85], "metallic": 0.0, "roughness": 0.15, "opacity": 0.35}
RED = {"look": "red-plastic", "source": "render.json", "base": [0.6, 0.06, 0.05], "metallic": 0.0, "roughness": 0.45, "opacity": 1.0}
GREY = {"look": "grey-plastic", "source": "default", "base": [0.30, 0.31, 0.33], "metallic": 0.0, "roughness": 0.55, "opacity": 1.0}
THEN = {"base": ACRYLIC, "pin": RED}
VIEWS = {
    "part-base": {"id": "part-base", "kind": "part-thumbnail", "part_id": "base"},
    "part-pin": {"id": "part-pin", "kind": "part-thumbnail", "part_id": "pin"},
    "part-pin-end": {"id": "part-pin-end", "kind": "part-end", "part_id": "pin"},
    "overview": {"id": "overview", "kind": "overview", "visible": ["base-1", "pin-a", "pin-b"]},
    "exploded": {"id": "exploded", "kind": "exploded", "visible": ["base-1", "pin-a", "pin-b"], "offsets_mm": {"g": [0, 0, 1.0]},
                 "direction": [0.5698, -0.6838, 0.4558], "direction_from_settings": False},
    "group-pins": {"id": "group-pins", "kind": "group", "visible": ["pin-a", "pin-b"]},
    "still-iso": {"id": "still-iso", "kind": "still", "visible": ["base-1", "pin-a", "pin-b"]},
    # a joint shows its subjects in their looks; the context (the base here) is flat grey
    "joint-a": {"id": "joint-a", "kind": "joint", "occurrence_ids": ["pin-a", "pin-b"], "context_ids": ["G"], "context_style": "faded",
                "visible": ["pin-a", "pin-b", "base-1"], "context_occurrences": ["base-1"], "direction": [0.5698, -0.6838, 0.4558],
                "direction_from_settings": True},
    # a step shows what it adds; what was installed before is ghosted
    "step-01-base": {"id": "step-01-base", "kind": "step", "highlighted": ["base-1"], "subdued": [], "visible": ["base-1"]},
    "step-02-pins": {"id": "step-02-pins", "kind": "step", "highlighted": ["pin-a", "pin-b"], "subdued": ["base-1"], "visible": ["base-1", "pin-a", "pin-b"]},
    "step-02-pins-result": {"id": "step-02-pins-result", "kind": "step-result", "highlighted": ["pin-a", "pin-b"], "subdued": ["base-1"],
                            "visible": ["base-1", "pin-a", "pin-b"]},
}
JOINTS = {"joint-a": {"occurrence_ids": ["pin-a", "pin-b"], "context": ["G"], "context_style": "faded", "direction": [1.0, -1.2, 0.8]}}
EXPLODED = {"enabled": True, "offsets_mm": {"g": [0, 0, 1.0]}, "direction": None}
STEPS = {"step-01-base": (["base-1"], []), "step-02-pins": (["pin-a", "pin-b"], ["base-1"]), "step-02-pins-result": (["pin-a", "pin-b"], ["base-1"])}


def stale(then, now):
    """The ids of the views an earlier receipt (its part looks `then`, or None when it recorded none) cannot stand in for."""
    out = set()
    for vid, old in VIEWS.items():
        reason = stale_reason(old, JOINTS, True, 1000, EXPLODED, False, STEPS, (then, now, PART_OF))
        if reason is not None:
            assert "look" in reason
            out.add(vid)
    return out


def test_which_parts_a_view_shows_in_their_looks():
    shown = {vid: shown_in_look(old, PART_OF) for vid, old in VIEWS.items()}
    assert shown == {"part-base": ["base"], "part-pin": ["pin"], "part-pin-end": ["pin"], "overview": ["base", "pin"], "exploded": ["base", "pin"],
                     "group-pins": ["pin"], "still-iso": ["base", "pin"], "joint-a": ["pin"], "step-01-base": ["base"], "step-02-pins": ["pin"],
                     "step-02-pins-result": ["pin"]}
    assert shown_in_look({"id": "x", "kind": "overview"}, PART_OF) == []          # a record without the list shows nothing known


def test_unchanged_looks_stale_nothing():
    assert stale(THEN, dict(THEN)) == set()
    # and without the looks the judgement is what it was
    assert all(stale_reason(old, JOINTS, True, 1000, EXPLODED, False, STEPS) is None for old in VIEWS.values())


def test_a_changed_finish_stales_the_views_that_show_its_part_in_that_look():
    darker = {**THEN, "base": {**ACRYLIC, "base": [0.2, 0.3, 0.4]}}
    assert stale(THEN, darker) == {"part-base", "overview", "exploded", "still-iso", "step-01-base"}
    assert stale_reason(VIEWS["overview"], JOINTS, True, 1000, EXPLODED, False, STEPS, (THEN, darker, PART_OF)) == "the look of base changed"
    # the joint draws the base as grey context and the second step ghosts it: both stand
    clearer = {**THEN, "base": {**ACRYLIC, "opacity": 0.2}}
    assert stale(THEN, clearer) == {"part-base", "overview", "exploded", "still-iso", "step-01-base"}


def test_a_changed_look_in_render_json_is_detected_too():
    blue = {**THEN, "pin": {"look": "blue-anodized", "source": "render.json", "base": [0.05, 0.16, 0.55], "metallic": 0.3, "roughness": 0.4, "opacity": 1.0}}
    assert stale(THEN, blue) == {"part-pin", "part-pin-end", "overview", "exploded", "group-pins", "still-iso", "joint-a", "step-02-pins",
                                 "step-02-pins-result"}
    # the same numbers from another source are another look: the record says where it came from
    assert stale(THEN, {**THEN, "pin": {**RED, "source": "default"}}) == stale(THEN, blue)


def test_an_earlier_receipt_without_the_record():
    # no finishes file now: nothing could have changed its source, so the views are taken as they always were
    assert stale(None, {"base": GREY, "pin": RED}) == set()
    # the base now takes its look from finishes.json, which that receipt never saw: the views that show it are stale
    assert stale(None, THEN) == {"part-base", "overview", "exploded", "still-iso", "step-01-base"}
    reason = look_reason(VIEWS["part-base"], (None, THEN, PART_OF))
    assert reason == "the earlier receipt records no looks and base now takes its look from finishes.json"
    assert look_reason(VIEWS["part-pin"], (None, THEN, PART_OF)) is None


def test_other_reasons_come_before_the_look():
    darker = {**THEN, "pin": {**RED, "base": [0.1, 0.1, 0.1]}}
    assert stale_reason(VIEWS["joint-a"], {}, True, 1000, EXPLODED, False, STEPS, (THEN, darker, PART_OF)) == "joint view no longer configured"
    assert stale_reason(VIEWS["step-02-pins"], JOINTS, True, 1000, EXPLODED, True, STEPS, (THEN, darker, PART_OF)) == "instructions changed"
