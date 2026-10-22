"""Static HTML manual from manual.json: one page, embedded CSS, print rules.

Web-only extras (clickable callouts on the overview, count inputs) are marked
`.web-only` and hidden in print; the printed page shows blank count boxes.
Images are referenced relatively from images/ unless embedded as data URIs.
"""
from __future__ import annotations

import base64
import html as H
import json
from pathlib import Path

CSS = """
:root { --ink: #111; --muted: #555; --line: #999; --accent: #d9480f; --card: #fff; --bg: #f4f4f5; }
* { box-sizing: border-box; }
body { margin: 0; font: 15px/1.45 system-ui, -apple-system, "Segoe UI", Roboto, sans-serif; color: var(--ink); background: var(--bg); }
main { max-width: 1100px; margin: 0 auto; padding: 24px 16px 64px; }
h1 { font-size: 2rem; margin: 0 0 .25rem; }
h2 { font-size: 1.4rem; margin: 2rem 0 .75rem; border-bottom: 2px solid var(--ink); padding-bottom: .25rem; }
.status { border: 2px solid var(--ink); background: var(--card); padding: 10px 14px; margin: 16px 0; }
.status p { margin: .25rem 0; }
.status .state { font-weight: 700; text-transform: uppercase; letter-spacing: .04em; }
table.inventory { width: 100%; border-collapse: collapse; background: var(--card); }
table.inventory th, table.inventory td { border: 1px solid var(--line); padding: 8px; vertical-align: middle; text-align: left; }
table.inventory th { background: #e8e8ea; }
table.inventory img { width: 120px; height: 120px; object-fit: contain; display: block; background: #fff; }
td.num, th.num { text-align: center; font-size: 1.4rem; font-weight: 700; width: 5.5rem; }
.label { display: inline-block; min-width: 2rem; height: 2rem; line-height: 2rem; text-align: center; border-radius: 50%; border: 2px solid var(--ink); font-weight: 700; margin-right: .5rem; }
.count-box { display: inline-block; width: 4.5rem; height: 2.4rem; border: 2px solid var(--ink); vertical-align: middle; }
input.count { width: 4.5rem; height: 2.4rem; font-size: 1.2rem; text-align: center; }
figure { margin: 0; background: var(--card); padding: 8px; border: 1px solid var(--line); }
figure img { width: 100%; height: auto; display: block; background: #fff; }
figcaption { color: var(--muted); font-size: .9rem; padding-top: 4px; }
.overview-wrap { position: relative; }
.overview-wrap svg.callouts { position: absolute; left: 8px; top: 8px; width: calc(100% - 16px); height: auto; }
.callouts a rect { fill: transparent; stroke: transparent; stroke-width: 3; }
.callouts a:hover rect, .callouts a:focus rect { stroke: var(--accent); fill: rgba(217,72,15,.08); }
.callouts text { font: 700 44px sans-serif; fill: #fff; text-anchor: middle; dominant-baseline: central; pointer-events: none; }
.callouts circle { fill: var(--accent); stroke: #fff; stroke-width: 3; }
section.step { background: var(--card); border: 2px solid var(--ink); margin: 24px 0; padding: 16px; display: grid; grid-template-columns: 220px 1fr; grid-template-rows: auto auto; gap: 16px; }
section.step header { grid-column: 1 / -1; display: flex; align-items: baseline; gap: 16px; }
.step-number { font-size: 3rem; font-weight: 800; line-height: 1; border: 3px solid var(--ink); padding: 4px 14px; }
.step-title { font-size: 1.1rem; color: var(--muted); }
.needed { border: 1px dashed var(--line); padding: 8px; }
.needed h3 { margin: 0 0 8px; font-size: .9rem; text-transform: uppercase; letter-spacing: .06em; color: var(--muted); }
.needed .item { display: flex; align-items: center; gap: 8px; margin-bottom: 8px; }
.needed img { width: 90px; height: 90px; object-fit: contain; background: #fff; border: 1px solid var(--line); }
.needed .qty { font-size: 1.8rem; font-weight: 800; }
.step-images { display: grid; grid-template-columns: 1fr; gap: 12px; }
.step-images.with-result { grid-template-columns: 2.2fr 1fr; align-items: start; }
.caption { grid-column: 1 / -1; font-size: 1.05rem; }
.hint { color: var(--muted); font-size: .9rem; }
dl.receipt { display: grid; grid-template-columns: max-content 1fr; gap: 4px 16px; font-size: .85rem; }
dl.receipt dt { font-weight: 600; } dl.receipt dd { margin: 0; overflow-wrap: anywhere; font-family: ui-monospace, monospace; }
@media (max-width: 720px) { section.step { grid-template-columns: 1fr; } .step-images.with-result { grid-template-columns: 1fr; } }
@media print {
  @page { size: A4; margin: 12mm; }
  body { background: #fff; font-size: 11pt; }
  main { max-width: none; padding: 0; }
  .web-only { display: none !important; }
  section.step { break-before: page; page-break-before: always; border-width: 1.5pt; }
  h2.parts { break-before: page; page-break-before: always; }
  figure, table.inventory tr { break-inside: avoid; page-break-inside: avoid; }
  a { color: inherit; text-decoration: none; }
}
@media screen { .print-only { display: none !important; } }
"""


