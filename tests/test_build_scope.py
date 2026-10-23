"""build-scope.json: one build phase scoping what the documents print (pure Python)."""
import json
from types import SimpleNamespace

import pytest

from mechanical_docs import checks, document, html as html_out, typst as typst_out
from mechanical_docs.manifest import ManifestError, load_project
from mechanical_docs.procedure import derive_states
from mechanical_docs.reuse import stale_reason
from tests.test_document import rendered  # noqa: F401  (fixture: a complete synthetic receipt)


def test_fixture_scope_loads_and_classifies(fixture_dir):
    pr = load_project(fixture_dir)
    bs = pr.build_scope
    assert bs is not None and bs.phase == "fixture-phase-1" and bs.review_state == "draft" and bs.deferred_occurrence_ids == ["pin-b"]
    assert bs.deferred_ids(pr.scene) == ["pin-b"] and bs.conditional_ids(pr.scene) == []
    assert {o: bs.classify(pr.scene, o) for o in pr.scene.occurrences} == {"base-1": "build", "pin-a": "build", "pin-b": "deferred"}
    assert bs.part_quantities(pr.scene) == {"base": {"cad": 1, "this_build": 1, "conditional": 0, "deferred": 0}, "pin": {"cad": 2, "this_build": 1, "conditional": 0, "deferred": 1}}
    assert "build-scope.json" in pr.input_hashes() and "build-scope.json" in pr.non_render_inputs()
    # the last step adds only the deferred pin: a deferred step, shown seated but not accumulated
    states = derive_states(pr.instructions, pr.scene, bs.deferred_ids(pr.scene))
    assert [st.deferred for st in states] == [False, False, True]
    assert states[2].before == ["base-1", "pin-a"] and states[2].after == ["base-1", "pin-a", "pin-b"] and states[2].hidden == []


def test_scope_validation(project_copy):
    def scope(**over):
        d = {"schema_version": 1, "scene": "scene.json", "phase": "p1", "title": "T", "decided_by": "x", "review_state": "draft",
             "deferred_occurrence_ids": [], "conditional_groups": [], "backlight": "n/a", "deferred_design": [], "note": "n"}
        d.update(over)
        (project_copy.dir / "build-scope.json").write_text(json.dumps(d))
        return load_project(project_copy.dir)
    assert scope().build_scope.deferred_occurrence_ids == []
    for bad, msg in ((dict(schema_version="draft-1"), "schema_version must be 1"), (dict(extra=1), "unsupported field"),
                     (dict(deferred_occurrence_ids=["nowhere"]), "unknown occurrence 'nowhere'"), (dict(deferred_occurrence_ids=["pin-pair"]), "an assembly id"),
                     (dict(deferred_occurrence_ids=["pin-a", "pin-a"]), "listed twice"), (dict(conditional_groups=[{"id": "root", "rule": "r", "decided": None}]), "non-root assembly"),
                     (dict(conditional_groups=[{"id": "pin-pair", "rule": "r"}]), "missing field 'decided'"), (dict(conditional_groups=[{"id": "pin-pair", "rule": "r", "decided": "no"}]), "true, false or null"),
                     (dict(conditional_groups=[{"id": "pin-pair", "rule": "", "decided": None}]), "non-empty sentence"), (dict(phase="phase 1"), "identifier"),
                     (dict(review_state="final"), "review_state"), (dict(scene="other.json"), "does not name the loaded scene"), (dict(deferred_design="x"), "list of strings")):
        with pytest.raises(ManifestError, match=msg):
            scope(**bad)
    del_ = {"schema_version": 1, "scene": "scene.json", "phase": "p1", "title": "T", "decided_by": "x", "review_state": "draft",
            "deferred_occurrence_ids": [], "conditional_groups": [], "backlight": "n/a", "deferred_design": []}
    (project_copy.dir / "build-scope.json").write_text(json.dumps(del_))
    with pytest.raises(ManifestError, match="missing field 'note'"):
        load_project(project_copy.dir)
    # the recipe's path within its own repository is accepted when the file name is the scene's
    assert scope(scene="references/enclosure/scene.json").build_scope is not None
    # a conditional group decided against defers its members; undecided makes them conditional
    pr = scope(conditional_groups=[{"id": "pin-pair", "rule": "only if needed", "decided": False}])
    assert pr.build_scope.deferred_ids(pr.scene) == ["pin-a", "pin-b"] and pr.build_scope.part_quantities(pr.scene)["pin"]["deferred"] == 2
    pr = scope(conditional_groups=[{"id": "pin-pair", "rule": "only if needed", "decided": None}], deferred_occurrence_ids=["pin-b"])
    assert pr.build_scope.conditional_ids(pr.scene) == ["pin-a"] and pr.build_scope.part_quantities(pr.scene)["pin"] == {"cad": 2, "this_build": 0, "conditional": 1, "deferred": 1}
    assert pr.build_scope.conditional_group_of(pr.scene, "pin-a").rule == "only if needed"


