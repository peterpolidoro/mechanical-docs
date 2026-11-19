"""What each part is drawn with: its look, where the look came from, and the numbers of it.

A part's look is, in this order:

1. the palette entry `render.json` names for it under `looks` (the project's
   illustration settings say so explicitly, and that holds);
2. else its finish in `finishes.json`, when the file gives it one;
3. else the settings' `default_look`.

A palette entry's `base` is a linear colour, as Blender's shader takes it. A
finish's `color` is an sRGB colour as a colour picker gives it, `#rrggbb`, and
is converted here. Every resolved look has the same form, so the renderer
builds one material from it and a receipt can record it:

    {"look": "clear-acrylic", "source": "finishes.json",
     "base": [0.5210, 0.7682, 0.8550], "metallic": 0.0, "roughness": 0.15, "opacity": 0.35}

`source` is `render.json`, `finishes.json` or `default`. Two receipts that
record the same look for a part drew it the same way; reuse.py compares them.
Nothing here needs Blender.
"""
from __future__ import annotations

SOURCES = ("render.json", "finishes.json", "default")
DIGITS = 6      # recorded numbers are rounded, so that a record read back equals the one computed again


class LookError(ValueError):
    pass


def srgb_to_linear(c):
    """One sRGB channel, 0 to 1, as the linear value a shader works with."""
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def hex_to_srgb(color):
    """`#rrggbb` as three numbers from 0 to 1."""
    if not (isinstance(color, str) and len(color) == 7 and color[0] == "#"):
        raise LookError(f"expected a colour as #rrggbb, got {color!r}")
    try:
        return [int(color[i:i + 2], 16) / 255.0 for i in (1, 3, 5)]
    except ValueError:
        raise LookError(f"expected a colour as #rrggbb, got {color!r}") from None


def hex_to_linear(color):
    return [srgb_to_linear(c) for c in hex_to_srgb(color)]


def _numbers(base, metallic, roughness, opacity):
    return {"base": [round(float(c), DIGITS) for c in base], "metallic": round(float(metallic), DIGITS),
            "roughness": round(float(roughness), DIGITS), "opacity": round(float(opacity), DIGITS)}


def from_palette(name, spec, source):
    look = {"look": name, "source": source, **_numbers(spec["base"], spec.get("metallic", 0.0), spec.get("roughness", 0.5), 1.0)}
    if "coat" in spec:
        look["coat"] = round(float(spec["coat"]), DIGITS)
        look["coat_roughness"] = round(float(spec.get("coat_roughness", 0.1)), DIGITS)
    return look


def from_finish(name, finish):
    return {"look": name, "source": "finishes.json",
            **_numbers(hex_to_linear(finish["color"]), finish["metallic"], finish["roughness"], finish["opacity"])}


def resolve(part_ids, settings, finishes=None):
    """part id -> its resolved look, for every part id given.

    `settings` are the illustration settings (render_settings.load_settings);
    `finishes` is the project's loaded finishes.json (manifest.Finishes) or
    None. An unknown palette name is an error, as it always was.
    """
    palette = settings["palette"]
    out = {}
    for pid in part_ids:
        named = settings["looks"].get(pid)
        finish = finishes.of(pid) if finishes is not None and named is None else None
        if finish is not None:
            out[pid] = from_finish(*finish)
            continue
        name = named if named is not None else settings["default_look"]
        if name not in palette:
            raise LookError(f"render.json: unknown look {name!r} for part {pid!r}; palette has {sorted(palette)}")
        out[pid] = from_palette(name, palette[name], "render.json" if named is not None else "default")
    return out


def material_key(look):
    """What tells two materials apart: a palette entry and a finish may share a name."""
    return ("finish:" if look["source"] == "finishes.json" else "look:") + look["look"]


def chosen(resolved):
    """Whether any part's look was chosen for it, in render.json or in finishes.json, and is not just the default."""
    return any(look["source"] != "default" for look in resolved.values())


def gltf_material(look):
    """A resolved look as a glTF material: the colour as light adds up with the opacity as its alpha, how
    metallic and how rough, named after the look, blended where it lets through what lies behind. A palette
    entry's coat is not carried: glTF has it only as an extension."""
    material = {"name": look["look"],
                "pbrMetallicRoughness": {"baseColorFactor": [*look["base"], look["opacity"]], "metallicFactor": look["metallic"],
                                         "roughnessFactor": look["roughness"]},
                "doubleSided": True, "extras": {"source": look["source"]}}
    if look["opacity"] < 1.0:
        material["alphaMode"] = "BLEND"
    return material


def viewer_materials(resolved, flat):
    """The materials of a viewer model and which of them each part has: ([materials], {part id: index}).

    `flat` is the viewer's own material and always the first. A part whose look was chosen for it, in
    render.json or in finishes.json, gets that look as a material of its own, one for every look whatever the
    number of parts that have it; a part in the default look keeps the flat one, as every part has it in a
    project that chose nothing.
    """
    materials, index, of = [flat], {}, {}
    for pid, look in resolved.items():
        if look["source"] == "default":
            of[pid] = 0
            continue
        key = material_key(look)
        if key not in index:
            index[key] = len(materials)
            materials.append(gltf_material(look))
        of[pid] = index[key]
    return materials, of
