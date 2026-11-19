"""Moving pictures, without Blender: where a camera stands at each frame, and how far a part has come.

Three sequences are drawn by motion.py from what is worked out here:

- a **turntable**: the camera goes once round the vertical axis through the
  middle of what is drawn, at one height, and the picture's scale is the one
  that holds everything at every frame, so that it does not breathe;
- an **exploded sequence**: the top-level groups of a scene move apart, from
  where they are installed to the offsets of the exploded view (explode.py),
  and may come back;
- a **steps sequence**: in the order of a project's instructions, what each
  step adds arrives at its seat while what earlier steps added stays.

A frame is one picture. A movement of `move` frames starts slowly and ends
slowly (`smooth`). Everything here is in the scene's +Z-up frame; angles are
radians unless a name says degrees.
"""
from __future__ import annotations

import math

from . import explode
from . import transforms as T

# where the view `iso` stands (views.py): from +X and -Y, 0.8 above the diagonal
ISO_AZIMUTH_DEG = -45.0
ISO_ELEVATION_DEG = math.degrees(math.atan2(0.8, math.sqrt(2.0)))
UP = (0.0, 0.0, 1.0)
SOURCES = ("approach", "exploded", "lift")


class TimelineError(ValueError):
    pass


def smooth(t):
    """0 to 1 with no jerk at either end: how far a movement has come when the fraction `t` of its time has passed."""
    t = min(1.0, max(0.0, float(t)))
    return t * t * (3.0 - 2.0 * t)


def _count(value, name, least=1):
    if isinstance(value, bool) or not isinstance(value, int) or value < least:
        raise TimelineError(f"{name}: expected a whole number of at least {least}, got {value!r}")
    return value


# ------------------------------------------------------------------ turntable

def turntable(frames, elevation_deg=ISO_ELEVATION_DEG, start_deg=ISO_AZIMUTH_DEG, turns=1.0):
    """[(the angle turned since the first frame, where the camera stands)] for one frame after another.

    The camera stands in a direction from the middle of what is drawn: at
    `start_deg` round the vertical axis from +X towards +Y, `elevation_deg`
    above the horizontal, and goes round counter-clockwise as seen from above.
    The last frame is one step short of the first, so that the sequence closes
    when it is played again.
    """
    _count(frames, "frames")
    if not -89.0 <= elevation_deg <= 89.0:
        raise TimelineError(f"elevation: expected degrees from -89 to 89, got {elevation_deg!r}: straight above and below, a turn is a spin of the picture")
    el = math.radians(elevation_deg)
    out = []
    for i in range(frames):
        turned = 2.0 * math.pi * turns * i / frames
        az = math.radians(start_deg) + turned
        out.append((turned, (math.cos(el) * math.cos(az), math.cos(el) * math.sin(az), math.sin(el))))
    return out


def camera_axes(stands, up=UP):
    """(to the right, upwards) in the picture of a camera that stands in the direction `stands` and looks back
    at the middle, with `up` upwards: the axes render.py's `aim` gives its camera."""
    n = math.sqrt(sum(c * c for c in stands))
    if n < 1e-12:
        raise TimelineError("a camera has to stand somewhere: the direction is zero")
    f = [-c / n for c in stands]                                     # the way it looks
    r = [f[1] * up[2] - f[2] * up[1], f[2] * up[0] - f[0] * up[2], f[0] * up[1] - f[1] * up[0]]
    rn = math.sqrt(sum(c * c for c in r))
    if rn < 1e-9:
        raise TimelineError("the camera looks along its own up axis")
    r = [c / rn for c in r]
    u = [r[1] * f[2] - r[2] * f[1], r[2] * f[0] - r[0] * f[2], r[0] * f[1] - r[1] * f[0]]
    return r, u


def ortho_scale(points, target, cameras, width, height, fill):
    """The orthographic scale at which every point is inside the picture for every camera, the middle of the
    picture being `target`, with `fill` of the picture used at most.

    `cameras` is [(stands, up)]; `points` and `target` are in one unit, and so is the result. It is Blender's
    `ortho_scale`: the length the longer side of the picture spans.
    """
    if not points or not cameras:
        raise TimelineError("nothing to frame")
    if not 0.0 < fill <= 1.0:
        raise TimelineError(f"fill: expected a fraction of the picture above 0 and at most 1, got {fill!r}")
    need = 0.0
    for stands, up in cameras:
        r, u = camera_axes(stands, up)
        half_w = max(abs(sum((p[i] - target[i]) * r[i] for i in range(3))) for p in points)
        half_h = max(abs(sum((p[i] - target[i]) * u[i] for i in range(3))) for p in points)
        if width >= height:
            need = max(need, 2.0 * half_w, 2.0 * half_h * width / height)
        else:
            need = max(need, 2.0 * half_h, 2.0 * half_w * height / width)
    return need / fill


# ------------------------------------------------------------------ exploded

def exploded_fractions(move, hold, back=False):
    """How far apart the groups are at each frame, from 0 (installed) to 1 (the exploded view's offsets).

    `hold` frames at rest, `move` frames apart, `hold` frames at rest; with `back`, the same movement the other
    way, ending one frame short of the first so that the sequence closes when it is played again.
    """
    _count(move, "frames")
    _count(hold, "hold", 0)
    out = [0.0] * hold + [smooth(k / move) for k in range(1, move + 1)] + [1.0] * hold
    if back:
        out += [smooth(k / move) for k in range(move - 1, 0, -1)]
    return out


# --------------------------------------------------------------------- steps

def step_frames(steps, move, hold):
    """[(the step's place in the order from 0, how far its additions have come)] for one frame after another.

    Each step takes `move` frames, in the first of which its additions are where they start from, and then
    `hold` frames with them seated.
    """
    _count(steps, "steps")
    _count(move, "frames")
    _count(hold, "hold", 1)                      # a step's additions are seen seated at least once
    out = []
    for i in range(steps):
        out += [(i, smooth(k / move)) for k in range(move)] + [(i, 1.0)] * hold
    return out


def step_starts(scene, states, exploded_offsets_mm, lift_mm):
    """Where each occurrence starts from before its step seats it: {occurrence id: (offset in mm, source)}.

    The offset is from the installed pose, in the scene's frame. Its source is, in this order: `approach`, the
    start offset of the step's approach hint, when the hint is for this occurrence; `exploded`, the offset of
    its top-level group in the exploded view, when that group moves at all; `lift`, straight up by `lift_mm`.
    None of them is an insertion path: they are where a picture lets a part come from.
    """
    to_mm = T.unit_factor(scene.units, "mm")
    out = {}
    for st in states:
        ap = st.step.approach
        for oid in st.added:
            if ap is not None and ap.occurrence_id == oid:
                out[oid] = ([float(v) * to_mm for v in ap.start_offset], "approach")
                continue
            off = exploded_offsets_mm.get(explode.group_of(scene, oid)) if exploded_offsets_mm else None
            if off is not None and any(abs(v) > 1e-9 for v in off):
                out[oid] = ([float(v) for v in off], "exploded")
            else:
                out[oid] = ([0.0, 0.0, float(lift_mm)], "lift")
    return out


def duration_s(frames, fps):
    return frames / float(fps)
