import math

import pytest

from mechanical_docs import gltf


def unit_cube():
    # +Z-up mm cube from (0,0,0) to (10,10,10), 12 triangles, outward winding
    v = [(x, y, z) for z in (0, 10) for y in (0, 10) for x in (0, 10)]
    # indices into v: bit0 = x, bit1 = y, bit2 = z
    faces = [
        (0, 2, 3, 1),  # bottom z=0 (normal -z)
        (4, 5, 7, 6),  # top z=10 (+z)
        (0, 1, 5, 4),  # y=0 (-y)
        (2, 6, 7, 3),  # y=10 (+y)
        (0, 4, 6, 2),  # x=0 (-x)
        (1, 3, 7, 5),  # x=10 (+x)
    ]
    idx = []
    for a, b, c, d in faces:
        idx += [a, b, c, a, c, d]
    return v, idx


def test_signed_volume_positive_for_outward_cube():
    v, idx = unit_cube()
    assert gltf.signed_volume(v, idx) == pytest.approx(1000.0)
    flipped = [idx[k + j] for k in range(0, len(idx), 3) for j in (0, 2, 1)]
    assert gltf.signed_volume(v, flipped) == pytest.approx(-1000.0)


def test_glb_round_trip_and_frame_conversion(tmp_path):
    v, idx = unit_cube()
    pos = [gltf.to_gltf_frame(p, 0.001) for p in v]
    nrm = [(0.0, 1.0, 0.0)] * len(pos)
    path = tmp_path / "cube.glb"
    size = gltf.write_glb(path, pos, nrm, idx, name="cube", extras={"source_units": "mm"})
    assert path.stat().st_size == size
    doc, binary = gltf.read_glb(path)
    assert doc["asset"]["extras"] == {"source_units": "mm"}
    assert doc["accessors"][0]["min"] == pytest.approx([0, 0, -0.01])
    assert doc["accessors"][0]["max"] == pytest.approx([0.01, 0.01, 0])
    p2, n2, i2 = gltf.read_mesh(path)
    assert i2 == idx and len(p2) == len(v)
    back = [gltf.from_gltf_frame(p, 1000.0) for p in p2]
    for a, b in zip(back, v):
        assert a == pytest.approx(b, abs=1e-6)
    # frame conversion keeps handedness: volume stays positive
    assert gltf.signed_volume(p2, i2) == pytest.approx(1e-6, rel=1e-6)


def test_frame_conversion_is_rotation_not_reflection():
    x, y, z = gltf.to_gltf_frame((1, 0, 0), 1), gltf.to_gltf_frame((0, 1, 0), 1), gltf.to_gltf_frame((0, 0, 1), 1)
    # x × y must equal z under the mapping
    cx = (x[1] * y[2] - x[2] * y[1], x[2] * y[0] - x[0] * y[2], x[0] * y[1] - x[1] * y[0])
    assert cx == pytest.approx(z)


def test_writer_rejects_bad_input(tmp_path):
    with pytest.raises(ValueError):
        gltf.write_glb(tmp_path / "a.glb", [(0, 0, 0)], [], [0, 0, 0])
    with pytest.raises(ValueError):
        gltf.write_glb(tmp_path / "a.glb", [(0, 0, 0)] * 3, [(0, 0, 1)] * 3, [0, 1, 5])
    with pytest.raises(ValueError):
        gltf.write_glb(tmp_path / "a.glb", [(0, 0, 0)] * 3, [(0, 0, 1)] * 3, [0, 1])
