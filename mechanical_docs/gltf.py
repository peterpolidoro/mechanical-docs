"""A minimal binary glTF (GLB) writer and reader for triangle meshes.

One mesh per file, one node, float32 positions and normals, uint32 indices.
Positions are written in glTF's convention (metres, +Y up). The conversion
from the scene frame (+Z up, declared units) is done here, once, by
`to_gltf_frame`; Blender's glTF importer converts back to +Z up on import,
so a mesh imported there lies in the scene frame scaled to metres.
"""
from __future__ import annotations

import json
import struct
from pathlib import Path

MAGIC = 0x46546C67
JSON_CHUNK = 0x4E4F534A
BIN_CHUNK = 0x004E4942


def to_gltf_frame(xyz_zup, scale):
    """Scene (+Z up) * scale -> glTF (+Y up): (x, y, z) -> (x, z, -y)."""
    x, y, z = xyz_zup
    return (x * scale, z * scale, -y * scale)


def from_gltf_frame(xyz_yup, scale):
    x, y, z = xyz_yup
    return (x * scale, -z * scale, y * scale)


def _pad(b, char=b"\x00"):
    return b + char * ((4 - len(b) % 4) % 4)


def write_glb(path, positions, normals, indices, name="mesh", extras=None):
    """positions/normals: lists of (x, y, z) in glTF frame; indices: flat list of ints, 3 per triangle."""
    if len(positions) != len(normals):
        raise ValueError("positions and normals differ in length")
    if len(indices) % 3:
        raise ValueError("indices must be a multiple of three")
    n = len(positions)
    if any(i < 0 or i >= n for i in indices):
        raise ValueError("index out of range")
    pos = struct.pack("<%df" % (3 * n), *[c for p in positions for c in p])
    nrm = struct.pack("<%df" % (3 * n), *[c for p in normals for c in p])
    idx = struct.pack("<%dI" % len(indices), *indices)
    pos, nrm, idx = _pad(pos), _pad(nrm), _pad(idx)
    mins = [min(p[i] for p in positions) for i in range(3)]
    maxs = [max(p[i] for p in positions) for i in range(3)]
    doc = {
        "asset": {"version": "2.0", "generator": "mechanical-docs gltf.py"},
        "scene": 0,
        "scenes": [{"nodes": [0]}],
        "nodes": [{"mesh": 0, "name": name}],
        "meshes": [{"name": name, "primitives": [{"attributes": {"POSITION": 0, "NORMAL": 1}, "indices": 2, "mode": 4}]}],
        "accessors": [
            {"bufferView": 0, "componentType": 5126, "count": n, "type": "VEC3", "min": mins, "max": maxs},
            {"bufferView": 1, "componentType": 5126, "count": n, "type": "VEC3"},
            {"bufferView": 2, "componentType": 5125, "count": len(indices), "type": "SCALAR"},
        ],
        "bufferViews": [
            {"buffer": 0, "byteOffset": 0, "byteLength": len(pos), "target": 34962},
            {"buffer": 0, "byteOffset": len(pos), "byteLength": len(nrm), "target": 34962},
            {"buffer": 0, "byteOffset": len(pos) + len(nrm), "byteLength": len(idx), "target": 34963},
        ],
        "buffers": [{"byteLength": len(pos) + len(nrm) + len(idx)}],
    }
    if extras:
        doc["asset"]["extras"] = extras
    js = _pad(json.dumps(doc, separators=(",", ":")).encode("utf-8"), b" ")
    binary = pos + nrm + idx
    total = 12 + 8 + len(js) + 8 + len(binary)
    out = struct.pack("<III", MAGIC, 2, total) + struct.pack("<II", len(js), JSON_CHUNK) + js + struct.pack("<II", len(binary), BIN_CHUNK) + binary
    Path(path).write_bytes(out)
    return total


def read_glb(path):
    """(json document, binary chunk bytes)."""
    data = Path(path).read_bytes()
    magic, version, length = struct.unpack_from("<III", data, 0)
    if magic != MAGIC or version != 2 or length != len(data):
        raise ValueError(f"{path}: not a GLB 2.0 file")
    off = 12
    doc = None; binary = b""
    while off < len(data):
        clen, ctype = struct.unpack_from("<II", data, off); off += 8
        chunk = data[off:off + clen]; off += clen
        if ctype == JSON_CHUNK:
            doc = json.loads(chunk.decode("utf-8"))
        elif ctype == BIN_CHUNK:
            binary = chunk
    if doc is None:
        raise ValueError(f"{path}: no JSON chunk")
    return doc, binary


def read_mesh(path):
    """positions, normals, indices of the single primitive, as Python lists."""
    doc, binary = read_glb(path)
    prim = doc["meshes"][0]["primitives"][0]

    def accessor(i):
        acc = doc["accessors"][i]; bv = doc["bufferViews"][acc["bufferView"]]
        start = bv.get("byteOffset", 0) + acc.get("byteOffset", 0)
        if acc["type"] == "VEC3":
            vals = struct.unpack_from("<%df" % (3 * acc["count"]), binary, start)
            return [tuple(vals[k:k + 3]) for k in range(0, len(vals), 3)]
        fmt = {5125: "I", 5123: "H"}[acc["componentType"]]
        return list(struct.unpack_from("<%d%s" % (acc["count"], fmt), binary, start))

    return accessor(prim["attributes"]["POSITION"]), accessor(prim["attributes"]["NORMAL"]), accessor(prim["indices"])


def signed_volume(positions, indices):
    """Divergence-theorem volume of a closed mesh: positive for outward winding."""
    v = 0.0
    for k in range(0, len(indices), 3):
        a, b, c = positions[indices[k]], positions[indices[k + 1]], positions[indices[k + 2]]
        v += (a[0] * (b[1] * c[2] - b[2] * c[1]) - a[1] * (b[0] * c[2] - b[2] * c[0]) + a[2] * (b[0] * c[1] - b[1] * c[0])) / 6.0
    return v


def bounds(positions):
    return [min(p[i] for p in positions) for i in range(3)], [max(p[i] for p in positions) for i in range(3)]
