"""Derive each step's cumulative state from the ordered additions.

The canonical scene is the final arrangement; a step never changes a
transform. This module only answers "which occurrences are installed before,
added by and installed after each step", and checks that prerequisites are
transitively satisfied by the order. Approach offsets are illustration hints
carried through untouched.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from . import transforms as T
from .manifest import Instructions, Scene, Step


@dataclass
class StepState:
    index: int                    # 1-based step number
    step: Step
    before: list = field(default_factory=list)    # occurrence ids installed before this step
    added: list = field(default_factory=list)     # occurrence ids this step installs
    after: list = field(default_factory=list)     # before + added
    hidden: list = field(default_factory=list)    # occurrences of later steps
    parts_needed: dict = field(default_factory=dict)   # part id -> count added in this step


class ProcedureError(ValueError):
    pass


def derive_states(instructions: Instructions, scene: Scene):
    """One StepState per step, in order. Raises ProcedureError on a prerequisite
    the order does not satisfy or a repeated installation (the loader rejects
    these too; this guards callers that build Instructions themselves)."""
    installed = []
    done = set()
    states = []
    all_ids = list(scene.occurrences)
    for i, step in enumerate(instructions.steps, 1):
        missing = [r for r in step.requires if r not in done]
        if missing:
            raise ProcedureError(f"step {step.id!r} requires {missing} which have not been completed in order")
        dup = [o for o in step.add if o in installed]
        if dup:
            raise ProcedureError(f"step {step.id!r} installs {dup} again")
        unknown = [o for o in step.add if o not in scene.occurrences]
        if unknown:
            raise ProcedureError(f"step {step.id!r} adds unknown occurrence(s) {unknown}")
        before = list(installed)
        installed = installed + list(step.add)
        done.add(step.id)
        needed = {}
        for oid in step.add:
            pid = scene.occurrences[oid].part_id
            needed[pid] = needed.get(pid, 0) + 1
        st = StepState(i, step, before, list(step.add), list(installed), [o for o in all_ids if o not in installed], needed)
        states.append(st)
    left = [o for o in all_ids if o not in installed]
    if left:
        raise ProcedureError(f"occurrence(s) never installed: {left}")
    return states


def approach_pose(scene: Scene, state: StepState):
    """(occurrence id, start world transform, end world transform) for the
    step's approach hint, or None. The start pose is the canonical world pose
    translated by the hint's start offset in scene units; the end pose is the
    canonical pose itself (end_offset must be zero)."""
    ap = state.step.approach
    if ap is None:
        return None
    occ = scene.occurrences[ap.occurrence_id]
    start = T.multiply(T.translate(*ap.start_offset), occ.world)
    return ap.occurrence_id, start, occ.world
