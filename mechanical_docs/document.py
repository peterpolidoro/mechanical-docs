"""Build the manual from the validated project and the render receipt.

    python3 -m mechanical_docs manual PROJECT_DIR --renders DIR --out DIR [--meshes FILE] [--no-pdf] [--embed-images] [--appendix]

Writes OUT/manual.json (the one document model both outputs are generated
from), OUT/images/ (the renders this manual uses, copied and hashed),
OUT/index.html, OUT/manual.typ and, when `typst` is on PATH, OUT/<id>.pdf,
plus OUT/build-receipt.json. Quantities and step order come from the validated
manifests; images come from the render receipt, which must have been made
from the same inputs. Nothing is invented: unknown stock stays unknown and the
review state is printed on both outputs.

The printed inventory is picture-led and compact: one card per part with a
large picture (a wide picture and an end view for long parts), a short label,
the overall size, the CAD instance count labelled as such and a blank box for
the counted quantity. Subassembly inspection views from the render receipt
(kind `group`) get one page each: the parts at their CAD poses, never a step.
Joint close-ups (kind `joint`) get one page each too. Supplementary items
from `supplement.json` (hardware not modelled in CAD) are a separate section
and per-joint lists, never part of the CAD counts; rows with scope `new_design`
print in the appendix only. Full identities (Vault ids, occurrence paths,
every hash, every supplement field) are always in manual.json and
build-receipt.json; `--appendix` prints them as a technical appendix as well,
so the default printed document stays compact.
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

from . import receipts
from .manifest import ManifestError, load_project
from .names import slug
from .procedure import derive_states
from . import html as html_out
from . import typst as typst_out


class DocumentError(ValueError):
    pass


CAD_QTY_NOTE = ("CAD qty is the number of instances of the part in the CAD model (reference-only geometry excluded). "
                "It is not a purchase quantity: purchased kits, pack sizes, spares and stock are not reconciled.")
SUPPLEMENT_NOTE = ("Supplementary items are hardware, consumables or purchased items that are not modelled in CAD. They are listed "
                   "for review and are never added to CAD quantities; an unknown quantity stays unknown. This is not an approved bill of materials.")
HARDWARE_HEADING = "Hardware to review at this joint (not an approved BOM)"
COUNT_BOX_NOTE = "The counted box is for a paper count only; recorded stock is on_hand_each in the project's manifests."
STATUS_TEXT = {"candidate_requires_review": "candidate, requires review", "not_required": "not required",
               "covered": "covered (included with another item)", "specified": "specified"}
KIND_TEXT = {"family": "item family, no SKU", "sku": "SKU"}


def stock_text(on_hand, counted_by=None, counted_date=None, location=None, on_order=None):
    """'on hand 3 (counted 2026-10-22 by X, drawer A); on order 0' or 'on hand unknown'.
    Unknown is printed as unknown, never as 0."""
    if on_hand is None:
        text = "on hand unknown"
    else:
        text = f"on hand {on_hand} (counted {counted_date} by {counted_by}" + (f", {location}" if location else "") + ")"
    if on_order is not None:
        text += f"; on order {on_order}"
    return text


def required_text(item):
    if item.item_kind == "family":
        text = "required unknown (family, not specified)"
    else:
        text = "required unknown" if item.confirmed_required_each is None else f"required {item.confirmed_required_each}"
    if item.quantity_basis:
        text += f"; basis: {item.quantity_basis}"
    return text


def included_with_text(inc, label_of, parts):
    if not inc:
        return ""
    if inc["kind"] == "scene_part":
        return f"included with part {label_of.get(inc['id'], '?')} ({display_name(parts[inc['id']])})"
    return f"included with kit: {inc['name']}"


def fmt(v):
    return f"{v:g}"


def fmt_mm(v):
    """Millimetres for a label: whole numbers from 100 mm, one decimal below."""
    return f"{v:.0f}" if v >= 100 else f"{v:.1f}".rstrip("0").rstrip(".")


def fmt_in(v_mm):
    return f"{v_mm / 25.4:.3f}".rstrip("0").rstrip(".")


def display_name(part):
    """The exporter's name with underscores as spaces; nothing dropped or added."""
    return " ".join(part.name.replace("_", " ").split())


