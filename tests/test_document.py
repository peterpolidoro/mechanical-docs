"""The document stage against a synthetic render receipt (no Blender needed)."""
import json
import struct
import zlib
from pathlib import Path
from types import SimpleNamespace

import pytest

from mechanical_docs import checks, document, html as html_out, receipts, typst as typst_out
from mechanical_docs.manifest import load_project


def png(path, w=8, h=6, grey=200):
    """A tiny valid PNG so image tools accept it."""
    raw = b"".join(b"\x00" + bytes([grey, grey, grey, 255]) * w for _ in range(h))

    def chunk(t, d):
        return struct.pack(">I", len(d)) + t + d + struct.pack(">I", zlib.crc32(t + d) & 0xFFFFFFFF)

    data = b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 6, 0, 0, 0)) + chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b"")
    Path(path).write_bytes(data)


@pytest.fixture
def rendered(fixture_dir, tmp_path):
    """A fake but complete render receipt for the fixture, with image files."""
    project = load_project(fixture_dir)
    renders = tmp_path / "renders"; (renders / "hotspots").mkdir(parents=True)
    view_ids = ["part-base", "part-pin", "part-pin-end", "overview", "group-pin-pair", "joint-pin-to-base", "step-01-place-base", "step-02-insert-pin-a",
                "step-02-insert-pin-a-result", "step-03-insert-pin-b", "step-03-insert-pin-b-result"]
    views = []
    for vid in view_ids:
        p = renders / f"{vid}.png"; png(p)
        kind = ("part-end" if vid.endswith("-end") else "part-thumbnail" if vid.startswith("part-") else "overview" if vid == "overview"
                else "group" if vid.startswith("group-") else "joint" if vid.startswith("joint-") else "step-result" if vid.endswith("-result") else "step")
        rec = {"id": vid, "file": p.name, "sha256": receipts.sha256_file(p), "bytes": p.stat().st_size, "width": 8, "height": 6, "seconds": 0.1, "kind": kind}
        if vid == "part-pin":
            rec.update({"style": "long", "end_view": "part-pin-end", "long_axis": "z", "aspect": 3.0})
        if vid == "group-pin-pair":
            rec.update({"group_id": "pin-pair", "parent_id": "root", "assembly_path": ["root", "pin-pair"], "visible": ["pin-a", "pin-b"], "parts": {"pin": 2},
                        "poses": "canonical", "exploded": False, "note": "inspection view: occurrences at their CAD poses; not an assembly step"})
        if vid == "joint-pin-to-base":
            rec.update({"joint_id": "pin_to_base", "occurrence_ids": ["pin-a", "base-1"], "context_assembly": "root", "context_style": "faded",
                        "context_occurrences": ["pin-b"], "visible": ["pin-a", "base-1", "pin-b"], "hidden": [], "direction": [0.56, -0.67, 0.45],
                        "poses": "canonical", "exploded": False, "note": "inspection view, not a step"})
        views.append(rec)
    (renders / "hotspots" / "overview.json").write_text(json.dumps({"view": "overview", "width": 8, "height": 6, "occurrences": [
        {"id": "base-1", "part_id": "base", "box_px": [0, 0, 8, 6], "corners_in_frame": 8},
        {"id": "pin-a", "part_id": "pin", "box_px": [1, 1, 3, 3], "corners_in_frame": 8}]}))
    (renders / "hotspots" / "group-pin-pair.json").write_text(json.dumps({"view": "group-pin-pair", "width": 8, "height": 6, "occurrences": [
        {"id": "pin-a", "part_id": "pin", "box_px": [1, 1, 3, 3], "corners_in_frame": 8}, {"id": "pin-b", "part_id": "pin", "box_px": [5, 1, 7, 3], "corners_in_frame": 8}]}))
    (renders / "hotspots" / "joint-pin-to-base.json").write_text(json.dumps({"view": "joint-pin-to-base", "width": 8, "height": 6, "occurrences": [
        {"id": "pin-a", "part_id": "pin", "box_px": [1, 1, 3, 3], "corners_in_frame": 8}, {"id": "base-1", "part_id": "base", "box_px": [0, 2, 8, 6], "corners_in_frame": 8}]}))
    receipt = {"kind": "mechanical-docs-render-receipt", "blender": "test", "engine": "TEST", "denoiser": None, "preview": False, "samples": 1,
               "long_side_px": 8, "settings_sha256": "0" * 64, "input_hashes": project.input_hashes(), "views": views, "partial": False,
               "all_checks_passed": True, "warnings": []}
    receipts.write_json(renders / "render-receipt.json", receipt)
    return project, renders, receipt


