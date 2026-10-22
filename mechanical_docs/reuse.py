"""Which views an earlier render receipt can still stand in for.

`render.py --reuse` copies a view from an earlier receipt made from the same
scene, assets, instructions, meshes, engine and quality. Two settings changes
are detected per view so a copy is never silently stale: a joint close-up
whose specification (occurrences, context, context style, explicit direction)
differs from the record, and any view drawn without outlines that the current
line budget would now outline (a lower budget never discards an outlined
image: the budget caps cost, it is not a look). Other appearance changes
(looks, group direction, thumbnail rules, --no-lines) are not detected: name
those views with --views.
"""
from __future__ import annotations


def normalised(v):
    n = sum(x * x for x in v) ** 0.5
    return [round(x / n, 4) for x in v] if n > 1e-12 else [0.0, 0.0, 0.0]


def stale_reason(old, joint_specs, lines_enabled, budget):
    """None when `old` (a view record from an earlier receipt) can be reused
    under the current settings, else a short reason.

    joint_specs: view id -> resolved joint spec (occurrence_ids, context,
    context_style, direction or None). lines_enabled/budget: the current run's
    line-art switch and visible-triangle budget."""
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