def dimensions_text(dims, asset_units="mm"):
    """'overall 80 × 32 × 28 mm' from an exporter extent (longest first; the inch
    equivalent for an inch asset), or '100 × 60 × 8 mm, hole Ø10.5 mm' from the
    fixtures' named dimensions."""
    if not dims:
        return ""
    parts = []
    if "extent" in dims:
        ext = sorted(dims["extent"], reverse=True)
        text = "overall " + " × ".join(fmt_mm(v) for v in ext) + " mm"
        if asset_units == "in":
            text += " (" + " × ".join(fmt_in(v) for v in ext) + " in)"
        parts.append(text)
    box = [dims[k] for k in ("width", "depth", "height") if k in dims]
    if len(box) == 3:
        parts.append(" × ".join(fmt(v) for v in box) + " mm")
    if "diameter" in dims and "length" in dims:
        parts.append(f"Ø{fmt(dims['diameter'])} × {fmt(dims['length'])} mm")
    for k, v in dims.items():
        if k == "extent" or (k in ("width", "depth", "height") and len(box) == 3):
            continue
        if k in ("diameter", "length") and "diameter" in dims and "length" in dims:
            continue
        label = k.replace("_", " ")
        if "diameter" in k:
            parts.append(f"{label.replace(' diameter', '')} Ø{fmt(v)} mm".strip())
        else:
            parts.append(f"{label} {fmt(v)} mm")
    return ", ".join(parts)


def part_details(part):
    """Short metadata line for the card when the exporter supplied it: part
    number, material, body count, a non-default BOM structure. Vendor,
    manufacturer, model state and Vault identity go to the appendix."""
    bits = []
    pr = part.properties or {}
    if pr.get("part_number"):
        bits.append(f"P/N {pr['part_number']}")
    if pr.get("material"):
        bits.append(str(pr["material"]))
    if part.bodies and part.bodies.get("solid_bodies", 1) != 1:
        bits.append(f"{part.bodies['solid_bodies']} bodies")
    if part.bom_structure_default and part.bom_structure_default != "Normal":
        bits.append(f"BOM {part.bom_structure_default}")
    return " · ".join(bits)


