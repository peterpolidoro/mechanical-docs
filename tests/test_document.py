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
    view_ids = ["part-base", "part-pin", "overview", "step-01-place-base", "step-02-insert-pin-a", "step-02-insert-pin-a-result",
                "step-03-insert-pin-b", "step-03-insert-pin-b-result"]
    views = []
    for vid in view_ids:
        p = renders / f"{vid}.png"; png(p)
        kind = "part-thumbnail" if vid.startswith("part-") else "overview" if vid == "overview" else "step-result" if vid.endswith("-result") else "step"
        views.append({"id": vid, "file": p.name, "sha256": receipts.sha256_file(p), "bytes": p.stat().st_size, "width": 8, "height": 6, "seconds": 0.1, "kind": kind})
    (renders / "hotspots" / "overview.json").write_text(json.dumps({"view": "overview", "width": 8, "height": 6, "occurrences": [
        {"id": "base-1", "part_id": "base", "box_px": [0, 0, 8, 6], "corners_in_frame": 8},
        {"id": "pin-a", "part_id": "pin", "box_px": [1, 1, 3, 3], "corners_in_frame": 8}]}))
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
    assert model["inventory"][0]["dimensions"] == "100 × 60 × 8 mm, hole Ø10.5 mm"
    assert model["inventory"][1]["dimensions"] == "Ø10 × 30 mm"


def test_model_rejects_stale_or_partial_receipt(rendered):
    project, renders, receipt = rendered
    bad = dict(receipt); bad["input_hashes"] = dict(receipt["input_hashes"]); bad["input_hashes"]["scene.json"] = "f" * 64
    with pytest.raises(document.DocumentError, match="different inputs"):
        document.build_model(project, bad)
    bad = dict(receipt); bad["partial"] = True
    with pytest.raises(document.DocumentError, match="partial"):
        document.build_model(project, bad)
    bad = dict(receipt); bad["views"] = [v for v in receipt["views"] if v["id"] != "part-pin"]
    with pytest.raises(document.DocumentError, match="no view 'part-pin'"):
        document.build_model(project, bad)
    bad = dict(receipt); bad["all_checks_passed"] = False
    with pytest.raises(document.DocumentError, match="failed checks"):
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
    assert "<svg class=\"callouts web-only\"" in text
    typ = typst_out.render(model)
    assert typ.count("== Step ") == 3
    assert "required 2 each" in typ and "required 1 each" in typ
    assert "DRAFT" in typ
    assert "\\[insert-pin-a\\]" in typ
    assert typ.count("#pagebreak()") == 4   # before each step and before the record


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
    (out / "index.html").write_text(html.replace('data-required="2"', 'data-required="3"').replace("images/part-pin.png", "images/missing.png"))
    monkeypatch.setattr(checks.shutil, "which", lambda name: None)
    checks.run(SimpleNamespace(out_dir=str(out), json=None))
    rep = json.loads((out / "check-report.json").read_text())
    statuses = {c["name"]: c["status"] for c in rep["checks"]}
    assert statuses["HTML inventory rows match manual.json"] == "failed"
    assert statuses["HTML images resolve"] == "failed"


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
    assert "No assembly sequence has been authored" in html and 'class="step"' not in html
    typ = (out / "manual.typ").read_text()
    assert "== Steps" in typ and "#pagebreak()" in typ and "== Step 1" not in typ
    monkeypatch.setattr(checks.shutil, "which", lambda name: None)
    checks.run(SimpleNamespace(out_dir=str(out), json=None))
    rep = json.loads((out / "check-report.json").read_text())
    statuses = {c["name"]: c["status"] for c in rep["checks"]}
    assert statuses["manual.json: parts needed over all steps equal required quantities"] == "not-run"
    assert statuses["HTML inventory rows match manual.json"] == "passed"
    assert statuses["HTML step order matches manual.json"] == "passed"


def test_dimensions_and_details_for_production_parts():
    from mechanical_docs.manifest import Asset, Part
    assert document.dimensions_text({"extent": [28.375, 32.004, 80.0003]}) == "extent 28.4 × 32 × 80 mm"
    part = Part("x", "X", Asset("a", "step", "in", "0" * 64, __import__("pathlib").Path()), {}, "",
                model_state="[Primary]", bodies={"surface_bodies": 9, "solid_bodies": 9, "visible_solid_bodies": 9},
                properties={"part_number": "5537T293", "material": "Zinc", "vendor": "", "manufacturer": None}, bom_structure_default="Purchased")
    assert document.part_details(part) == "P/N 5537T293 · Zinc · [Primary] · 9 bodies · BOM Purchased"
    assert document.part_details(Part("y", "Y", Asset("a", "step", "mm", "0" * 64, __import__("pathlib").Path()))) == ""
