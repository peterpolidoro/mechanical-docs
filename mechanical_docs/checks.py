"""Verify a built manual: HTML, PDF and manual.json agree; links and images resolve.

    python3 -m mechanical_docs check OUT_DIR [--json REPORT]

Reads OUT_DIR/manual.json as the reference, parses index.html for inventory
cards (part, CAD quantity), subassembly sections (group, parts, quantities),
joint sections, supplementary rows and the per-group/per-joint hardware lists,
step order and every image/link target, and reads the PDF back with pdftotext
(Poppler, content order) for the `Step N`, `Subassembly N`, `Joint N`,
`[step-id]` and `CAD qty N` tokens and the printed supplementary item ids. Rasterises the PDF pages (pdftoppm) and writes greyscale
copies of the step images (ImageMagick) under OUT_DIR/checks/ for inspection.
Each check is reported as passed, failed or not run; the exit status is 1 if
any check failed.
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
from html.parser import HTMLParser
from pathlib import Path

from . import receipts


class _Html(HTMLParser):
    def __init__(self):
        super().__init__()
        self.inventory = []     # (part, required, label)
        self.this_build = []    # (part, this-build qty) on scoped cards
        self.step_kinds = []    # (step id, kind)
        self.checklist = []     # (part, this-build qty) in the verification checklist
        self.steps = []         # (id, index)
        self.needed = []        # (step id, part, qty)
        self.groups = []        # (group id, index)
        self.group_instances = []   # (group id, instance count, identical)
        self.group_parts = []   # (group id, part, qty)
        self.joints = []        # (joint id, index)
        self.sup_rows = []      # (item id, scope, status) in the supplementary table
        self.callouts = []      # (number, group id) in the exploded view's key
        self.hardware = []      # (kind, group/joint key, item id) from the per-group and per-joint lists
        self.images = []
        self.links = []
        self.ids = set()
        self._step = None
        self._group = None

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if "id" in a:
            self.ids.add(a["id"])
        if "data-part" in a and "data-required" in a:
            self.inventory.append((a["data-part"], int(a["data-required"]), int(a.get("data-label", 0))))
            if "data-this-build" in a:
                self.this_build.append((a["data-part"], int(a["data-this-build"])))
        if tag == "tr" and "data-check-part" in a:
            self.checklist.append((a["data-check-part"], int(a["data-this-build"])))
        if tag == "section" and "data-step" in a:
            self._step = a["data-step"]
            self.steps.append((a["data-step"], int(a["data-index"])))
            self.step_kinds.append((a["data-step"], a.get("data-kind", "build")))
        if tag == "section" and "data-group" in a:
            self._group = a["data-group"]
            self.groups.append((a["data-group"], int(a["data-index"])))
            if "data-instance-count" in a:
                self.group_instances.append((a["data-group"], int(a["data-instance-count"]), a.get("data-identical") == "true"))
        if tag == "tr" and "data-gpart" in a and self._group:
            self.group_parts.append((self._group, a["data-gpart"], int(a["data-qty"])))
        if tag == "section" and "data-joint" in a:
            self.joints.append((a["data-joint"], int(a["data-index"])))
        if tag == "tr" and "data-callout" in a:
            self.callouts.append((int(a["data-callout"]), a.get("data-callout-target")))
        if tag == "tr" and "data-sitem" in a and "data-scope" in a:
            self.sup_rows.append((a["data-sitem"], a["data-scope"], a.get("data-status")))
        if tag == "li" and "data-sgroup" in a:
            self.hardware.append(("group", a["data-sgroup"], a["data-sitem"]))
        if tag == "li" and "data-sjoint" in a:
            self.hardware.append(("joint", a["data-sjoint"], a["data-sitem"]))
        if tag == "div" and "data-qty" in a and self._step:
            self.needed.append((self._step, a["data-part"], int(a["data-qty"])))
        if tag == "img" and "src" in a:
            self.images.append(a["src"])
        if tag == "a" and "href" in a:
            self.links.append(a["href"])

    def handle_endtag(self, tag):
        if tag == "section":
            self._step = None
            self._group = None


def run_cmd(cmd, **kw):
    return subprocess.run(cmd, capture_output=True, text=True, **kw)


def run(args):
    out = Path(args.out_dir)
    report = {"kind": "mechanical-docs-check-report", "generated_at_utc": receipts.utc_now(), "out_dir": str(out), "checks": []}
    failed = False

    def check(name, status, detail=None):
        nonlocal failed
        report["checks"].append({"name": name, "status": status, **({"detail": detail} if detail is not None else {})})
        if status == "failed":
            failed = True
        print(f"[check] {status:8s} {name}" + (f": {detail}" if detail is not None and status != "passed" else ""))

    model = receipts.read_json(out / "manual.json")
    ref_inv = [(r["part_id"], r["required"], r["label"]) for r in model["inventory"]]
    ref_steps = [(s["id"], s["index"]) for s in model["steps"]]
    ref_needed = [(s["id"], n["part_id"], n["qty"]) for s in model["steps"] for n in s["parts_needed"]]
    ref_groups = [(g["id"], g["index"]) for g in model.get("groups", [])]
    ref_gparts = [(g["id"], p["part_id"], p["qty"]) for g in model.get("groups", []) for p in g["parts"]]
    ref_joints = [(j["joint_id"], j["index"]) for j in model.get("joints", [])]
    ref_ginst = [(g["id"], g["instance_count"], g["instances_identical"]) for g in model.get("groups", []) if "instance_count" in g]
    sup = model.get("supplement") or {"present": False, "rows": [], "existing": [], "new_design": [], "by_group": {}, "by_joint": {}}
    scope = model.get("build_scope")
    ref_this = [(r["part_id"], r["this_build"]) for r in model["inventory"]] if scope else []
    ref_kinds = [(s["id"], s.get("kind", "build")) for s in model["steps"]]
    exploded = model.get("exploded_view")
    ref_callouts = [(c["number"], c["group_id"]) for c in (exploded or {}).get("callouts", [])]
    ref_sup = [(r["item_id"], r["scope"], r["status"]) for r in sup["rows"] if not r["appendix_only"]]
    ref_hw = [("group", g, i) for g, items in sup["by_group"].items() for i in items] + [("joint", j, i) for j, items in sup["by_joint"].items() for i in items]
    # a subassembly's part quantities can never exceed the whole scene's
    over = [(g, p, q) for g, p, q in ref_gparts if q > dict((r["part_id"], r["required"]) for r in model["inventory"]).get(p, 0)]
    if ref_groups:
        check("manual.json: subassembly part quantities within CAD quantities", "passed" if not over else "failed", over or f"{len(ref_groups)} subassemblies")
    # manual.json internal consistency: parts needed over all steps equal required quantities
    totals = {}
    for _, pid, q in ref_needed:
        totals[pid] = totals.get(pid, 0) + q
    if ref_steps:
        check("manual.json: parts needed over all steps equal required quantities",
              "passed" if totals == {p: r for p, r, _ in ref_inv} else "failed", {"needed": totals, "required": {p: r for p, r, _ in ref_inv}})
    else:
        check("manual.json: parts needed over all steps equal required quantities", "not-run", "no steps: inventory-only document")
    check("manual.json: step indices are 1..N in order", "passed" if [i for _, i in ref_steps] == list(range(1, len(ref_steps) + 1)) else "failed")
    if scope:
        # the phase quantities partition the CAD count, the checklist lists every part in card order, deferred steps come last
        bad = [r["part_id"] for r in model["inventory"] if r["this_build"] + r["conditional"] + r["deferred"] != r["required"]]
        order_ok = [c["part_id"] for c in scope["checklist"]] == [r["part_id"] for r in model["inventory"]]
        kinds = [s.get("kind") for s in model["steps"]]
        deferred_last = kinds == [k for k in kinds if k != "deferred"] + [k for k in kinds if k == "deferred"]
        check("manual.json: build-scope quantities partition the CAD counts, checklist and step chapters agree", "passed" if not bad and order_ok and deferred_last else "failed",
              {"parts not partitioned": bad, "checklist order": order_ok, "deferred steps last": deferred_last} if bad or not order_ok or not deferred_last
              else f"{scope['totals']} ; {len(scope['parts_deferred'])} part(s) deferred entirely, {len(scope['deferred_steps'])} deferred step(s), {len(scope['conditional_steps'])} conditional")
    if sup["present"]:
        # supplementary quantities are their own list: none is a CAD part row, and every printed row keeps null as unknown
        cad_ids = {r["part_id"] for r in model["inventory"]}
        mixed = [r["item_id"] for r in sup["rows"] if r["item_id"] in cad_ids]
        coerced = [r["item_id"] for r in sup["rows"] if any(r[k] == 0 and "unknown" in r["required_text" if k == "confirmed_required_each" else "stock_text"]
                                                          for k in ("confirmed_required_each", "on_hand_each"))]
        check("manual.json: supplementary rows are separate from CAD parts and keep unknown quantities unknown", "passed" if not mixed and not coerced else "failed",
              {"item ids colliding with part ids": mixed, "zero printed as unknown": coerced} if mixed or coerced else f"{len(sup['rows'])} rows, {len(ref_sup)} printed, {len(sup['new_design'])} appendix-only")

    # HTML
    html_path = out / "index.html"
    p = _Html(); p.feed(html_path.read_text(encoding="utf-8"))
    check("HTML inventory rows match manual.json", "passed" if p.inventory == ref_inv else "failed", {"html": p.inventory, "ref": ref_inv})
    check("HTML step order matches manual.json", "passed" if p.steps == ref_steps else "failed", {"html": p.steps, "ref": ref_steps})
    if scope:
        check("HTML this-build quantities, checklist and step kinds match manual.json", "passed" if p.this_build == ref_this and p.checklist == ref_this and p.step_kinds == ref_kinds else "failed",
              {"cards": p.this_build, "checklist": p.checklist, "kinds": p.step_kinds, "ref": ref_this, "ref kinds": ref_kinds})
    check("HTML parts-needed per step match manual.json", "passed" if p.needed == ref_needed else "failed", {"html": p.needed, "ref": ref_needed})
    check("HTML subassembly sections match manual.json", "passed" if p.groups == ref_groups and p.group_parts == ref_gparts else "failed",
          {"html": [p.groups, p.group_parts], "ref": [ref_groups, ref_gparts]})
    check("HTML joint sections match manual.json", "passed" if p.joints == ref_joints else "failed", {"html": p.joints, "ref": ref_joints})
    if ref_ginst:
        check("HTML subassembly instance counts match manual.json", "passed" if p.group_instances == ref_ginst else "failed", {"html": p.group_instances, "ref": ref_ginst})
    if exploded:
        check("HTML exploded-view callouts match manual.json", "passed" if p.callouts == ref_callouts else "failed", {"html": p.callouts, "ref": ref_callouts})
    if sup["present"]:
        check("HTML supplementary rows match manual.json", "passed" if p.sup_rows == ref_sup else "failed", {"html": p.sup_rows, "ref": ref_sup})
        check("HTML per-group and per-joint hardware lists match manual.json", "passed" if sorted(p.hardware) == sorted(ref_hw) else "failed", {"html": p.hardware, "ref": ref_hw})
    missing_imgs = [s for s in p.images if not s.startswith("data:") and not (out / s).is_file()]
    check("HTML images resolve", "passed" if not missing_imgs else "failed", missing_imgs or f"{len(p.images)} images")
    bad_links = []
    for href in p.links:
        if href.startswith("#"):
            if href[1:] not in p.ids:
                bad_links.append(href)
        elif "://" not in href and not (out / href).exists():
            bad_links.append(href)
    check("HTML links resolve", "passed" if not bad_links else "failed", bad_links or f"{len(p.links)} links")
    check("HTML marks web-only extras", "passed" if 'class="web-only' in html_path.read_text(encoding="utf-8") or "web-only" in html_path.read_text(encoding="utf-8") else "failed")

    # PDF
    pdfs = sorted(out.glob("*.pdf"))
    pdftotext = shutil.which("pdftotext"); pdfinfo = shutil.which("pdfinfo"); pdftoppm = shutil.which("pdftoppm"); pdfimages = shutil.which("pdfimages")
    if not pdfs:
        check("PDF present", "failed", "no PDF in output directory")
    elif not pdftotext:
        check("PDF text agrees with manual.json", "not-run", "pdftotext not on PATH (Poppler)")
    else:
        pdf = pdfs[0]
        # content order (one card, one cell at a time); -layout interleaves the grid's columns line by line
        text = run_cmd([pdftotext, "-raw", str(pdf), "-"]).stdout
        steps_in_pdf = [int(m) for m in re.findall(r"^\s*Step (\d+)\s*$", text, re.M)]
        ids_in_pdf = re.findall(r"\[([a-z0-9][a-z0-9._-]*)\]", text)
        ids_in_pdf = [i for i in ids_in_pdf if i in {s for s, _ in ref_steps}]
        check("PDF step headings are 1..N in order", "passed" if steps_in_pdf == [i for _, i in ref_steps] else "failed", {"pdf": steps_in_pdf, "ref": [i for _, i in ref_steps]})
        check("PDF step ids in manual.json order", "passed" if ids_in_pdf == [s for s, _ in ref_steps] else "failed", {"pdf": ids_in_pdf, "ref": [s for s, _ in ref_steps]})
        req_in_pdf = [int(m) for m in re.findall(r"CAD qty (\d+)\b", text)]       # the small text may wrap right after the number
        check("PDF CAD quantities match manual.json", "passed" if req_in_pdf == [r for _, r, _ in ref_inv] else "failed", {"pdf": req_in_pdf, "ref": [r for _, r, _ in ref_inv]})
        if scope:
            this_in_pdf = [int(m) for m in re.findall(r"this build (\d+)\b", text)]
            headings = ("Verification checklist" in text) and (("Deferred steps (not in this build)" in text) == bool(scope["deferred_steps"])) and (("Deferred (not in this build)" in text) == bool(scope["parts_deferred"]))
            check("PDF this-build quantities, checklist page and deferred chapters match manual.json", "passed" if this_in_pdf == [q for _, q in ref_this] and headings else "failed",
                  {"pdf": this_in_pdf, "ref": [q for _, q in ref_this], "headings": headings})
        groups_in_pdf = [int(m) for m in re.findall(r"^\s*Subassembly (\d+):", text, re.M)]
        check("PDF subassembly headings are 1..M in order", "passed" if groups_in_pdf == [i for _, i in ref_groups] else "failed", {"pdf": groups_in_pdf, "ref": [i for _, i in ref_groups]})
        if ref_ginst:
            # every subassembly heading states how many of it the project needs
            inst_in_pdf = [int(m) for m in re.findall(r"^\s*Subassembly \d+: .*?\((\d+) in this project\)\s*$", text, re.M)]
            check("PDF subassembly instance counts match manual.json", "passed" if inst_in_pdf == [n for _, n, _ in ref_ginst] else "failed", {"pdf": inst_in_pdf, "ref": [n for _, n, _ in ref_ginst]})
        joints_in_pdf = [int(m) for m in re.findall(r"^\s*Joint (\d+):", text, re.M)]
        check("PDF joint headings are 1..K in order", "passed" if joints_in_pdf == [i for _, i in ref_joints] else "failed", {"pdf": joints_in_pdf, "ref": [i for _, i in ref_joints]})
        if sup["present"]:
            # the printed rows name their item ids; appendix-only rows appear only when the appendix is printed
            absent = [i for i in sup["existing"] if i not in text]
            leaked = [] if model.get("appendix") else [i for i in sup["new_design"] if i in text]
            heading = "Supplementary items (not modelled in CAD)" in text
            check("PDF prints the supplementary items as manual.json lists them", "passed" if heading and not absent and not leaked else "failed",
                  {"missing ids": absent, "new-design ids printed without the appendix": leaked, "heading": heading} if absent or leaked or not heading else f"{len(sup['existing'])} ids present")
        for token in (model["review_state"],):
            check(f"PDF states review state {token!r}", "passed" if token.upper() in text or token in text else "failed")
        if pdfinfo:
            info = run_cmd([pdfinfo, str(pdf)]).stdout
            pages = int(re.search(r"Pages:\s+(\d+)", info).group(1))
            report["pdf_pages"] = pages
            if exploded:
                # the exploded view's key prints each subassembly's page number (a Typst label lookup): it must be the page with that heading
                heading_page = {}
                for i in range(1, pages + 1):
                    for m in re.finditer(r"^\s*Subassembly (\d+):", run_cmd([pdftotext, "-f", str(i), "-l", str(i), "-raw", str(pdf), "-"]).stdout, re.M):
                        heading_page.setdefault(int(m.group(1)), i)
                sect = text.split("Subassemblies, drawn apart", 1)[1].split("\nParts\n", 1)[0] if "Subassemblies, drawn apart" in text else ""
                refs = [int(m) for m in re.findall(r"\bpage (\d+)\b", sect)]
                want = [heading_page.get(c["number"]) for c in exploded["callouts"] if c["kind"] == "subassembly"]
                check("PDF exploded-view key page numbers point at the subassembly pages", "passed" if refs == want and None not in want else "failed", {"pdf": refs, "headings": want})
            # one page per step after the front matter, so each step has a usable page break
            check("PDF has at least one page per step, subassembly and joint plus front matter", "passed" if pages >= len(ref_steps) + len(ref_groups) + len(ref_joints) + (2 if ref_steps else 1) else "failed",
                  f"{pages} pages for {len(ref_steps)} steps, {len(ref_groups)} subassemblies and {len(ref_joints)} joints")
        if pdfimages:
            imgs = run_cmd([pdfimages, "-list", str(pdf)]).stdout.strip().splitlines()
            n_imgs = max(0, len(imgs) - 2)
            expected = len(model["images"])
            check("PDF embeds images", "passed" if n_imgs >= expected else "failed", f"{n_imgs} image objects, {expected} distinct source images")
        checks_dir = out / "checks"; checks_dir.mkdir(exist_ok=True)
        if pdftoppm:
            r = run_cmd([pdftoppm, "-r", "60", "-png", str(pdf), str(checks_dir / "page")])
            pages_png = sorted(checks_dir.glob("page*.png"))
            check("PDF pages rasterised for inspection", "passed" if r.returncode == 0 and pages_png else "failed", [str(p.relative_to(out)) for p in pages_png])
        else:
            check("PDF pages rasterised for inspection", "not-run", "pdftoppm not on PATH")
    # viewer data beside the manual: the files the hotspots name exist with the receipt's hashes and the numbers are the manual's
    if model.get("viewer"):
        v = model["viewer"]
        problems = []
        hs_path = out / v["hotspots"]
        if not hs_path.is_file():
            problems.append(f"{v['hotspots']} missing")
        else:
            hs = receipts.read_json(hs_path)
            for state, rel in v["files"].items():
                f = out / rel
                if not f.is_file() or receipts.sha256_file(f) != v["sha256"][state]:
                    problems.append(f"{rel} missing or not the receipt's file")
                if hs.get("states", {}).get(state, {}).get("glb") != rel:
                    problems.append(f"hotspots.json names {hs.get('states', {}).get(state, {}).get('glb')!r} for {state}, manual.json {rel!r}")
            got = [(s["number"], s["definition"], s["shown_instance"]) for s in hs.get("subassemblies", [])]
            want = [(g["index"], g["definition"], g["id"]) for g in model.get("groups", [])]
            if got != want:
                problems.append({"hotspots": got, "manual": want})
            if hs.get("root_parts") and hs["root_parts"]["number"] != len(model.get("groups", [])) + 1:
                problems.append("root_parts number is not groups + 1")
            for s in hs.get("subassemblies", []) + ([hs["root_parts"]] if hs.get("root_parts") else []):
                for state in hs.get("states", {}):
                    a = (s.get("anchors") or {}).get(state)
                    if not a or len(a.get("position_m", [])) != 3 or len(a.get("normal", [])) != 3:
                        problems.append(f"{s.get('definition')}: no {state} anchor")
        check("viewer files resolve and hotspots.json agrees with manual.json", "passed" if not problems else "failed", problems or f"{len(v['files'])} GLB(s), {len(model.get('groups', []))} subassemblies")
    convert = shutil.which("magick") or shutil.which("convert")
    if not model["steps"]:
        check("greyscale step images written for monochrome inspection", "not-run", "no steps: inventory-only document")
    elif convert:
        checks_dir = out / "checks"; checks_dir.mkdir(exist_ok=True)
        made = []
        for s in model["steps"]:
            for name in (s["image"], s["result_image"]):
                if not name:
                    continue
                dst = checks_dir / f"grey-{name}"
                r = run_cmd([convert, str(out / "images" / name), "-background", "white", "-flatten", "-colorspace", "Gray", str(dst)])
                if r.returncode == 0:
                    made.append(str(dst.relative_to(out)))
        check("greyscale step images written for monochrome inspection", "passed" if made else "failed", made)
    else:
        check("greyscale step images written for monochrome inspection", "not-run", "ImageMagick not on PATH")
    report["not_checked"] = ["legibility of the images and pages (inspect checks/ output)", "insertion path, tool access, physical assembly"]
    report["all_passed"] = not failed
    if args.json:
        receipts.write_json(args.json, report)
    else:
        receipts.write_json(out / "check-report.json", report)
    print(f"[check] {'all passed' if not failed else 'FAILED'}; report at {args.json or out / 'check-report.json'}")
    return 1 if failed else 0