def build_model(project, render_receipt, meshes_receipt=None, appendix=False):
    sc, ins, inv = project.scene, project.instructions, project.inventory
    states = derive_states(ins, sc) if ins is not None else []
    views = {v["id"]: v for v in render_receipt["views"]}
    if render_receipt.get("partial"):
        raise DocumentError("render receipt is partial (--views without --reuse); render every view before building the manual")
    # the images depend on the scene, the assets and the instructions; a later stock
    # count or supplement row needs a new manual, not a new render
    stale = {k: v for k, v in project.render_input_hashes().items() if render_receipt["input_hashes"].get(k) != v}
    if stale:
        raise DocumentError(f"render receipt was made from a different scene, assets or instructions: {sorted(stale)}")
    if not render_receipt.get("all_checks_passed"):
        raise DocumentError("render receipt reports failed checks; fix the renders first")

    def view_file(vid):
        if vid not in views:
            raise DocumentError(f"render receipt has no view {vid!r}")
        return views[vid]["file"]

    label_of = {}
    inventory = []
    for n, item in enumerate(inv.items, 1):
        part = sc.parts[item.part_id]
        label_of[part.id] = n
        tv = views.get(f"part-{slug(part.id)}") or {}
        end_id = tv.get("end_view")
        parents = {}
        for o in sc.installed_occurrences_of(part.id):
            parents[o.parent_id] = parents.get(o.parent_id, 0) + 1
        inventory.append({
            "label": n, "part_id": part.id, "name": part.name, "label_text": display_name(part), "description": part.description,
            "dimensions": dimensions_text(part.identifying_dimensions_mm, part.asset.units), "identifying_dimensions_mm": part.identifying_dimensions_mm,
            "asset_units": part.asset.units, "asset_path": part.asset.path, "asset_sha256": part.asset.sha256,
            "details": part_details(part), "properties": part.properties, "model_state": part.model_state,
            "bom_structure_default": part.bom_structure_default, "bodies": part.bodies, "source": part.source,
            "required": item.required, "unit": item.unit,
            "on_hand_each": item.on_hand_each, "counted_by": item.counted_by, "counted_date": item.counted_date, "stock_location": item.stock_location,
            "intended_configuration_confirmed": item.intended_configuration_confirmed,
            "stock_text": stock_text(item.on_hand_each, item.counted_by, item.counted_date, item.stock_location) if item.extended else "",
            "occurrences": [o.id for o in sc.installed_occurrences_of(part.id)],
            "reference_occurrences": [o.id for o in sc.occurrences_of(part.id) if not o.installed],
            "parents": parents,
            "coincident": sc.coincident_of(part.id),
            "review_note": (f"{len(sc.coincident_of(part.id))} coincident instance pair(s) in CAD: review before counting as stock"
                            if sc.coincident_of(part.id) else ""),
            "thumbnail": view_file(f"part-{slug(part.id)}"), "thumbnail_style": tv.get("style", "square"),
            "end_view": view_file(end_id) if end_id else None,
        })
    groups = []
    for v in render_receipt["views"]:
        if v.get("kind") != "group":
            continue
        gid = v["group_id"]
        if gid not in sc.assemblies:
            raise DocumentError(f"render receipt view {v['id']} names unknown assembly {gid!r}")
        counts = {}
        for oid in v["visible"]:
            if oid not in sc.occurrences or gid not in sc.occurrences[oid].path:
                raise DocumentError(f"render receipt view {v['id']}: occurrence {oid!r} is not under {gid!r}")
            pid = sc.occurrences[oid].part_id
            counts[pid] = counts.get(pid, 0) + 1
        expected = [o.id for o in sc.occurrences.values() if gid in o.path]
        if sorted(expected) != sorted(v["visible"]):
            raise DocumentError(f"render receipt view {v['id']} does not show every occurrence under {gid!r}")
        asm = sc.assemblies[gid]
        groups.append({
            "index": len(groups) + 1, "id": gid, "short_name": gid.split("/")[-1], "parent_id": asm.parent_id, "path": v.get("assembly_path", []),
            "depth": asm.depth, "flexible": asm.flexible, "image": view_file(v["id"]), "view_id": v["id"],
            "occurrences": [{"id": oid, "part_id": sc.occurrences[oid].part_id, "label": label_of[sc.occurrences[oid].part_id], "parent_id": sc.occurrences[oid].parent_id} for oid in v["visible"]],
            "parts": [{"part_id": pid, "label": label_of[pid], "name": sc.parts[pid].name, "label_text": display_name(sc.parts[pid]), "qty": q,
                       "thumbnail": view_file(f"part-{slug(pid)}")} for pid, q in sorted(counts.items(), key=lambda kv: label_of[kv[0]])],
            "poses": v.get("poses", "canonical"), "exploded": bool(v.get("exploded", False)),
            "note": v.get("note", "inspection view: occurrences at their CAD poses; not an assembly step"),
        })
    joints = []
    for v in render_receipt["views"]:
        if v.get("kind") != "joint":
            continue
        subject = v["occurrence_ids"]
        for oid in subject:
            if oid not in sc.occurrences:
                raise DocumentError(f"render receipt view {v['id']} names unknown occurrence {oid!r}")
        ctx = v["context_assembly"]
        if ctx not in sc.assemblies:
            raise DocumentError(f"render receipt view {v['id']} names unknown context assembly {ctx!r}")
        outside = [oid for oid in subject if ctx not in sc.occurrences[oid].path]
        if outside:
            raise DocumentError(f"render receipt view {v['id']}: occurrence(s) {outside} are not under {ctx!r}")
        rest = sorted(oid for oid in sc.members(ctx) if oid not in subject)
        if sorted(v.get("context_occurrences", [])) != rest:
            raise DocumentError(f"render receipt view {v['id']}: context does not list exactly the other occurrences under {ctx!r}")
        counts = {}
        for oid in subject:
            counts[sc.occurrences[oid].part_id] = counts.get(sc.occurrences[oid].part_id, 0) + 1
        joints.append({
            "index": len(joints) + 1, "joint_id": v["joint_id"], "view_id": v["id"], "image": view_file(v["id"]),
            "occurrences": [{"id": oid, "part_id": sc.occurrences[oid].part_id, "label": label_of[sc.occurrences[oid].part_id],
                             "label_text": display_name(sc.parts[sc.occurrences[oid].part_id]), "parent_id": sc.occurrences[oid].parent_id,
                             "thumbnail": view_file(f"part-{slug(sc.occurrences[oid].part_id)}")} for oid in subject],
            "parts": [{"part_id": pid, "label": label_of[pid], "label_text": display_name(sc.parts[pid]), "qty": q} for pid, q in sorted(counts.items(), key=lambda kv: label_of[kv[0]])],
            "context_assembly": ctx, "context_short": ctx.split("/")[-1], "context_style": v.get("context_style"), "context_occurrences": rest,
            "direction": v.get("direction"), "poses": v.get("poses", "canonical"), "exploded": bool(v.get("exploded", False)),
            "note": v.get("note", "inspection view, not a step"),
            "hardware": [],
        })
    # supplementary items: separate from the CAD counts, attached to joints and groups
    sup = project.supplement
    sup_rows = []
    if sup is not None:
        for n, it in enumerate(sup.items, 1):
            groups_hit = [g["id"] for g in groups if any(sc.under(a, g["id"]) for a in it.attaches_to)]
            joints_hit = [j["view_id"] for j in joints if j["joint_id"] == it.joint_id]
            row = {**it.as_dict(), "index": n, "label": f"S{n}",
                   "title": it.candidate_item_family if it.item_kind == "family" or not it.specification else it.specification,
                   "kind_text": KIND_TEXT[it.item_kind], "status_text": STATUS_TEXT[it.status],
                   "required_text": required_text(it),
                   "stock_text": stock_text(it.on_hand_each, it.counted_by, it.counted_date, it.stock_location, it.on_order_each),
                   "included_with_text": included_with_text(it.included_with, label_of, sc.parts),
                   "attaches_text": ", ".join(a.split("/")[-1] for a in it.attaches_to) or "not placed",
                   "attaches_to_groups": groups_hit, "joint_views": joints_hit, "appendix_only": it.scope == "new_design"}
            sup_rows.append(row)
        for g in groups:
            g["hardware"] = [{"label": r["label"], "item_id": r["item_id"], "title": r["title"], "status_text": r["status_text"], "required_text": r["required_text"], "joint_id": r["joint_id"]}
                             for r in sup_rows if g["id"] in r["attaches_to_groups"]]
        for j in joints:
            j["hardware"] = [{"label": r["label"], "item_id": r["item_id"], "title": r["title"], "status_text": r["status_text"], "required_text": r["required_text"], "joint_id": r["joint_id"]}
                             for r in sup_rows if j["view_id"] in r["joint_views"]]
    supplement = {
        "present": sup is not None, "status": sup.status if sup else "", "source": sup.source if sup else {},
        "note": SUPPLEMENT_NOTE, "hardware_heading": HARDWARE_HEADING, "rows": sup_rows,
        "existing": [r["item_id"] for r in sup_rows if not r["appendix_only"]], "new_design": [r["item_id"] for r in sup_rows if r["appendix_only"]],
        "by_group": {g["id"]: [h["item_id"] for h in g.get("hardware", [])] for g in groups},
        "by_joint": {j["view_id"]: [h["item_id"] for h in j["hardware"]] for j in joints},
    }
    for g in groups:
        g.setdefault("hardware", [])
    steps = []
    for st in states:
        needed = []
        for pid, qty in st.parts_needed.items():
            needed.append({"part_id": pid, "label": label_of[pid], "name": sc.parts[pid].name, "qty": qty, "thumbnail": view_file(f"part-{slug(pid)}")})
        vid = f"step-{st.index:02d}-{slug(st.step.id)}"
        ap = st.step.approach
        steps.append({
            "index": st.index, "id": st.step.id, "caption": st.step.caption, "requires": st.step.requires,
            "add": st.added, "installed_before": st.before, "installed_after": st.after,
            "parts_needed": needed, "image": view_file(vid),
            "result_image": view_file(vid + "-result") if ap is not None else None,
            "approach": None if ap is None else {"occurrence_id": ap.occurrence_id, "start_offset": ap.start_offset, "validation": ap.validation,
                                                 "direction_text": approach_text(ap.start_offset)},
            "view": st.step.view,
        })
    source_summary = {k: v for k, v in sc.source.items() if k in ("kind", "generator", "qualification", "revision", "version", "root_version_id",
                                                                   "exported_at", "exporter", "occurrence_id_scope")}
    model = {
        "kind": "mechanical-docs-manual", "generated_at_utc": receipts.utc_now(),
        "id": ins.id if ins is not None else f"{slug(sc.id)}-inventory",
        "title": ins.title if ins is not None else f"{sc.title}: parts inventory",
        "scene": {"id": sc.id, "title": sc.title, "units": sc.units, "native_up_axis": sc.native_up_axis, "source": sc.source, "source_summary": source_summary,
                  "parts": len(sc.parts), "occurrences": len(sc.occurrences), "assemblies": len(sc.assemblies)},
        "review_state": ins.review_state if ins is not None else "draft",
        "inventory_only": ins is None,
        "status_lines": status_lines(project, render_receipt, bool(groups), bool(joints)),
        "findings": {"coincident_occurrences": sc.coincident},
        "project_notes": list(inv.notes),
        "inventory_status": inv.status,
        "cad_qty_note": CAD_QTY_NOTE, "count_box_note": COUNT_BOX_NOTE,
        "inventory": inventory,
        "overview_image": view_file("overview"),
        "groups": groups,
        "joints": joints,
        "supplement": supplement,
        "steps": steps,
        "appendix": bool(appendix),
        "hotspots": {v["id"]: f"hotspots/{v['id']}.json" for v in render_receipt["views"] if v.get("kind") in ("overview", "group", "joint", "step", "step-result")},
        "receipt": {
            "input_hashes": project.input_hashes(),
            "meshes": None if meshes_receipt is None else {"freecad_version": meshes_receipt.get("freecad_version"), "tessellation": meshes_receipt.get("tessellation"),
                                                           "mesh_hashes": {k: v["mesh"]["sha256"] for k, v in meshes_receipt["parts"].items()},
                                                           "all_checks_passed": meshes_receipt.get("all_checks_passed"),
                                                           "sha256": render_receipt.get("meshes_json_sha256")},
            "render": {k: render_receipt.get(k) for k in ("generated_at_utc", "blender", "engine", "denoiser", "preview", "samples", "long_side_px", "settings_sha256",
                                                          "lines", "lines_max_triangles", "all_checks_passed", "warnings", "reused_from", "reused_views", "inspection_groups", "joint_views")},
            "render_views": {v["id"]: v["sha256"] for v in render_receipt["views"]},
            "render_view_details": {v["id"]: {k: v.get(k) for k in ("kind", "width", "height", "seconds", "lines", "visible_triangles", "reused_from", "reused_generated_at_utc", "style")}
                                    for v in render_receipt["views"]},
            "generator": {**receipts.python_info(), "package": "mechanical-docs"},
        },
    }
    return model


