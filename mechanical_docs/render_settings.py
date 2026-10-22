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
    # Cycles path tracing is the reference look (contact shadows, physically based
    # shading); it needs a Blender with OpenImageDenoise, which the official bpy
    # wheel has and the Guix package lacks. Pass --engine BLENDER_EEVEE_NEXT for
    # fast, noise-free rasterised images on a Blender without the denoiser.
    "engine": "CYCLES",
    "samples": 64,                 # EEVEE TAA samples
    "preview_samples": 8,
    "cycles_samples": 64,          # Cycles path-tracing samples (adaptive, denoised)
    "cycles_preview_samples": 16,
    "cycles_adaptive_threshold": 0.01,
    "cycles_max_bounces": 4,       # flat illustration lighting converges in a few bounces
    "cycles_persistent_data": True,  # keep the BVH between views
    # A floor just under the lowest visible point of a view, catching contact
    # shadows onto the transparent film (Cycles only; EEVEE has no shadow catcher).
    # The catcher costs Cycles a second full pass (about 4x the view time), so by
    # default only the part thumbnails and the overview get it; add "step" and
    # "step-result" to `views` for the step images too.
    "floor": {"enabled": "auto", "views": ["part-thumbnail", "overview", "group", "joint"], "color": [0.46, 0.47, 0.49], "roughness": 0.9, "size_factor": 40},
    "long_side_px": 1600,
    "preview_long_side_px": 480,
    "thumbnail_px": 600,
    "aspect": [4, 3],
    "fill": 0.86,
    "thumbnail_fill": 0.78,
    "thumbnail_direction": [1.0, -1.2, 0.9],
    # A long part (longest extent at least `thumbnail_long_aspect` times the next) is
    # turned so its long axis runs along X and drawn in a wide image from
    # `thumbnail_long_direction`; a second image looks straight along the axis
    # (part-<id>-end.png: the profile/end detail that identifies an extrusion).
    "thumbnail_long_aspect": 4.0,
    "thumbnail_long_px": 1200,
    "thumbnail_long_aspect_px": [2, 1],
    "thumbnail_long_direction": [0.35, -1.0, 0.55],
    "thumbnail_end_view": True,
    # Isolated inspection views of subassemblies (assembly ids), occurrences at
    # their canonical poses: parts views, not assembly steps. --groups adds to this.
    "inspection_groups": [],
    "group_direction": [1.0, -1.2, 0.8],
    "group_fill": 0.84,
    # Per-joint close-ups: each entry names a project joint id and the specific
    # occurrences that form the joint; they are framed alone at their canonical
    # poses while the context (default: their deepest common ancestor; or any
    # assembly/occurrence ids, so a joint between two groups can fade just one
    # frame) is drawn faded or hidden. Inspection views, not steps.
    #   {"joint_id": "caster_to_plate", "occurrence_ids": ["…/CASTER:1", "…/PLATE:1"],
    #    "direction": [1, -1.2, 0.8], "context": "FREE STANDING FRAME:1/CASTER ASSEMBLY:1",
    #    "context_style": "faded", "id": "caster_to_plate-1"}
    "joint_views": [],
    "joint_direction": [1.0, -1.2, 0.8],
    "joint_fill": 0.80,
    "joint_context_style": "faded",
    "overview_direction": [1.0, -1.2, 0.8],   # used when a project has no instructions (inventory only)
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
        "enabled": True,
        # Freestyle's view map grows superlinearly with edge count; above this many visible
        # triangles a view is rendered without line art and the receipt says so
        "max_triangles": 3000000,
        "preview_max_triangles": 400000,
        "crease_angle_deg": 110,
        "subject": {"color": [0.06, 0.06, 0.08], "thickness": 2.6},
        "context": {"color": [0.42, 0.43, 0.46], "thickness": 0.9},
    },
    "arrow": {"color": [0.95, 0.35, 0.05], "shaft_fraction": 0.16, "head_radius_factor": 2.4, "head_length_factor": 4.0,
              "start_gap_fraction": 0.03, "tip_gap_fraction": 0.2},
    "palette": PALETTE,
}

