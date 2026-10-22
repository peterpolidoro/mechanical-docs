"""Build the manual from the validated project and the render receipt.

    python3 -m mechanical_docs manual PROJECT_DIR --renders DIR --out DIR [--meshes FILE] [--no-pdf] [--embed-images]

Writes OUT/manual.json (the one document model both outputs are generated
from), OUT/images/ (the renders this manual uses, copied and hashed),
OUT/index.html, OUT/manual.typ and, when `typst` is on PATH, OUT/<id>.pdf,
plus OUT/build-receipt.json. Quantities and step order come from the validated
manifests; images come from the render receipt, which must have been made
from the same inputs. Nothing is invented: unknown stock stays unknown and the
review state is printed on both outputs.
"""
from __future__ import annotations

import base64
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


def dimensions_text(dims):
    """'100 × 60 × 8 mm, hole Ø10.5 mm' from identifying_dimensions_mm."""
    if not dims:
        return ""
    box = [dims[k] for k in ("width", "depth", "height") if k in dims]
    parts = []
    if len(box) == 3:
        parts.append(" × ".join(fmt(v) for v in box) + " mm")
    if "extent" in dims:
        parts.append("extent " + " × ".join(fmt(round(v, 1)) for v in dims["extent"]) + " mm")
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


def fmt(v):
    return f"{v:g}"


def part_details(part):
    """Short provenance/metadata line for a part when the exporter supplied it."""
    bits = []
    pr = part.properties or {}
    if pr.get("part_number"):
        bits.append(f"P/N {pr['part_number']}")
    for k in ("material", "vendor", "manufacturer"):
        if pr.get(k):
            bits.append(str(pr[k]))
    if part.model_state:
        bits.append(part.model_state)
    if part.bodies and part.bodies.get("solid_bodies", 1) != 1:
        bits.append(f"{part.bodies['solid_bodies']} bodies")
    if part.bom_structure_default and part.bom_structure_default != "Normal":
        bits.append(f"BOM {part.bom_structure_default}")
    return " · ".join(bits)


def build_model(project, render_receipt, meshes_receipt=None):
    sc, ins, inv = project.scene, project.instructions, project.inventory
    states = derive_states(ins, sc) if ins is not None else []
    views = {v["id"]: v for v in render_receipt["views"]}
    if render_receipt.get("partial"):
        raise DocumentError("render receipt is partial (--views); render every view before building the manual")
    if render_receipt.get("preview"):
        pass  # allowed, but recorded
    stale = {k: v for k, v in project.input_hashes().items() if render_receipt["input_hashes"].get(k) != v}
    if stale:
        raise DocumentError(f"render receipt was made from different inputs: {sorted(stale)}")
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
        inventory.append({
            "label": n, "part_id": part.id, "name": part.name, "description": part.description,
            "dimensions": dimensions_text(part.identifying_dimensions_mm), "identifying_dimensions_mm": part.identifying_dimensions_mm,
            "details": part_details(part), "properties": part.properties, "model_state": part.model_state,
            "bom_structure_default": part.bom_structure_default, "bodies": part.bodies, "source": part.source,
            "required": item.required, "unit": item.unit, "counted": item.counted,
            "occurrences": [o.id for o in sc.installed_occurrences_of(part.id)],
            "reference_occurrences": [o.id for o in sc.occurrences_of(part.id) if not o.installed],
            "thumbnail": view_file(f"part-{slug(part.id)}"),
        })
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
    model = {
        "kind": "mechanical-docs-manual", "generated_at_utc": receipts.utc_now(),
        "id": ins.id if ins is not None else f"{slug(sc.id)}-inventory",
        "title": ins.title if ins is not None else f"{sc.title}: parts inventory",
        "scene": {"id": sc.id, "title": sc.title, "units": sc.units, "native_up_axis": sc.native_up_axis, "source": sc.source,
                  "parts": len(sc.parts), "occurrences": len(sc.occurrences), "assemblies": len(sc.assemblies)},
        "review_state": ins.review_state if ins is not None else "draft",
        "inventory_only": ins is None,
        "status_lines": status_lines(project, render_receipt),
        "inventory_status": inv.status,
        "inventory": inventory,
        "overview_image": view_file("overview"),
        "steps": steps,
        "hotspots": {v["id"]: f"hotspots/{v['id']}.json" for v in render_receipt["views"] if v.get("kind") in ("overview", "step", "step-result")},
        "receipt": {
            "input_hashes": project.input_hashes(),
            "meshes": None if meshes_receipt is None else {"freecad_version": meshes_receipt.get("freecad_version"), "tessellation": meshes_receipt.get("tessellation"),
                                                           "mesh_hashes": {k: v["mesh"]["sha256"] for k, v in meshes_receipt["parts"].items()},
                                                           "all_checks_passed": meshes_receipt.get("all_checks_passed")},
            "render": {k: render_receipt.get(k) for k in ("blender", "engine", "denoiser", "preview", "samples", "long_side_px", "settings_sha256", "all_checks_passed", "warnings")},
            "render_views": {v["id"]: v["sha256"] for v in render_receipt["views"]},
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


def status_lines(project, render_receipt):
    ins, sc = project.instructions, project.scene
    if ins is None:
        lines = ["Parts inventory and overview only: no assembly sequence has been authored or reviewed for this scene."]
    else:
        lines = [f"Review state: {ins.review_state}. This sequence has not been physically validated."]
    if sc.source.get("kind", "").startswith("autodesk-inventor"):
        lines.append("Geometry/hierarchy snapshot from the CAD export named in the build record; not an accepted BOM, not a purchase list.")
    if sc.source.get("kind") == "synthetic":
        lines.append("Synthetic documentation fixture: not a product, not a manufactured design, not a project component.")
    lines.append("Approach arrows are unverified render hints; they do not prove an insertion path or tool access.")
    lines.append("Required quantities come from the CAD scene. Stock is unknown until counted and recorded.")
    if render_receipt.get("preview"):
        lines.append("Preview-quality renders.")
    return lines


def stage_images(model, renders_dir, out_dir):
    images = sorted({row["thumbnail"] for row in model["inventory"]} | {model["overview_image"]}
                    | {s["image"] for s in model["steps"]} | {s["result_image"] for s in model["steps"] if s["result_image"]})
    dst = Path(out_dir) / "images"
    dst.mkdir(parents=True, exist_ok=True)
    staged = {}
    for name in images:
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
        model = build_model(project, rr, mr)
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