def img_src(model, name, out_dir, embed):
    if embed:
        data = (Path(out_dir) / "images" / name).read_bytes()
        return "data:image/png;base64," + base64.b64encode(data).decode("ascii")
    return f"images/{name}"


def callouts_svg(model, out_dir):
    """Clickable numbered callouts over the overview, one per visible occurrence (web only)."""
    hs_path = Path(out_dir) / "hotspots" / "overview.json"
    if not hs_path.is_file():
        return ""
    hs = json.loads(hs_path.read_text())
    W, H_ = hs["width"], hs["height"]
    label_of = {row["part_id"]: row["label"] for row in model["inventory"]}
    r = max(16, round(min(W, H_) * 0.022))
    out = [f'<svg class="callouts web-only" viewBox="0 0 {W} {H_}" aria-label="Clickable part callouts (web only)">']
    # one callout per part (its largest projected occurrence) keeps a 155-occurrence scene legible
    best = {}
    for e in hs["occurrences"]:
        if e["corners_in_frame"] < 4:
            continue
        x0, y0, x1, y1 = e["box_px"]
        area = (x1 - x0) * (y1 - y0)
        if e["part_id"] not in best or area > best[e["part_id"]][0]:
            best[e["part_id"]] = (area, e)
    for _, e in sorted(best.values(), key=lambda t: (t[1]["box_px"][1], t[1]["box_px"][0])):
        x0, y0, x1, y1 = e["box_px"]
        n = label_of.get(e["part_id"], "?")
        out.append(f'<a href="#part-{H.escape(e["part_id"])}"><title>{H.escape(e["id"])}: part {n}</title>'
                   f'<rect x="{x0:.0f}" y="{y0:.0f}" width="{x1 - x0:.0f}" height="{y1 - y0:.0f}"/>'
                   f'<circle cx="{x0 + r:.0f}" cy="{y0 + r:.0f}" r="{r}"/><text x="{x0 + r:.0f}" y="{y0 + r:.0f}" style="font-size:{int(r * 1.2)}px">{n}</text></a>')
    out.append("</svg>")
    return "\n".join(out)