# render.json may set these top-level keys; palette entries may be added, not the whole palette replaced.
OVERRIDABLE = {"engine", "samples", "preview_samples", "cycles_samples", "cycles_preview_samples", "cycles_adaptive_threshold", "cycles_max_bounces", "cycles_persistent_data", "floor", "long_side_px", "preview_long_side_px", "thumbnail_px", "aspect", "fill",
               "thumbnail_fill", "thumbnail_direction", "thumbnail_long_aspect", "thumbnail_long_px", "thumbnail_long_aspect_px", "thumbnail_long_direction", "thumbnail_end_view",
               "inspection_groups", "group_direction", "group_fill", "joint_views", "joint_direction", "joint_fill", "joint_context_style", "overview_direction", "film_transparent", "view_transform", "look", "exposure", "world", "studio",
               "default_look", "looks", "context_color", "lines", "arrow", "palette", "note", "schema_version"}


JOINT_VIEW_FIELDS = {"id", "joint_id", "occurrence_ids", "direction", "context", "context_style"}
JOINT_CONTEXT_STYLES = ("faded", "hidden")


class SettingsError(ValueError):
    pass


def _vec3(v):
    return isinstance(v, list) and len(v) == 3 and all(isinstance(x, (int, float)) and not isinstance(x, bool) for x in v)


def check_joint_views(views, context_style):
    """Structural validation of `joint_views` (scene ids are checked by the
    renderer, which has the scene). Returns the list with defaults filled."""
    if not isinstance(views, list):
        raise SettingsError("render.json: joint_views must be a list of objects")
    out = []
    for i, jv in enumerate(views):
        where = f"render.json: joint_views[{i}]"
        if not isinstance(jv, dict):
            raise SettingsError(f"{where}: expected an object")
        extra = sorted(set(jv) - JOINT_VIEW_FIELDS)
        if extra:
            raise SettingsError(f"{where}: unsupported field(s) {extra}; accepted {sorted(JOINT_VIEW_FIELDS)}")
        jid = jv.get("joint_id")
        if not isinstance(jid, str) or not jid.strip():
            raise SettingsError(f"{where}.joint_id: expected a non-empty string")
        occs = jv.get("occurrence_ids")
        if not isinstance(occs, list) or not occs or any(not isinstance(o, str) for o in occs):
            raise SettingsError(f"{where}.occurrence_ids: expected a non-empty list of occurrence ids")
        if len(set(occs)) != len(occs):
            raise SettingsError(f"{where}.occurrence_ids: an occurrence is listed twice")
        if "direction" in jv and not _vec3(jv["direction"]):
            raise SettingsError(f"{where}.direction: expected three numbers")
        ctx = jv.get("context")
        if "context" in jv and not ((isinstance(ctx, str) and ctx) or (isinstance(ctx, list) and ctx and all(isinstance(c, str) and c for c in ctx))):
            raise SettingsError(f"{where}.context: expected an assembly or occurrence id, or a list of them")
        style = jv.get("context_style", context_style)
        if style not in JOINT_CONTEXT_STYLES:
            raise SettingsError(f"{where}.context_style: expected one of {JOINT_CONTEXT_STYLES}, got {style!r}")
        if "id" in jv and (not isinstance(jv["id"], str) or not jv["id"].strip()):
            raise SettingsError(f"{where}.id: expected a non-empty string")
        out.append({"id": jv.get("id"), "joint_id": jid, "occurrence_ids": list(occs), "direction": jv.get("direction"),
                    "context": jv.get("context"), "context_style": style})
    return out


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
        if k in ("palette", "looks", "studio", "lines", "arrow", "world", "floor") and isinstance(v, dict):
            s[k].update(v)
        else:
            s[k] = v
    if not isinstance(s["looks"], dict) or any(not isinstance(x, str) for x in s["looks"].values()):
        raise SettingsError("render.json: looks must map part id -> look name")
    if not isinstance(s["inspection_groups"], list) or any(not isinstance(x, str) for x in s["inspection_groups"]):
        raise SettingsError("render.json: inspection_groups must be a list of assembly ids")
    if s["joint_context_style"] not in JOINT_CONTEXT_STYLES:
        raise SettingsError(f"render.json: joint_context_style must be one of {JOINT_CONTEXT_STYLES}")
    s["joint_views"] = check_joint_views(s["joint_views"], s["joint_context_style"])
    unknown = sorted(set(s["looks"].values()) - set(s["palette"]))
    if unknown:
        raise SettingsError(f"render.json: unknown look(s) {unknown}; palette has {sorted(s['palette'])}")
    return s, path
