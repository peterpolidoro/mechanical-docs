"""Per-view staleness of reused renders under changed settings."""
from mechanical_docs.reuse import stale_reason

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