def approach_text(offset):
    x, y, z = offset
    axes = [("from above", z > 0), ("from below", z < 0), ("from +X", x > 0), ("from −X", x < 0), ("from +Y", y > 0), ("from −Y", y < 0)]
    mags = [abs(z), abs(z), abs(x), abs(x), abs(y), abs(y)]
    best = max(range(6), key=lambda i: mags[i] if axes[i][1] else -1)
    return axes[best][0] if mags[best] > 0 else "in place"


def status_lines(project, render_receipt, has_groups=False, has_joints=False):
    ins, sc, inv, sup = project.instructions, project.scene, project.inventory, project.supplement
    if ins is None:
        lines = ["Parts inventory and overview only: no assembly sequence has been authored or reviewed for this scene."]
    else:
        lines = [f"Review state: {ins.review_state}. This sequence has not been physically validated."]
    if sc.source.get("kind", "").startswith("autodesk-inventor"):
        lines.append("Geometry and hierarchy come from the CAD export named in the build record. "
                     "Quantities are CAD instance counts, not purchase quantities, kits, stock or an approved bill of materials.")
    if sc.source.get("kind") == "synthetic":
        lines.append("Synthetic documentation fixture: not a product, not a manufactured design, not a project component.")
    for note in inv.notes:
        lines.append(f"Project note: {note}")
    if has_groups or has_joints:
        lines.append(("Subassembly pages" if has_groups else "Joint pages") + (" and joint close-ups" if has_groups and has_joints else "")
                     + " are inspection views of parts at their CAD positions; they are not assembly steps and imply no sequence, fasteners or tool access.")
    if sup is not None:
        n_new = sum(1 for it in sup.items if it.scope == "new_design")
        lines.append(f"Supplementary items ({len(sup.items)} rows, {len(sup.items) - n_new} for the existing design"
                     + (f", {n_new} for new design in the appendix only" if n_new else "") + ") are hardware not modelled in CAD: "
                     "listed separately for review, never added to CAD quantities, unknown quantities left unknown; not an approved bill of materials.")
    if sc.coincident:
        names = sorted({sc.parts[c["part_id"]].name for c in sc.coincident})
        lines.append(f"CAD ambiguity: {len(sc.coincident)} pair(s) of occurrences of the same part share one position ({'; '.join(names)}). "
                     "All source instances are kept and counted; review the intended configuration before treating the count as stock.")
    if ins is not None:
        lines.append("Approach arrows are unverified render hints; they do not prove an insertion path or tool access.")
    counted = [it for it in inv.items if it.on_hand_each is not None]
    if counted:
        dates = sorted({it.counted_date for it in counted})
        lines.append(f"Recorded stock: {len(counted)} of {len(inv.items)} parts have an on-hand count (counted {dates[0]}" + (f" to {dates[-1]}" if len(dates) > 1 else "")
                     + "); the others are unknown. The counted box is for a new paper count and is not read back.")
    else:
        lines.append("Stock is unknown until counted and recorded (on_hand_each with counted_by and counted_date). The counted box is for a paper count only.")
    if render_receipt.get("preview"):
        lines.append("Preview-quality renders.")
    return lines