def test_deferred_step_in_the_middle_is_not_accumulated(fixture_dir):
    pr = load_project(fixture_dir)
    states = derive_states(pr.instructions, pr.scene, ["pin-a"])     # the second step becomes deferred
    assert [st.deferred for st in states] == [False, True, False]
    assert states[1].before == ["base-1"] and states[1].after == ["base-1", "pin-a"]
    assert states[2].before == ["base-1"] and states[2].after == ["base-1", "pin-b"] and states[2].hidden == ["pin-a"]
    # every occurrence is still placed exactly once
    assert sorted(o for st in states for o in st.added) == ["base-1", "pin-a", "pin-b"]


def test_reuse_detects_changed_step_states_and_instructions():
    old = {"id": "step-02-insert-pin-a", "kind": "step", "highlighted": ["pin-a"], "subdued": ["base-1"], "lines": True, "visible_triangles": 10}
    same = {"step-02-insert-pin-a": (["pin-a"], ["base-1"])}
    assert stale_reason(old, {}, True, 1000, None, False, same) is None
    assert stale_reason(old, {}, True, 1000, None, False, {"step-02-insert-pin-a": (["pin-a"], [])}) == "step state changed (additions or installed-before differ, e.g. a build scope)"
    assert stale_reason(old, {}, True, 1000, None, False, {}) == "step no longer in the procedure"
    assert stale_reason(old, {}, True, 1000, None, True, same) == "instructions changed"
    ov = {"id": "overview", "kind": "overview", "lines": False, "visible_triangles": 10}
    assert stale_reason(ov, {}, True, 5, None, True) == "instructions changed (the overview uses the first step's camera)"
    assert stale_reason(ov, {}, True, 5, None, False) is None
    thumb = {"id": "part-base", "kind": "part-thumbnail", "lines": True, "visible_triangles": 10}
    assert stale_reason(thumb, {}, True, 5, None, True) is None      # thumbnails do not follow the instructions


def test_scoped_document_prints_phase_quantities_checklist_and_chapters(rendered, tmp_path):  # noqa: F811
    project, renders, receipt = rendered
    model = document.build_model(project, receipt)
    bs = model["build_scope"]
    assert bs["phase"] == "fixture-phase-1" and bs["totals"] == {"cad": 3, "this_build": 2, "conditional": 0, "deferred": 1} and bs["parts_deferred"] == []
    assert [(r["part_id"], r["this_build"], r["deferred"], r["scope_kind"]) for r in model["inventory"]] == [("base", 1, 0, "build"), ("pin", 1, 1, "build")]
    assert [(s["id"], s["index"], s["kind"]) for s in model["steps"]] == [("place-base", 1, "build"), ("insert-pin-a", 2, "build"), ("insert-pin-b", 3, "deferred")]
    assert bs["deferred_steps"] == ["insert-pin-b"] and [c["part_id"] for c in bs["checklist"]] == ["base", "pin"]
    assert any(s.startswith("Build scope fixture-phase-1") and "2 of 3 installed occurrences are in this build, 1 deferred" in s for s in model["status_lines"])
    assert any(s.startswith("Phase note:") for s in model["status_lines"])
    out = tmp_path / "manual"; document.stage_images(model, renders, out)
    html = html_out.render(model, out); typ = typst_out.render(model)
    assert 'data-this-build="1" data-scope-kind="build"' in html and 'id="checklist"' in html and 'id="deferred-steps"' in html and 'data-kind="deferred"' in html
    assert "this build 1 \\ CAD qty 2 each · deferred 1" in typ and "== Verification checklist: fixture-phase-1" in typ and "= Deferred steps (not in this build)" in typ
    assert "DEFERRED: not in this build" in typ and "== Deferred (not in this build)" not in typ      # no part is deferred entirely here
    # a receipt whose step was rendered under a different installed-before set is refused
    bad = dict(receipt, views=[dict(v, highlighted=["pin-b"], subdued=["base-1"]) if v["id"] == "step-03-insert-pin-b" else v for v in receipt["views"]])
    with pytest.raises(document.DocumentError, match="different installed-before set"):
        document.build_model(project, bad)


