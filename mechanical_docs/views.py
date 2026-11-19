"""Named camera positions for a picture outside a manual.

The names are the ones `mechanical-cad`'s tools/picture.py takes, so that the
same word gives the same camera in both tools. They are in the scene's +Z-up
frame, as a direction from the middle of what is drawn to where the camera
stands:

    iso         from +X, -Y and above          iso-back    from -X, +Y and above
    below       from +X, -Y and below          below-back  from -X, +Y and below
    +x -x +y -y +z -z                          from that side, looking along the axis

Z points up in the picture, except straight along Z, where the picture is a
plan: from above X runs to the right and Y upwards, and from below Y is still
upwards. Nothing here needs Blender.
"""
from __future__ import annotations

CORNERS = {"iso": (1.0, -1.0, 0.8), "iso-back": (-1.0, 1.0, 0.8), "below": (1.0, -1.0, -0.8), "below-back": (-1.0, 1.0, -0.8)}
AXES = {"+x": (1.0, 0.0, 0.0), "-x": (-1.0, 0.0, 0.0), "+y": (0.0, 1.0, 0.0), "-y": (0.0, -1.0, 0.0),
        "+z": (0.0, 0.0, 1.0), "-z": (0.0, 0.0, -1.0)}
NAMES = tuple(CORNERS) + tuple(AXES)
Z_UP = (0.0, 0.0, 1.0)
Y_UP = (0.0, 1.0, 0.0)


class ViewError(ValueError):
    pass


def stands(view):
    """(where the camera stands, as a direction from the middle; which way is up in the picture)."""
    key = str(view).lower()
    if key in CORNERS:
        return CORNERS[key], Z_UP
    if key in AXES:
        return AXES[key], (Y_UP if key[1] == "z" else Z_UP)
    raise ViewError(f"unknown view {view!r}; known: {', '.join(NAMES)}")


def direction(text):
    """`X,Y,Z` as where the camera stands; up is +Z, or +Y when it stands straight above or below."""
    try:
        d = tuple(float(v) for v in str(text).split(","))
    except ValueError:
        d = ()
    if len(d) != 3 or not any(d):
        raise ViewError(f"--direction: expected three numbers X,Y,Z that are not all zero, got {text!r}")
    return d, (Y_UP if d[0] == 0.0 and d[1] == 0.0 else Z_UP)


def file_name(view):
    """A view's name in a file name: `+x` is plus-x and `-z` is minus-z."""
    view = str(view).lower()
    return {"+": "plus-", "-": "minus-"}[view[0]] + view[1:] if view[:1] in ("+", "-") else view