def model_images(model):
    names = {row["thumbnail"] for row in model["inventory"]} | {row["end_view"] for row in model["inventory"] if row["end_view"]}
    names |= {model["overview_image"]} | {g["image"] for g in model["groups"]} | {j["image"] for j in model["joints"]}
    names |= {s["image"] for s in model["steps"]} | {s["result_image"] for s in model["steps"] if s["result_image"]}
    return sorted(names)


def stage_images(model, renders_dir, out_dir):
    dst = Path(out_dir) / "images"
    dst.mkdir(parents=True, exist_ok=True)
    staged = {}
    for name in model_images(model):
        src = Path(renders_dir) / name
        if not src.is_file():
            raise DocumentError(f"render {name} listed in the receipt is missing from {renders_dir}")
        shutil.copyfile(src, dst / name)
        staged[name] = receipts.file_entry(dst / name, out_dir)
    hs_src = Path(renders_dir) / "hotspots"
    if hs_src.is_dir():
        hs_dst = Path(out_dir) / "hotspots"; hs_dst.mkdir(exist_ok=True)
        for p in hs_src.glob("*.json"):
            shutil.copyfile(p, hs_dst / p.name)
    return staged


def compile_pdf(out_dir, typ_path, pdf_path):
    exe = shutil.which("typst")
    if not exe:
        return {"ran": False, "reason": "typst not on PATH"}
    cmd = [exe, "compile", "--root", str(out_dir), str(typ_path), str(pdf_path)]
    r = subprocess.run(cmd, capture_output=True, text=True)
    info = {"ran": True, "command": " ".join(cmd), "returncode": r.returncode, "stderr": r.stderr[-2000:]}
    v = subprocess.run([exe, "--version"], capture_output=True, text=True)
    info["typst_version"] = v.stdout.strip()
    if r.returncode == 0:
        info["pdf"] = receipts.file_entry(pdf_path, out_dir)
    return info