def test_conditional_and_entirely_deferred_parts(project_copy, tmp_path, monkeypatch):
    """A conditional group makes its steps conditional; a part with nothing in this build moves to the deferred section and the checklist still lists it."""
    scope = json.loads((project_copy.dir / "build-scope.json").read_text())
    scope["conditional_groups"] = [{"id": "pin-pair", "rule": "install the pins only if the base will not be re-machined", "decided": None}]
    scope["deferred_occurrence_ids"] = []
    (project_copy.dir / "build-scope.json").write_text(json.dumps(scope))
    project = load_project(project_copy.dir)
    from tests.test_document import png, receipts
    renders = tmp_path / "renders"; (renders / "hotspots").mkdir(parents=True)
    views = []
    for vid, kind in (("part-base", "part-thumbnail"), ("part-pin", "part-thumbnail"), ("overview", "overview"), ("step-01-place-base", "step"),
                      ("step-02-insert-pin-a", "step"), ("step-02-insert-pin-a-result", "step-result"), ("step-03-insert-pin-b", "step"), ("step-03-insert-pin-b-result", "step-result")):
        p = renders / f"{vid}.png"; png(p)
        views.append({"id": vid, "file": p.name, "sha256": receipts.sha256_file(p), "bytes": p.stat().st_size, "width": 8, "height": 6, "seconds": 0.1, "kind": kind})
    receipt = {"kind": "mechanical-docs-render-receipt", "blender": "test", "engine": "TEST", "denoiser": None, "preview": False, "samples": 1,
               "long_side_px": 8, "settings_sha256": "0" * 64, "input_hashes": project.input_hashes(), "views": views, "partial": False, "all_checks_passed": True, "warnings": []}
    receipts.write_json(renders / "render-receipt.json", receipt)
    model = document.build_model(project, receipt)
    assert [(s["id"], s["kind"], s["rule"]) for s in model["steps"]] == [("place-base", "build", None), ("insert-pin-a", "conditional", "install the pins only if the base will not be re-machined"),
                                                                        ("insert-pin-b", "conditional", "install the pins only if the base will not be re-machined")]
    assert [(r["part_id"], r["this_build"], r["conditional"], r["scope_kind"]) for r in model["inventory"]] == [("base", 1, 0, "build"), ("pin", 0, 2, "conditional")]
    # defer the whole pin pair instead: the pin's card moves to the deferred section (last), the base keeps label 1
    scope["conditional_groups"][0]["decided"] = False
    (project_copy.dir / "build-scope.json").write_text(json.dumps(scope))
    project = load_project(project_copy.dir)
    receipt["input_hashes"] = project.input_hashes(); receipts.write_json(renders / "render-receipt.json", receipt)
    model = document.build_model(project, receipt)
    assert [(r["part_id"], r["label"], r["scope_kind"]) for r in model["inventory"]] == [("base", 1, "build"), ("pin", 2, "deferred")] and model["build_scope"]["parts_deferred"] == ["pin"]
    assert [(s["id"], s["kind"]) for s in model["steps"]] == [("place-base", "build"), ("insert-pin-a", "deferred"), ("insert-pin-b", "deferred")]
    out = tmp_path / "manual"
    args = SimpleNamespace(project_dir=str(project.dir), renders=str(renders), out=str(out), meshes=None, no_pdf=True, embed_images=False)
    assert document.build(args) == 0
    html = (out / "index.html").read_text(); typ = (out / "manual.typ").read_text()
    assert 'id="deferred-parts"' in html and "== Deferred (not in this build)" in typ and typ.count("DEFERRED: not in this build") == 2
    monkeypatch.setattr(checks.shutil, "which", lambda name: None)
    checks.run(SimpleNamespace(out_dir=str(out), json=None))
    statuses = {c["name"]: c["status"] for c in json.loads((out / "check-report.json").read_text())["checks"]}
    assert statuses["manual.json: build-scope quantities partition the CAD counts, checklist and step chapters agree"] == "passed"
    assert statuses["HTML this-build quantities, checklist and step kinds match manual.json"] == "passed"
    assert statuses["HTML inventory rows match manual.json"] == "passed" and statuses["HTML step order matches manual.json"] == "passed"