def test_model_has_same_quantities_and_order(rendered):
    project, renders, receipt = rendered
    model = document.build_model(project, receipt)
    assert [(r["part_id"], r["required"], r["label"]) for r in model["inventory"]] == [("base", 1, 1), ("pin", 2, 2)]
    assert [s["id"] for s in model["steps"]] == ["place-base", "insert-pin-a", "insert-pin-b"]
    assert model["steps"][1]["parts_needed"] == [{"part_id": "pin", "label": 2, "name": "Pin", "qty": 1, "thumbnail": "part-pin.png"}]
    assert model["steps"][0]["result_image"] is None and model["steps"][1]["result_image"] == "step-02-insert-pin-a-result.png"
    assert model["steps"][1]["approach"]["direction_text"] == "from above"
    assert model["review_state"] == "draft"
    assert any("not been physically validated" in s for s in model["status_lines"])
    assert model["project_notes"] == [] and not any(s.startswith("Project note") for s in model["status_lines"])
    assert model["inventory"][0]["dimensions"] == "100 × 60 × 8 mm, hole Ø10.5 mm"
    assert model["inventory"][1]["dimensions"] == "Ø10 × 30 mm"
    # the long part carries its end view; the group view becomes a subassembly with part counts from the scene
    assert model["inventory"][1]["thumbnail_style"] == "long" and model["inventory"][1]["end_view"] == "part-pin-end.png"
    assert model["inventory"][0]["end_view"] is None
    assert [(g["id"], g["index"], g["short_name"], g["parent_id"]) for g in model["groups"]] == [("pin-pair", 1, "pin-pair", "root")]
    assert model["groups"][0]["parts"] == [{"part_id": "pin", "label": 2, "name": "Pin", "label_text": "Pin", "qty": 2, "thumbnail": "part-pin.png"}]
    assert [o["id"] for o in model["groups"][0]["occurrences"]] == ["pin-a", "pin-b"]
    assert any("not assembly steps" in s for s in model["status_lines"])
    assert model["appendix"] is False and "CAD qty" in model["cad_qty_note"]
    # the joint view becomes a joint page with the subject occurrences and the faded context
    assert [(j["joint_id"], j["index"], j["context_assembly"], j["context_occurrences"]) for j in model["joints"]] == [("pin_to_base", 1, "root", ["pin-b"])]
    assert [o["id"] for o in model["joints"][0]["occurrences"]] == ["pin-a", "base-1"]
    # supplementary rows: separate from the inventory, unknown stays unknown, attached to the group and the joint
    sup = model["supplement"]
    assert sup["present"] and [r["label"] for r in sup["rows"]] == ["S1", "S2", "S3"]
    assert sup["existing"] == ["pin-retainer", "pin-spacer"] and sup["new_design"] == ["pin-label"]
    assert sup["by_group"] == {"pin-pair": ["pin-retainer", "pin-spacer"]}       # pin-pair itself, and its occurrences pin-a/pin-b
    assert sup["by_joint"] == {"joint-pin-to-base": ["pin-retainer", "pin-spacer"]}
    r1, r2, r3 = sup["rows"]
    assert r1["required_text"].startswith("required unknown") and r1["stock_text"] == "on hand unknown" and r1["included_with_text"] == "included with kit: synthetic pin kit"
    assert r2["required_text"].startswith("required 2") and r2["stock_text"].startswith("on hand 3 (counted 2026-10-22 by fixture author, synthetic drawer A); on order 0")
    assert r2["included_with_text"] == "included with part 1 (Base)" and r3["attaches_text"] == "not placed" and r3["appendix_only"]
    assert [(r["required"]) for r in model["inventory"]] == [1, 2]                 # CAD quantities untouched by the supplement
    assert any("never added to CAD quantities" in s for s in model["status_lines"])
    assert model["groups"][0]["hardware"][0]["item_id"] == "pin-retainer" and len(model["joints"][0]["hardware"]) == 2
    assert "counted" not in model["inventory"][0] and model["inventory"][0]["on_hand_each"] is None and model["inventory"][0]["stock_text"] == ""


