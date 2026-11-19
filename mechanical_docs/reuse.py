"""Which views an earlier render receipt can still stand in for.

`render.py --reuse` copies a view from an earlier receipt made from the same
scene, assets, meshes, engine and quality (the instructions may differ: the
views that follow them are then stale). Several changes
are detected per view so a copy is never silently stale: a joint close-up
whose specification (occurrences, context, context style, explicit direction)
differs from the record, an exploded view whose offsets or explicit direction
changed, the overview and the steps when the instructions changed, a step
whose additions or installed-before set changed, any view whose outlines would
now be drawn otherwise (below), and any view that shows a part
in a look other than the one it was drawn with.

Outlines. A view's record says whether it has outlines (`lines`) and what
drew them (`outliner`: "freestyle" or "line-art"; a record from before there
was a choice has none, and its outlines are Freestyle's). A view drawn
without outlines is stale when the current settings would outline it: with
Freestyle because the budget now allows it, with Line Art always. A lower
budget never discards an image Freestyle outlined: the budget caps cost, it is
not a look, and under "mixed" Freestyle is what is wanted wherever there is a
picture of it. The two outliners draw different lines, so a view outlined by
the one that the current settings would not use for it is stale: Freestyle's
under "line-art", Line Art's under "freestyle", and under "mixed" Line Art's
where Freestyle is within its budget.

Looks. A receipt records for every part the look it was drawn with
(looks.py: a palette entry named in render.json, a finish of finishes.json,
or the default, with its numbers). A view is stale when a part it shows in
its own look has another look now: a thumbnail or an end view shows its part;
the overview, the exploded view, a subassembly view and a still show every
visible occurrence's part; a joint close-up shows its subject occurrences
(the context is flat grey); a step shows what it adds (what was installed
before is ghosted). An earlier receipt without that record cannot tell what
its parts were drawn with. Its views are taken as they always were, except
those that show a part whose look now comes from finishes.json: that file did
not exist for it, so they are rendered again.

Other appearance changes (group direction, thumbnail rules, the studio,
--no-lines) are not detected: name those views with --views.
"""
from __future__ import annotations

from mechanical_docs.render_settings import outliner_for


def normalised(v):
    n = sum(x * x for x in v) ** 0.5
    return [round(x / n, 4) for x in v] if n > 1e-12 else [0.0, 0.0, 0.0]


def shown_in_look(old, part_of):
    """The parts a view shows in their own looks, sorted. `old` is the view's
    record and `part_of` maps an occurrence id to its part id."""
    kind = old.get("kind")
    if kind in ("part-thumbnail", "part-end"):
        return [old["part_id"]] if old.get("part_id") is not None else []
    if kind in ("step", "step-result"):
        occurrences = old.get("highlighted") or []
    elif kind == "joint":
        occurrences = old.get("occurrence_ids") or []
    else:                                   # overview, exploded, group, still: everything visible is in its look
        occurrences = old.get("visible") or []
    return sorted({part_of[o] for o in occurrences if o in part_of})


def look_reason(old, looks):
    """Why a view's looks make it stale, or None. `looks` is (the earlier
    receipt's part looks or None when it recorded none, the current part
    looks, occurrence id -> part id)."""
    earlier, current, part_of = looks
    for pid in shown_in_look(old, part_of):
        now = current.get(pid)
        if earlier is None:
            if now is not None and now.get("source") == "finishes.json":
                return f"the earlier receipt records no looks and {pid} now takes its look from finishes.json"
        elif earlier.get(pid) != now:
            return f"the look of {pid} changed"
    return None


def outline_reason(old, lines_enabled, budget, outliner="freestyle"):
    """Why a view's outlines make it stale, or None. Nothing is said of a view
    whose record does not hold its triangle count and whether it has lines,
    nor when this run draws no lines at all (--no-lines is not a look that is
    detected)."""
    tris = old.get("visible_triangles")
    if tris is None or old.get("lines") is None or not lines_enabled:
        return None
    was = (old.get("outliner") or "freestyle") if old["lines"] else None
    now = outliner_for(True, outliner, tris, budget)
    if was == now:
        return None
    if was is None:
        if now == "freestyle":
            return f"line art is now within the budget ({tris} <= {budget}) but the earlier view has none"
        return "Line Art now draws this view's outlines and the earlier view has none"
    if was == "freestyle":
        # a lower cap keeps what Freestyle drew, and so does "mixed"; only "line-art" asks for other lines
        return "the earlier view's outlines are Freestyle's and Line Art draws them now" if outliner == "line-art" else None
    if now == "freestyle":
        return "the earlier view's outlines are Line Art's and Freestyle draws them now"
    return "the earlier view's outlines are Line Art's, which this run does not use"


def stale_reason(old, joint_specs, lines_enabled, budget, exploded=None, instructions_changed=False, step_states=None, looks=None,
                 outliner="freestyle"):
    """None when `old` (a view record from an earlier receipt) can be reused
    under the current settings, else a short reason.

    joint_specs: view id -> resolved joint spec (occurrence_ids, context,
    context_style, direction or None). lines_enabled/budget: the current run's
    line-art switch and visible-triangle budget. exploded: the resolved
    exploded-view plan (offsets_mm, direction) or None when none is drawn.
    instructions_changed: the instructions file differs from the old receipt's
    (the overview camera and every step follow it). step_states: view id ->
    (added, before) of the current derivation, so a step whose cumulative state
    changed (a build scope deferring an earlier step) is rendered again.
    looks: see look_reason; None leaves looks out of the judgement. outliner:
    the setting `lines.outliner` of the current run."""
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
    if looks is not None:
        reason = look_reason(old, looks)
        if reason is not None:
            return reason
    # the budget is a cost cap, not a look: an image that already has outlines is
    # still right under a lower cap (the enclosure overview keeps its 32-minute
    # Freestyle lines); newly affordable outlines make a copy stale, and so do
    # outlines of the outliner that is not the one in use
    return outline_reason(old, lines_enabled, budget, outliner)
