"""Verify a built manual: HTML, PDF and manual.json agree; links and images resolve.

    python3 -m mechanical_docs check OUT_DIR [--json REPORT]

Reads OUT_DIR/manual.json as the reference, parses index.html for inventory
rows (part, required), step order and every image/link target, and reads the
PDF back with pdftotext (Poppler) for the `Step N`, `[step-id]` and
`required N` tokens. Rasterises the PDF pages (pdftoppm) and writes greyscale
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
        self.steps = []         # (id, index)
        self.needed = []        # (step id, part, qty)
        self.images = []
        self.links = []
        self.ids = set()
        self._step = None

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if "id" in a:
            self.ids.add(a["id"])
        if tag == "tr" and "data-part" in a and "data-required" in a:
            self.inventory.append((a["data-part"], int(a["data-required"]), int(a.get("data-label", 0))))
        if tag == "section" and "data-step" in a:
            self._step = a["data-step"]
            self.steps.append((a["data-step"], int(a["data-index"])))
        if tag == "div" and "data-qty" in a and self._step:
            self.needed.append((self._step, a["data-part"], int(a["data-qty"])))
        if tag == "img" and "src" in a:
            self.images.append(a["src"])
        if tag == "a" and "href" in a:
            self.links.append(a["href"])

    def handle_endtag(self, tag):
        if tag == "section":
            self._step = None


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
    # manual.json internal consistency: parts needed over all steps equal required quantities
    totals = {}
    for _, pid, q in ref_needed:
        totals[pid] = totals.get(pid, 0) + q
    check("manual.json: parts needed over all steps equal required quantities",
          "passed" if totals == {p: r for p, r, _ in ref_inv} else "failed", {"needed": totals, "required": {p: r for p, r, _ in ref_inv}})
    check("manual.json: step indices are 1..N in order", "passed" if [i for _, i in ref_steps] == list(range(1, len(ref_steps) + 1)) else "failed")

    # HTML
    html_path = out / "index.html"
    p = _Html(); p.feed(html_path.read_text(encoding="utf-8"))
    check("HTML inventory rows match manual.json", "passed" if p.inventory == ref_inv else "failed", {"html": p.inventory, "ref": ref_inv})
    check("HTML step order matches manual.json", "passed" if p.steps == ref_steps else "failed", {"html": p.steps, "ref": ref_steps})
    check("HTML parts-needed per step match manual.json", "passed" if p.needed == ref_needed else "failed", {"html": p.needed, "ref": ref_needed})
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
        text = run_cmd([pdftotext, "-layout", str(pdf), "-"]).stdout
        steps_in_pdf = [int(m) for m in re.findall(r"^\s*Step (\d+)\s*$", text, re.M)]
        ids_in_pdf = re.findall(r"\[([a-z0-9][a-z0-9._-]*)\]", text)
        ids_in_pdf = [i for i in ids_in_pdf if i in {s for s, _ in ref_steps}]
        check("PDF step headings are 1..N in order", "passed" if steps_in_pdf == [i for _, i in ref_steps] else "failed", {"pdf": steps_in_pdf, "ref": [i for _, i in ref_steps]})
        check("PDF step ids in manual.json order", "passed" if ids_in_pdf == [s for s, _ in ref_steps] else "failed", {"pdf": ids_in_pdf, "ref": [s for s, _ in ref_steps]})
        req_in_pdf = [int(m) for m in re.findall(r"required (\d+) ", text)]
        check("PDF required quantities match manual.json", "passed" if req_in_pdf == [r for _, r, _ in ref_inv] else "failed", {"pdf": req_in_pdf, "ref": [r for _, r, _ in ref_inv]})
        for token in (model["review_state"],):
            check(f"PDF states review state {token!r}", "passed" if token.upper() in text or token in text else "failed")
        if pdfinfo:
            info = run_cmd([pdfinfo, str(pdf)]).stdout
            pages = int(re.search(r"Pages:\s+(\d+)", info).group(1))
            report["pdf_pages"] = pages
            # one page per step after the front matter, so each step has a usable page break
            check("PDF has at least one page per step plus front matter", "passed" if pages >= len(ref_steps) + 2 else "failed", f"{pages} pages for {len(ref_steps)} steps")
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
    convert = shutil.which("magick") or shutil.which("convert")
    if convert:
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