def build(args):
    try:
        project = load_project(args.project_dir)
    except ManifestError as e:
        print(e, file=sys.stderr)
        return 2
    renders = Path(args.renders)
    out = Path(args.out)
    rr_path = renders / "render-receipt.json"
    if not rr_path.is_file():
        print(f"no render receipt at {rr_path}", file=sys.stderr)
        return 2
    rr = receipts.read_json(rr_path)
    mr = receipts.read_json(args.meshes) if args.meshes else None
    try:
        model = build_model(project, rr, mr, appendix=getattr(args, "appendix", False))
        out.mkdir(parents=True, exist_ok=True)
        staged = stage_images(model, renders, out)
    except DocumentError as e:
        print(f"manual: {e}", file=sys.stderr)
        return 2
    model["images"] = staged
    receipts.write_json(out / "manual.json", model)
    html_text = html_out.render(model, out, embed_images=args.embed_images)
    (out / "index.html").write_text(html_text, encoding="utf-8")
    typ_text = typst_out.render(model)
    typ_path = out / "manual.typ"
    typ_path.write_text(typ_text, encoding="utf-8")
    pdf_name = f"{model['id']}.pdf"
    pdf_info = {"ran": False, "reason": "--no-pdf"} if args.no_pdf else compile_pdf(out, typ_path, out / pdf_name)
    receipt = {
        "kind": "mechanical-docs-build-receipt", "generated_at_utc": receipts.utc_now(), **receipts.python_info(),
        "project_dir": str(project.dir), "input_hashes": project.input_hashes(),
        "render_receipt": receipts.file_entry(rr_path), "meshes_receipt": receipts.file_entry(args.meshes) if args.meshes else None,
        "appendix_printed": model["appendix"], "groups": [g["id"] for g in model["groups"]], "joints": [j["joint_id"] for j in model["joints"]],
        "supplement_rows": len(model["supplement"]["rows"]),
        "outputs": {"manual.json": receipts.file_entry(out / "manual.json", out), "index.html": receipts.file_entry(out / "index.html", out),
                    "manual.typ": receipts.file_entry(typ_path, out), "images": staged},
        "pdf": pdf_info,
        "review_state": model["review_state"], "physical_assembly_validated": False,
        "not_checked_here": ["HTML/PDF agreement and link resolution (run `check`)", "page breaks and legibility (inspect the PDF pages)"],
    }
    receipts.write_json(out / "build-receipt.json", receipt)
    print(f"wrote {out / 'manual.json'}, {out / 'index.html'}, {typ_path}" + (f", {out / pdf_name}" if pdf_info.get("pdf") else ""))
    if pdf_info.get("ran") and pdf_info.get("returncode"):
        print("typst failed:\n" + pdf_info["stderr"], file=sys.stderr)
        return 1
    if not pdf_info.get("ran"):
        print(f"PDF not built: {pdf_info.get('reason')}")
    return 0