def test_model_rejects_stale_or_partial_receipt(rendered):
    project, renders, receipt = rendered
    bad = dict(receipt); bad["input_hashes"] = dict(receipt["input_hashes"]); bad["input_hashes"]["scene.json"] = "f" * 64
    with pytest.raises(document.DocumentError, match="different scene, assets or instructions"):
        document.build_model(project, bad)
    # a changed inventory or supplement (stock count, new row) does not stale the images
    ok = dict(receipt); ok["input_hashes"] = dict(receipt["input_hashes"]); ok["input_hashes"]["inventory.json"] = "e" * 64; ok["input_hashes"]["supplement.json"] = "d" * 64
    assert document.build_model(project, ok)["inventory"][1]["required"] == 2
    bad = dict(receipt); bad["partial"] = True
    with pytest.raises(document.DocumentError, match="partial"):
        document.build_model(project, bad)
    bad = dict(receipt); bad["views"] = [v for v in receipt["views"] if v["id"] != "part-pin"]
    with pytest.raises(document.DocumentError, match="no view 'part-pin'"):
        document.build_model(project, bad)
    bad = dict(receipt); bad["all_checks_passed"] = False
    with pytest.raises(document.DocumentError, match="failed checks"):
        document.build_model(project, bad)
    # a group view that does not show every occurrence under its assembly is refused
    bad = dict(receipt); bad["views"] = [dict(v, visible=["pin-a"]) if v["id"] == "group-pin-pair" else v for v in receipt["views"]]
    with pytest.raises(document.DocumentError, match="does not show every occurrence"):
        document.build_model(project, bad)
    bad = dict(receipt); bad["views"] = [dict(v, visible=["pin-a", "base-1"]) if v["id"] == "group-pin-pair" else v for v in receipt["views"]]
    with pytest.raises(document.DocumentError, match="is not under"):
        document.build_model(project, bad)
    # a joint view must list exactly the other occurrences of its context as context
    bad = dict(receipt); bad["views"] = [dict(v, context_occurrences=[]) if v["id"] == "joint-pin-to-base" else v for v in receipt["views"]]
    with pytest.raises(document.DocumentError, match="context does not list exactly"):
        document.build_model(project, bad)
    bad = dict(receipt); bad["views"] = [dict(v, context_assembly="pin-pair", context_occurrences=["pin-b"]) if v["id"] == "joint-pin-to-base" else v for v in receipt["views"]]
    with pytest.raises(document.DocumentError, match="are not under 'pin-pair'"):
        document.build_model(project, bad)


def test_html_and_typst_carry_the_same_content(rendered, tmp_path):
    project, renders, receipt = rendered
    out = tmp_path / "manual"
    model = document.build_model(project, receipt)
    document.stage_images(model, renders, out)
    text = html_out.render(model, out)
    assert text.count('class="step"') == 3
    assert 'data-part="pin" data-required="2"' in text
    assert "web-only" in text and "print-only" in text
    assert text.count("<svg class=\"callouts web-only\"") == 3      # overview, the subassembly view and the joint view
    assert 'data-group="pin-pair" data-index="1"' in text and 'data-gpart="pin" data-qty="2"' in text
    assert 'data-joint="pin_to_base" data-index="1"' in text and 'data-joint-occ="base-1"' in text
    assert 'class="pic long"' in text and "part-pin-end.png" in text
    assert "Technical appendix" not in text
    # supplementary rows: the existing-design rows in their table, the hardware lists under the group and the joint, no new-design row
    assert 'data-sitem="pin-retainer" data-scope="existing" data-status="candidate_requires_review"' in text and 'data-sitem="pin-spacer" data-scope="existing"' in text
    assert 'data-scope="new_design"' not in text and "pin-label" not in text
    assert text.count('data-sgroup="pin-pair"') == 2 and text.count('data-sjoint="joint-pin-to-base"') == 2
    assert "Hardware to review at this joint (not an approved BOM)" in text and "never added to CAD quantities" in text
    assert 'value=""' in text         # the paper count box is never prefilled from data
    typ = typst_out.render(model)
    assert typ.count("== Step ") == 3
    parts_section = typ.split("== Parts")[1].split("== Supplementary")[0]
    assert "CAD qty 2 each" in typ and "CAD qty 1 each" in typ and "required" not in parts_section
    assert "== Subassembly 1: pin-pair" in typ and "== Joint 1: pin\\_to\\_base" in typ
    assert "== Supplementary items (not modelled in CAD)" in typ and '#raw("pin-retainer")' in typ and '#raw("pin-spacer")' in typ and "pin-label" not in typ
    assert '#raw("pin_to_base")' in typ and "pin\\_to\\_base`" not in typ      # ids are set verbatim, never escaped inside raw text
    assert typ.count("Hardware to review at this joint") == 2
    assert "DRAFT" in typ
    assert "\\[insert-pin-a\\]" in typ
    assert typ.count("#pagebreak()") == 3   # before each step; weak breaks elsewhere
    assert "Technical appendix" not in typ
    # the appendix is opt-in and carries the full identities, the new-design rows and every supplement field
    model_a = document.build_model(project, receipt, appendix=True)
    text_a = html_out.render(model_a, out); typ_a = typst_out.render(model_a)
    assert "Technical appendix" in text_a and "pin-a; pin-b" in text_a and 'data-sitem-appendix="pin-label"' in text_a and "FIXTURE-SPACER-10" in text_a
    assert "== Technical appendix" in typ_a and "pin-a; pin-b" in typ_a and "pin-label" in typ_a and "FIXTURE-SPACER-10" in typ_a


