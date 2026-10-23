"""A minimal binary glTF (GLB) writer and reader for triangle meshes.

`write_glb`: one mesh per file, one node (the CAD stage's per-part meshes).
`write_scene_glb`: several meshes shared by a node tree with matrices (the
viewer export: one mesh per part, one node per occurrence, one parent node
per subassembly instance), one flat material. Float32 positions and normals, uint32 indices.
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


FLAT_MATERIAL = {"name": "flat", "pbrMetallicRoughness": {"baseColorFactor": [0.74, 0.75, 0.77, 1.0], "metallicFactor": 0.0, "roughnessFactor": 0.65}, "doubleSided": True}


def frame_matrix_gltf(world_m):
    """A scene-frame (+Z up) rigid transform with its translation in metres as a
    glTF node matrix (column-major 16 floats, +Y up): C · M · C⁻¹ with C the
    axis change (x, y, z) -> (x, z, -y)."""
    C = [[1, 0, 0, 0], [0, 0, 1, 0], [0, -1, 0, 0], [0, 0, 0, 1]]
    Ci = [[1, 0, 0, 0], [0, 0, -1, 0], [0, 1, 0, 0], [0, 0, 0, 1]]
    mul = lambda a, b: [[sum(a[r][k] * b[k][c] for k in range(4)) for c in range(4)] for r in range(4)]  # noqa: E731
    M = mul(mul(C, world_m), Ci)
    return [M[r][c] for c in range(4) for r in range(4)]


def write_scene_glb(path, meshes, nodes, roots, extras=None, material=None):
    """meshes: [{"name", "positions", "normals", "indices"}] in glTF frame (metres);
    nodes: [{"name", "mesh": index or None, "matrix": 16 floats or None, "children": [node indices]}];
    roots: node indices of the scene. One material for every primitive. Returns the byte size."""
    binary = bytearray(); views = []; accessors = []; out_meshes = []

    def add_view(data, target):
        data = _pad(data)
        views.append({"buffer": 0, "byteOffset": len(binary), "byteLength": len(data), "target": target})
        binary.extend(data)
        return len(views) - 1

    for m in meshes:
        pos, nrm, idx = m["positions"], m["normals"], m["indices"]
        if len(pos) != len(nrm) or len(idx) % 3 or any(i < 0 or i >= len(pos) for i in idx):
            raise ValueError(f"mesh {m['name']!r}: positions/normals/indices inconsistent")
        vp = add_view(struct.pack("<%df" % (3 * len(pos)), *[c for p in pos for c in p]), 34962)
        vn = add_view(struct.pack("<%df" % (3 * len(nrm)), *[c for p in nrm for c in p]), 34962)
        vi = add_view(struct.pack("<%dI" % len(idx), *idx), 34963)
        mins = [min(p[i] for p in pos) for i in range(3)]; maxs = [max(p[i] for p in pos) for i in range(3)]
        a0 = len(accessors)
        accessors += [{"bufferView": vp, "componentType": 5126, "count": len(pos), "type": "VEC3", "min": mins, "max": maxs},
                      {"bufferView": vn, "componentType": 5126, "count": len(nrm), "type": "VEC3"},
                      {"bufferView": vi, "componentType": 5125, "count": len(idx), "type": "SCALAR"}]
        out_meshes.append({"name": m["name"], "primitives": [{"attributes": {"POSITION": a0, "NORMAL": a0 + 1}, "indices": a0 + 2, "mode": 4, "material": 0}]})
    out_nodes = []
    for n in nodes:
        node = {"name": n["name"]}
        if n.get("mesh") is not None:
            node["mesh"] = n["mesh"]
        if n.get("matrix") is not None:
            node["matrix"] = [float(v) for v in n["matrix"]]
        if n.get("children"):
            node["children"] = list(n["children"])
        out_nodes.append(node)
    doc = {"asset": {"version": "2.0", "generator": "mechanical-docs gltf.py"}, "scene": 0, "scenes": [{"nodes": list(roots)}],
           "nodes": out_nodes, "meshes": out_meshes, "materials": [material or FLAT_MATERIAL],
           "accessors": accessors, "bufferViews": views, "buffers": [{"byteLength": len(binary)}]}
    if extras:
        doc["asset"]["extras"] = extras
    js = _pad(json.dumps(doc, separators=(",", ":")).encode("utf-8"), b" ")
    total = 12 + 8 + len(js) + 8 + len(binary)
    out = struct.pack("<III", MAGIC, 2, total) + struct.pack("<II", len(js), JSON_CHUNK) + js + struct.pack("<II", len(binary), BIN_CHUNK) + bytes(binary)
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
