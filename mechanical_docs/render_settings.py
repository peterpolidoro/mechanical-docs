"""Illustration settings: defaults here, overridden by a project's render.json.

Nothing in these settings may change geometry, identity, quantity or order;
they choose looks, image sizes, sampling, outline and arrow styling. The look
palette is adapted from mouse-joysticks-mech atlas/scene.yaml (commit 22aa7544).
"""
from __future__ import annotations

import json
from pathlib import Path

PALETTE = {
    "aluminium": {"base": [0.62, 0.63, 0.65], "metallic": 0.8, "roughness": 0.55},
    "stainless": {"base": [0.50, 0.50, 0.52], "metallic": 1.0, "roughness": 0.28},
    "nickel": {"base": [0.58, 0.55, 0.50], "metallic": 1.0, "roughness": 0.28},
    "black-anodized": {"base": [0.035, 0.035, 0.040], "metallic": 0.6, "roughness": 0.42},
    "black-plastic": {"base": [0.020, 0.020, 0.022], "metallic": 0.0, "roughness": 0.48},
    "grey-plastic": {"base": [0.30, 0.31, 0.33], "metallic": 0.0, "roughness": 0.55},
    "blue-anodized": {"base": [0.05, 0.16, 0.55], "metallic": 0.3, "roughness": 0.40},
    "brass": {"base": [0.78, 0.56, 0.20], "metallic": 1.0, "roughness": 0.35},
    "label-white": {"base": [0.88, 0.88, 0.86], "metallic": 0.0, "roughness": 0.75},
    "beige-plastic": {"base": [0.62, 0.55, 0.42], "metallic": 0.0, "roughness": 0.55},
    "red-plastic": {"base": [0.60, 0.06, 0.05], "metallic": 0.0, "roughness": 0.45},
    "yellow-plastic": {"base": [0.80, 0.60, 0.05], "metallic": 0.0, "roughness": 0.45},
}

DEFAULTS = {
    "engine": "BLENDER_EEVEE_NEXT",
    "samples": 64,
    "preview_samples": 8,
    "long_side_px": 1600,
    "preview_long_side_px": 480,
    "thumbnail_px": 600,
    "aspect": [4, 3],
    "fill": 0.86,
    "thumbnail_fill": 0.78,
    "thumbnail_direction": [1.0, -1.2, 0.9],
    "film_transparent": True,
    "view_transform": "Standard",
    "look": "None",
    "exposure": 0.0,
    "world": {"color": [0.85, 0.86, 0.88], "strength": 0.9},
    "studio": {
        "key": {"direction": [-1.0, -0.7, 1.3], "distance": 3.0, "size": 2.0, "watts": 20},
        "fill": {"direction": [1.2, -0.9, 0.6], "distance": 3.5, "size": 3.0, "watts": 10},
        "rim": {"direction": [0.4, 1.3, 1.1], "distance": 3.0, "size": 2.0, "watts": 8},
    },
    "default_look": "grey-plastic",
    "looks": {},
    "context_color": [0.80, 0.81, 0.83],
    "lines": {
        "crease_angle_deg": 110,
        "subject": {"color": [0.06, 0.06, 0.08], "thickness": 2.6},
        "context": {"color": [0.42, 0.43, 0.46], "thickness": 0.9},
    },
    "arrow": {"color": [0.95, 0.35, 0.05], "shaft_fraction": 0.16, "head_radius_factor": 2.4, "head_length_factor": 4.0,
              "start_gap_fraction": 0.03, "tip_gap_fraction": 0.2},
    "palette": PALETTE,
}

# render.json may set these top-level keys; palette entries may be added, not the whole palette replaced.
OVERRIDABLE = {"engine", "samples", "preview_samples", "long_side_px", "preview_long_side_px", "thumbnail_px", "aspect", "fill",
               "thumbnail_fill", "thumbnail_direction", "film_transparent", "view_transform", "look", "exposure", "world", "studio",
               "default_look", "looks", "context_color", "lines", "arrow", "palette", "note", "schema_version"}


class SettingsError(ValueError):
    pass


def load_settings(project_dir):
    """(settings dict, path of render.json or None)."""
    path = Path(project_dir) / "render.json"
    s = json.loads(json.dumps(DEFAULTS))
    if not path.exists():
        return s, None
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise SettingsError("render.json: top level must be an object")
    extra = sorted(set(data) - OVERRIDABLE)
    if extra:
        raise SettingsError(f"render.json: unsupported field(s) {extra}")
    if data.get("schema_version", "draft-1") != "draft-1":
        raise SettingsError("render.json: schema_version must be 'draft-1'")
    for k, v in data.items():
        if k in ("note", "schema_version"):
            continue
        if k in ("palette", "looks", "studio", "lines", "arrow", "world") and isinstance(v, dict):
            s[k].update(v)
        else:
            s[k] = v
    if not isinstance(s["looks"], dict) or any(not isinstance(x, str) for x in s["looks"].values()):
        raise SettingsError("render.json: looks must map part id -> look name")
    unknown = sorted(set(s["looks"].values()) - set(s["palette"]))
    if unknown:
        raise SettingsError(f"render.json: unknown look(s) {unknown}; palette has {sorted(s['palette'])}")
    return s, path
