"""Which views an earlier render receipt can still stand in for.

`render.py --reuse` copies a view from an earlier receipt made from the same
scene, assets, meshes, engine and quality (the instructions may differ: the
views that follow them are then stale). Several changes
are detected per view so a copy is never silently stale: a joint close-up
whose specification (occurrences, context, context style, explicit direction)
differs from the record, an exploded view whose offsets or explicit direction
changed, the overview and the steps when the instructions changed, a step
whose additions or installed-before set changed, and any view drawn without outlines that the current
line budget would now outline (a lower budget never discards an outlined
image: the budget caps cost, it is not a look). Other appearance changes
(looks, group direction, thumbnail rules, --no-lines) are not detected: name
those views with --views.
"""
from __future__ import annotations


def normalised(v):
    n = sum(x * x for x in v) ** 0.5
    return [round(x / n, 4) for x in v] if n > 1e-12 else [0.0, 0.0, 0.0]


def stale_reason(old, joint_specs, lines_enabled, budget, exploded=None, instructions_changed=False, step_states=None):
    """None when `old` (a view record from an earlier receipt) can be reused
    under the current settings, else a short reason.

    joint_specs: view id -> resolved joint spec (occurrence_ids, context,
    context_style, direction or None). lines_enabled/budget: the current run's
    line-art switch and visible-triangle budget. exploded: the resolved
    exploded-view plan (offsets_mm, direction) or None when none is drawn.
    instructions_changed: the instructions file differs from the old receipt's
    (the overview camera and every step follow it). step_states: view id ->
    (added, before) of the current derivation, so a step whose cumulative state
    changed (a build scope deferring an earlier step) is rendered again."""
    if old.get("kind") == "overview" and instructions_changed:
        return "instructions changed (the overview uses the first step's camera)"
    if old.get("kind") in ("step", "step-result"):
        if instructions_changed:
            return "instructions changed"
        if step_states is not None:
            cur = step_states.get(old["id"])
            if cur is None:
                return "step no longer in the procedure"
            if sorted(old.get("highlighted") or []) != sorted(cur[0]) or sorted(old.get("subdued") or []) != sorted(cur[1]):
                return "step state changed (additions or installed-before differ, e.g. a build scope)"
    if old.get("kind") == "exploded":
        if exploded is None or not exploded.get("enabled"):
            return "exploded view no longer configured"
        old_off = old.get("offsets_mm") or {}
        new_off = exploded["offsets_mm"]
        if set(old_off) != set(new_off) or any(max(abs(a - b) for a, b in zip(old_off[g], new_off[g])) > 1e-3 for g in new_off):
            return "exploded offsets changed"
        if exploded.get("direction") is not None:
            same = max(abs(a - b) for a, b in zip(normalised(old.get("direction", [0, 0, 0])), normalised(exploded["direction"]))) < 2e-3
            if not old.get("direction_from_settings") or not same:
                return "exploded direction changed"
        elif old.get("direction_from_settings"):
            return "exploded direction no longer set"
    if old.get("kind") == "joint":
        spec = joint_specs.get(old["id"])
        if spec is None:
            return "joint view no longer configured"
        if list(old.get("occurrence_ids", [])) != list(spec["occurrence_ids"]):
            return "joint occurrences changed"
        old_ctx = list(old.get("context_ids") or [old.get("context_assembly")])
        if old_ctx != list(spec["context"]):
            return "joint context changed"
        if old.get("context_style") != spec["context_style"]:
            return "joint context style changed"
        if spec.get("direction") is not None:
            # the record holds Blender's float32 unit vector rounded to 4 decimals: compare with a tolerance
            same = max(abs(a - b) for a, b in zip(normalised(old.get("direction", [0, 0, 0])), normalised(spec["direction"]))) < 2e-3
            if not old.get("direction_from_settings") or not same:
                return "joint direction changed"
        elif old.get("direction_from_settings"):
            return "joint direction no longer set"
    # the budget is a cost cap, not a look: an image that already has outlines is
    # still right under a lower cap (the enclosure overview keeps its 32-minute
    # Freestyle lines); only newly affordable outlines make a copy stale
    tris = old.get("visible_triangles")
    if tris is not None and old.get("lines") is not None:
        if lines_enabled and tris <= budget and not old["lines"]:
            return f"line art is now within the budget ({tris} <= {budget}) but the earlier view has none"
    return None