def render(model, out_dir, embed_images=False):
    e = H.escape
    src = lambda name: img_src(model, name, out_dir, embed_images)  # noqa: E731
    o = []
    o.append("<!doctype html>\n<html lang=\"en\">\n<head>\n<meta charset=\"utf-8\">\n<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">")
    o.append(f"<title>{e(model['title'])}</title>\n<style>{CSS}</style>\n</head>\n<body>\n<main>")
    o.append(f"<h1>{e(model['title'])}</h1>")
    o.append(f"<p class=\"hint\">Scene <code>{e(model['scene']['id'])}</code>: {e(model['scene']['title'])}. Instructions <code>{e(model['id'])}</code>. Generated {e(model['generated_at_utc'])}.</p>")
    o.append('<div class="status" role="note">')
    o.append(f"<p class=\"state\">{e(model['review_state'])}</p>")
    for line in model["status_lines"]:
        o.append(f"<p>{e(line)}</p>")
    o.append("</div>")

    # inventory
    o.append('<h2 class="parts" id="parts">Parts</h2>')
    o.append(f"<p class=\"hint\">{e(model['inventory_status'])}. Write the quantity found in the box.</p>")
    o.append('<table class="inventory"><thead><tr><th>#</th><th>Picture</th><th>Part</th><th class="num">Required</th><th class="num">Found</th></tr></thead><tbody>')
    for row in model["inventory"]:
        counted = "" if row["counted"] is None else str(row["counted"])
        o.append(f'<tr id="part-{e(row["part_id"])}" data-part="{e(row["part_id"])}" data-required="{row["required"]}" data-label="{row["label"]}">')
        o.append(f'<td class="num"><span class="label">{row["label"]}</span></td>')
        o.append(f'<td><img src="{src(row["thumbnail"])}" alt="{e(row["name"])}" width="120" height="120"></td>')
        inst = ", ".join(e(x) for x in row["occurrences"][:6]) + (f", … ({len(row['occurrences'])} total)" if len(row["occurrences"]) > 6 else "")
        o.append(f'<td><strong>{e(row["name"])}</strong><br><span class="hint">{e(row["dimensions"])}</span>'
                 + (f'<br><span class="hint">{e(row["details"])}</span>' if row.get("details") else "")
                 + (f'<br><span class="hint">{e(row["description"])}</span>' if row["description"] else "")
                 + f'<br><span class="hint">id <code>{e(row["part_id"])}</code>, installed as {inst}</span></td>')
        o.append(f'<td class="num">{row["required"]}<div class="hint" style="font-size:.7rem;font-weight:400">{e(row["unit"])}</div></td>')
        o.append(f'<td class="num"><input class="count web-only" type="number" min="0" value="{counted}" aria-label="quantity found for {e(row["name"])}"><span class="count-box print-only">{counted}</span></td></tr>')
    o.append("</tbody></table>")

    # overview
    o.append('<h2 id="overview">Finished assembly</h2>')
    o.append('<figure><div class="overview-wrap">')
    o.append(f'<img src="{src(model["overview_image"])}" alt="Overview of the finished assembly">')
    o.append(callouts_svg(model, out_dir))
    o.append("</div><figcaption>All parts installed. On the web, click a numbered callout to jump to the part.</figcaption></figure>")

    # steps
    if model["steps"]:
        o.append('<h2 id="steps">Steps</h2>')
    else:
        o.append('<h2 id="steps">Steps</h2><p class="hint">No assembly sequence has been authored for this scene.</p>')
    for s in model["steps"]:
        o.append(f'<section class="step" id="step-{s["index"]}" data-step="{e(s["id"])}" data-index="{s["index"]}">')
        o.append(f'<header><div class="step-number">{s["index"]}</div><div class="step-title"><code>{e(s["id"])}</code>' + (f' &middot; after {", ".join(e(r) for r in s["requires"])}' if s["requires"] else "") + "</div></header>")
        o.append('<div class="needed"><h3>Parts needed</h3>')
        for n in s["parts_needed"]:
            o.append(f'<div class="item" data-part="{e(n["part_id"])}" data-qty="{n["qty"]}"><img src="{src(n["thumbnail"])}" alt="{e(n["name"])}" width="90" height="90"><div><span class="label">{n["label"]}</span><br><span class="qty">×{n["qty"]}</span></div></div>')
        o.append("</div>")
        cls = "step-images with-result" if s["result_image"] else "step-images"
        o.append(f'<div class="{cls}">')
        o.append(f'<figure><img src="{src(s["image"])}" alt="Step {s["index"]}: {e(s["caption"])}"><figcaption>' + (f'Approach {e(s["approach"]["direction_text"])}; arrow is an unverified hint.' if s["approach"] else "Place as shown.") + "</figcaption></figure>")
        if s["result_image"]:
            o.append(f'<figure><img src="{src(s["result_image"])}" alt="Result of step {s["index"]}"><figcaption>Result</figcaption></figure>')
        o.append("</div>")
        o.append(f'<p class="caption">{e(s["caption"])}</p>')
        o.append("</section>")

    # receipt
    r = model["receipt"]
    o.append('<h2 id="record">Build record</h2>')
    o.append('<dl class="receipt">')
    for k, v in r["input_hashes"].items():
        o.append(f"<dt>{e(k)}</dt><dd>{e(v)}</dd>")
    if r.get("meshes"):
        o.append(f"<dt>FreeCAD</dt><dd>{e(str(r['meshes']['freecad_version']))}; tessellation {e(json.dumps(r['meshes']['tessellation']))}</dd>")
        for k, v in r["meshes"]["mesh_hashes"].items():
            o.append(f"<dt>mesh {e(k)}</dt><dd>{e(v)}</dd>")
    rr = r["render"]
    o.append(f"<dt>Blender</dt><dd>{e(str(rr.get('blender')))}, engine {e(str(rr.get('engine')))}, denoiser {e(str(rr.get('denoiser')))}, samples {rr.get('samples')}, long side {rr.get('long_side_px')} px{', preview quality' if rr.get('preview') else ''}</dd>")
    for w in rr.get("warnings") or []:
        o.append(f"<dt>render warning</dt><dd>{e(w)}</dd>")
    for k, v in r["render_views"].items():
        o.append(f"<dt>image {e(k)}</dt><dd>{e(v)}</dd>")
    o.append(f"<dt>generator</dt><dd>{e(json.dumps(r['generator']))}</dd>")
    o.append("</dl>")
    o.append(f"<p class=\"hint\">Review state {e(model['review_state'])}; physical assembly not validated. Hotspot files for interactive use: {', '.join(e(v) for v in model['hotspots'].values())} (web only).</p>")
    o.append("</main>\n</body>\n</html>\n")
    return "\n".join(o)