def test_typst_escaping():
    assert typst_out.esc("a*b_c#d[e]@f") == "a\\*b\\_c\\#d\\[e\\]\\@f"


def test_checks_pass_on_consistent_output_without_pdf_tools(rendered, tmp_path, monkeypatch, capsys):
    project, renders, receipt = rendered
    out = tmp_path / "manual"
    args = SimpleNamespace(project_dir=str(project.dir), renders=str(renders), out=str(out), meshes=None, no_pdf=True, embed_images=False)
    assert document.build(args) == 0
    monkeypatch.setattr(checks.shutil, "which", lambda name: None)
    rc = checks.run(SimpleNamespace(out_dir=str(out), json=None))
    rep = json.loads((out / "check-report.json").read_text())
    statuses = {c["name"]: c["status"] for c in rep["checks"]}
    assert statuses["HTML inventory rows match manual.json"] == "passed"
    assert statuses["HTML step order matches manual.json"] == "passed"
    assert statuses["HTML subassembly sections match manual.json"] == "passed"
    assert statuses["manual.json: subassembly part quantities within CAD quantities"] == "passed"
    assert statuses["HTML joint sections match manual.json"] == "passed"
    assert statuses["HTML supplementary rows match manual.json"] == "passed"
    assert statuses["HTML per-group and per-joint hardware lists match manual.json"] == "passed"
    assert statuses["manual.json: supplementary rows are separate from CAD parts and keep unknown quantities unknown"] == "passed"
    assert statuses["HTML images resolve"] == "passed"
    assert statuses["HTML links resolve"] == "passed"
    assert statuses["PDF present"] == "failed"      # --no-pdf: honestly reported
    assert rc == 1


def test_checks_detect_tampered_html(rendered, tmp_path, monkeypatch):
    project, renders, receipt = rendered
    out = tmp_path / "manual"
    args = SimpleNamespace(project_dir=str(project.dir), renders=str(renders), out=str(out), meshes=None, no_pdf=True, embed_images=False)
    assert document.build(args) == 0
    html = (out / "index.html").read_text()
    (out / "index.html").write_text(html.replace('data-required="2"', 'data-required="3"').replace("images/part-pin.png", "images/missing.png").replace('data-gpart="pin" data-qty="2"', 'data-gpart="pin" data-qty="1"')
                                    .replace('data-sitem="pin-spacer" data-scope="existing"', 'data-sitem="pin-spacer" data-scope="new_design"').replace('data-sjoint="joint-pin-to-base" data-sitem="pin-retainer"', 'data-sjoint="joint-pin-to-base" data-sitem="pin-other"'))
    monkeypatch.setattr(checks.shutil, "which", lambda name: None)
    checks.run(SimpleNamespace(out_dir=str(out), json=None))
    rep = json.loads((out / "check-report.json").read_text())
    statuses = {c["name"]: c["status"] for c in rep["checks"]}
    assert statuses["HTML inventory rows match manual.json"] == "failed"
    assert statuses["HTML images resolve"] == "failed"
    assert statuses["HTML subassembly sections match manual.json"] == "failed"
    assert statuses["HTML supplementary rows match manual.json"] == "failed"
    assert statuses["HTML per-group and per-joint hardware lists match manual.json"] == "failed"


def test_embedded_images_are_data_uris(rendered, tmp_path):
    project, renders, receipt = rendered
    out = tmp_path / "manual"
    args = SimpleNamespace(project_dir=str(project.dir), renders=str(renders), out=str(out), meshes=None, no_pdf=True, embed_images=True)
    assert document.build(args) == 0
    text = (out / "index.html").read_text()
    assert "data:image/png;base64," in text and 'src="images/' not in text


