import math

import pytest

from mechanical_docs import transforms as T


def test_identity_is_rigid():
    assert T.check_matrix(T.IDENTITY) == T.IDENTITY


def test_rotation_and_translation_compose():
    m = T.multiply(T.translate(10, 0, 0), T.rotation_z(90))
    p = T.apply(m, [1, 0, 0])
    assert p == pytest.approx([10, 1, 0])


def test_nested_translation_matches_fixture_expectation():
    parent = T.translate(10)
    pins = [T.translate(-35), T.translate(15)]
    assert [T.translation(T.multiply(parent, c))[0] for c in pins] == [-25, 15 + 10]


@pytest.mark.parametrize("bad, msg", [
    ([[1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 1, 0]], "4x4"),
    ([[1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 1, 0], [0, 0, 1, 1]], "last row"),
    ([[2, 0, 0, 0], [0, 1, 0, 0], [0, 0, 1, 0], [0, 0, 0, 1]], "orthonormal"),
    ([[1, 0.5, 0, 0], [0, 1, 0, 0], [0, 0, 1, 0], [0, 0, 0, 1]], "orthonormal"),
    ([[-1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 1, 0], [0, 0, 0, 1]], "reflection"),
    ([[1, 0, 0, "x"], [0, 1, 0, 0], [0, 0, 1, 0], [0, 0, 0, 1]], "non-numeric"),
    ([[1, 0, 0, math.inf], [0, 1, 0, 0], [0, 0, 1, 0], [0, 0, 0, 1]], "non-finite"),
])
def test_rejects_non_rigid(bad, msg):
    with pytest.raises(T.TransformError, match=msg):
        T.check_matrix(bad)


def test_unit_factor():
    assert T.unit_factor("mm", "m") == pytest.approx(0.001)
    assert T.unit_factor("in", "mm") == pytest.approx(25.4)
    with pytest.raises(T.TransformError):
        T.unit_factor("furlong", "mm")
