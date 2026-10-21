"""4x4 rigid transforms as nested lists: row-major, applied to column vectors.

    p_parent = T_parent_from_child @ [x, y, z, 1]^T

The draft-1 contract allows rigid rotations (determinant +1, orthonormal) and
translations only. A reflection, scale or shear is rejected rather than
silently applied: a mirrored part must be an explicit geometry variant.
"""
from __future__ import annotations

import math

IDENTITY = [[1.0, 0.0, 0.0, 0.0], [0.0, 1.0, 0.0, 0.0], [0.0, 0.0, 1.0, 0.0], [0.0, 0.0, 0.0, 1.0]]


class TransformError(ValueError):
    pass


def check_matrix(m, where="transform", tol=1e-6):
    """Return the matrix as floats if it is a rigid 4x4; raise TransformError otherwise."""
    if not isinstance(m, list) or len(m) != 4 or any(not isinstance(r, list) or len(r) != 4 for r in m):
        raise TransformError(f"{where}: expected a 4x4 nested list")
    try:
        out = [[float(v) for v in r] for r in m]
    except (TypeError, ValueError):
        raise TransformError(f"{where}: non-numeric entry") from None
    for r in out:
        for v in r:
            if not math.isfinite(v):
                raise TransformError(f"{where}: non-finite entry")
    if any(abs(a - b) > tol for a, b in zip(out[3], [0.0, 0.0, 0.0, 1.0])):
        raise TransformError(f"{where}: last row must be [0, 0, 0, 1], got {out[3]}")
    R = [r[:3] for r in out[:3]]
    # orthonormal columns
    for i in range(3):
        for j in range(3):
            dot = sum(R[k][i] * R[k][j] for k in range(3))
            want = 1.0 if i == j else 0.0
            if abs(dot - want) > tol * 10:
                raise TransformError(f"{where}: rotation block is not orthonormal (scale or shear present)")
    if det3(R) < 0:
        raise TransformError(f"{where}: rotation determinant is negative (a reflection); declare a mirrored geometry variant instead")
    return out


def det3(R):
    return (R[0][0] * (R[1][1] * R[2][2] - R[1][2] * R[2][1])
            - R[0][1] * (R[1][0] * R[2][2] - R[1][2] * R[2][0])
            + R[0][2] * (R[1][0] * R[2][1] - R[1][1] * R[2][0]))


def multiply(a, b):
    """a @ b for 4x4 nested lists."""
    return [[sum(a[r][k] * b[k][c] for k in range(4)) for c in range(4)] for r in range(4)]


def apply(m, p):
    """m @ [x, y, z, 1] -> [x', y', z']."""
    x, y, z = p
    return [m[r][0] * x + m[r][1] * y + m[r][2] * z + m[r][3] for r in range(3)]


def translation(m):
    return [m[0][3], m[1][3], m[2][3]]


def translate(x=0.0, y=0.0, z=0.0):
    return [[1.0, 0.0, 0.0, float(x)], [0.0, 1.0, 0.0, float(y)], [0.0, 0.0, 1.0, float(z)], [0.0, 0.0, 0.0, 1.0]]


def scaled_translation(m, factor):
    """The same rotation with the translation multiplied by `factor` (a unit change)."""
    out = [list(r) for r in m]
    for r in range(3):
        out[r][3] *= factor
    return out


def rotation_z(deg):
    c, s = math.cos(math.radians(deg)), math.sin(math.radians(deg))
    return [[c, -s, 0.0, 0.0], [s, c, 0.0, 0.0], [0.0, 0.0, 1.0, 0.0], [0.0, 0.0, 0.0, 1.0]]


def close(a, b, tol=1e-9):
    return all(abs(x - y) <= tol for ra, rb in zip(a, b) for x, y in zip(ra, rb))


UNIT_TO_MM = {"mm": 1.0, "cm": 10.0, "m": 1000.0, "in": 25.4}


def unit_factor(src, dst):
    """Multiply a length in `src` by this to get `dst`."""
    try:
        return UNIT_TO_MM[src] / UNIT_TO_MM[dst]
    except KeyError:
        raise TransformError(f"unsupported unit {src!r} or {dst!r}; known: {sorted(UNIT_TO_MM)}") from None