@pytest.fixture
def rendered_inventory_only(project_copy, tmp_path):
    """A project without instructions and a matching receipt: thumbnails and overview only."""
    (project_copy.dir / "instructions.json").unlink()
    project = load_project(project_copy.dir)
    assert project.instructions is None
    renders = tmp_path / "renders"; (renders / "hotspots").mkdir(parents=True)
    views = []
    for vid, kind in (("part-base", "part-thumbnail"), ("part-pin", "part-thumbnail"), ("overview", "overview")):
        p = renders / f"{vid}.png"; png(p)
        views.append({"id": vid, "file": p.name, "sha256": receipts.sha256_file(p), "bytes": p.stat().st_size, "width": 8, "height": 6, "seconds": 0.1, "kind": kind})
    receipt = {"kind": "mechanical-docs-render-receipt", "blender": "test", "engine": "TEST", "denoiser": None, "preview": False, "samples": 1,
               "long_side_px": 8, "settings_sha256": "0" * 64, "input_hashes": project.input_hashes(), "views": views, "partial": False,
               "inventory_only": True, "all_checks_passed": True, "warnings": []}
    receipts.write_json(renders / "render-receipt.json", receipt)
    return project, renders, receipt


def test_inventory_only_document(rendered_inventory_only, tmp_path, monkeypatch):
    project, renders, receipt = rendered_inventory_only
    model = document.build_model(project, receipt)
    assert model["inventory_only"] is True and model["steps"] == []
    assert model["title"].endswith(": parts inventory") and model["id"] == "three-part-fixture-inventory"
    assert any("no assembly sequence" in line.lower() for line in model["status_lines"])
    assert [r["required"] for r in model["inventory"]] == [1, 2]
    out = tmp_path / "manual"
    args = SimpleNamespace(project_dir=str(project.dir), renders=str(renders), out=str(out), meshes=None, no_pdf=True, embed_images=False)
    assert document.build(args) == 0
    html = (out / "index.html").read_text()
    assert "No assembly sequence has been authored" in html and 'class="step"' not in html and 'class="group"' not in html
    assert model["supplement"]["by_group"] == {} and model["supplement"]["by_joint"] == {} and 'data-sitem="pin-retainer"' in html
    typ = (out / "manual.typ").read_text()
    assert "== Steps" in typ and "== Step 1" not in typ and "== Subassembly" not in typ
    monkeypatch.setattr(checks.shutil, "which", lambda name: None)
    checks.run(SimpleNamespace(out_dir=str(out), json=None))
    rep = json.loads((out / "check-report.json").read_text())
    statuses = {c["name"]: c["status"] for c in rep["checks"]}
    assert statuses["manual.json: parts needed over all steps equal required quantities"] == "not-run"
    assert statuses["HTML inventory rows match manual.json"] == "passed"
    assert statuses["HTML step order matches manual.json"] == "passed"


def test_dimensions_and_details_for_production_parts():
    from mechanical_docs.manifest import Asset, Part
    # overall size, longest first; inch equivalents only for an inch asset; whole millimetres from 100 mm
    assert document.dimensions_text({"extent": [28.375, 32.004, 80.0003]}) == "overall 80 × 32 × 28.4 mm"
    assert document.dimensions_text({"extent": [38.1, 38.1, 2438.4]}, "in") == "overall 2438 × 38.1 × 38.1 mm (96 × 1.5 × 1.5 in)"
    assert document.dimensions_text({"extent": [1193.8, 3.175, 1193.8]}, "in") == "overall 1194 × 1194 × 3.2 mm (47 × 47 × 0.125 in)"
    assert document.dimensions_text({"extent": [38.1, 38.1, 2438.4]}, "mm") == "overall 2438 × 38.1 × 38.1 mm"
    part = Part("x", "MCMASTER 5537T293_T-Slotted Framing", Asset("a", "step", "in", "0" * 64, __import__("pathlib").Path()), {}, "",
                model_state="[Primary]", bodies={"surface_bodies": 9, "solid_bodies": 9, "visible_solid_bodies": 9},
                properties={"part_number": "5537T293", "material": "Zinc", "vendor": "", "manufacturer": None}, bom_structure_default="Purchased")
    assert document.part_details(part) == "P/N 5537T293 · Zinc · 9 bodies · BOM Purchased"     # model state goes to the appendix
    assert document.display_name(part) == "MCMASTER 5537T293 T-Slotted Framing"
    assert document.part_details(Part("y", "Y", Asset("a", "step", "mm", "0" * 64, __import__("pathlib").Path()))) == ""


def test_coincident_finding_reaches_both_outputs(project_copy, tmp_path):
    """The coincident-pose finding is printed on the status block and the part's card, and the count is unchanged."""
    project_copy.edit("scene.json", lambda d: d["occurrences"][2].__setitem__("transform", d["occurrences"][1]["transform"]))
    (project_copy.dir / "instructions.json").unlink()
    project = load_project(project_copy.dir)
    renders = tmp_path / "renders"; (renders / "hotspots").mkdir(parents=True)
    views = []
    for vid, kind in (("part-base", "part-thumbnail"), ("part-pin", "part-thumbnail"), ("overview", "overview")):
        p = renders / f"{vid}.png"; png(p)
        views.append({"id": vid, "file": p.name, "sha256": receipts.sha256_file(p), "bytes": p.stat().st_size, "width": 8, "height": 6, "seconds": 0.1, "kind": kind})
    receipt = {"kind": "mechanical-docs-render-receipt", "blender": "test", "engine": "TEST", "denoiser": None, "preview": False, "samples": 1,
               "long_side_px": 8, "settings_sha256": "0" * 64, "input_hashes": project.input_hashes(), "views": views, "partial": False,
               "all_checks_passed": True, "warnings": []}
    model = document.build_model(project, receipt)
    assert model["inventory"][1]["required"] == 2 and "coincident instance pair" in model["inventory"][1]["review_note"]
    assert model["inventory"][0]["review_note"] == ""
    assert any(line.startswith("CAD ambiguity") and "Pin" in line for line in model["status_lines"])
    assert model["findings"]["coincident_occurrences"][0]["occurrences"] == ["pin-a", "pin-b"]
    out = tmp_path / "manual"; document.stage_images(model, renders, out)
    assert "review before counting as stock" in html_out.render(model, out)
    assert "review before counting as stock" in typst_out.render(model)


def test_stock_record_and_configuration_flag_reach_the_card(project_copy, tmp_path):
    """on_hand_each prints as recorded stock (never as the paper box), the explicit
    configuration flag prints beside the coincident finding without deriving from it."""
    def f(d):
        d["items"][1].update({"on_hand_each": 0, "counted_by": "fixture author", "counted_date": "2026-10-22", "intended_configuration_confirmed": False})
        del d["items"][1]["counted"]
    project_copy.edit("inventory.json", f)
    project_copy.edit("scene.json", lambda d: d["occurrences"][2].__setitem__("transform", d["occurrences"][1]["transform"]))
    (project_copy.dir / "instructions.json").unlink()
    project = load_project(project_copy.dir)
    renders = tmp_path / "renders"; (renders / "hotspots").mkdir(parents=True)
    views = []
    for vid, kind in (("part-base", "part-thumbnail"), ("part-pin", "part-thumbnail"), ("overview", "overview")):
        p = renders / f"{vid}.png"; png(p)
        views.append({"id": vid, "file": p.name, "sha256": receipts.sha256_file(p), "bytes": p.stat().st_size, "width": 8, "height": 6, "seconds": 0.1, "kind": kind})
    receipt = {"kind": "mechanical-docs-render-receipt", "blender": "test", "engine": "TEST", "denoiser": None, "preview": False, "samples": 1,
               "long_side_px": 8, "settings_sha256": "0" * 64, "input_hashes": project.input_hashes(), "views": views, "partial": False,
               "all_checks_passed": True, "warnings": []}
    model = document.build_model(project, receipt)
    pin = model["inventory"][1]
    assert pin["required"] == 2 and pin["on_hand_each"] == 0 and pin["stock_text"] == "on hand 0 (counted 2026-10-22 by fixture author)"
    assert pin["intended_configuration_confirmed"] is False and "coincident" in pin["review_note"]
    assert model["inventory"][0]["intended_configuration_confirmed"] is None and model["inventory"][0]["stock_text"] == ""
    assert any(line.startswith("Recorded stock: 1 of 2 parts") for line in model["status_lines"])
    out = tmp_path / "manual"; document.stage_images(model, renders, out)
    html = html_out.render(model, out); typ = typst_out.render(model)
    for text in (html, typ):
        assert "on hand 0 (counted 2026-10-22 by fixture author)" in text and "intended configuration confirmed: no" in text and "review before counting as stock" in text
    assert 'value="0"' not in html          # the paper box stays blank; stock is text, not the box
