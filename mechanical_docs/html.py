"""Static HTML manual from manual.json: one page, embedded CSS, print rules.

Picture-led parts cards (badge, large picture or wide picture plus end view,
short label, overall size, CAD quantity labelled as such, a count box), one
section per subassembly inspection view, the finished assembly with web-only
clickable callouts, the steps, a compact build record and, when the model
asks for it, a technical appendix with full identities and hashes. Web-only
extras (callouts, count inputs) are marked `.web-only` and hidden in print;
the printed page shows blank count boxes. Images are referenced relatively
from images/ unless embedded as data URIs.
"""
from __future__ import annotations

import base64
import html as H
import json
from pathlib import Path

from .names import slug

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
.hint { color: var(--muted); font-size: .9rem; }
.label { display: inline-block; min-width: 2rem; height: 2rem; line-height: 2rem; text-align: center; border-radius: 50%; border: 2px solid var(--ink); font-weight: 700; margin-right: .5rem; }
.count-box { display: inline-block; width: 4.5rem; height: 2.4rem; border: 2px solid var(--ink); vertical-align: middle; background: #fff; }
input.count { width: 4.5rem; height: 2.4rem; font-size: 1.2rem; text-align: center; }
.parts-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 14px; }
article.part { background: var(--card); border: 1.5px solid var(--ink); padding: 10px; display: grid; grid-template-rows: auto auto 1fr auto; gap: 6px; }
article.part .pic { display: grid; grid-template-columns: 1fr; gap: 6px; background: #fff; align-items: center; }
article.part .pic.long { grid-template-columns: 2fr 1fr; }
article.part img { width: 100%; height: auto; max-height: 230px; object-fit: contain; display: block; background: #fff; }
article.part h3 { margin: 0; font-size: 1rem; line-height: 1.25; display: flex; align-items: center; gap: .4rem; }
article.part .size { color: var(--muted); font-size: .9rem; }
article.part .review { color: var(--accent); }
article.part .qty-row { display: flex; align-items: center; justify-content: space-between; gap: 8px; border-top: 1px solid var(--line); padding-top: 6px; }
.cadqty { font-size: 1.9rem; font-weight: 800; line-height: 1; }
.cadqty small { display: block; font-size: .65rem; font-weight: 500; color: var(--muted); letter-spacing: .04em; text-transform: uppercase; }
figure { margin: 0; background: var(--card); padding: 8px; border: 1px solid var(--line); }
figure img { width: 100%; height: auto; display: block; background: #fff; }
figcaption { color: var(--muted); font-size: .9rem; padding-top: 4px; }
.overview-wrap { position: relative; }
.overview-wrap svg.callouts { position: absolute; left: 8px; top: 8px; width: calc(100% - 16px); height: auto; }
.callouts a rect { fill: transparent; stroke: transparent; stroke-width: 3; }
.callouts a:hover rect, .callouts a:focus rect { stroke: var(--accent); fill: rgba(217,72,15,.08); }
.callouts text { font: 700 44px sans-serif; fill: #fff; text-anchor: middle; dominant-baseline: central; pointer-events: none; }
.callouts circle { fill: var(--accent); stroke: #fff; stroke-width: 3; }
section.group { background: var(--card); border: 2px solid var(--ink); margin: 24px 0; padding: 16px; display: grid; grid-template-columns: 1fr 300px; gap: 16px; }
section.group header { grid-column: 1 / -1; display: flex; align-items: baseline; gap: 16px; flex-wrap: wrap; }
section.group .note { grid-column: 1 / -1; }
table.group-parts { width: 100%; border-collapse: collapse; }
table.group-parts td { border-bottom: 1px solid var(--line); padding: 6px 4px; vertical-align: middle; }
table.group-parts img { width: 64px; height: 64px; object-fit: contain; background: #fff; border: 1px solid var(--line); }
table.group-parts .qty { font-size: 1.5rem; font-weight: 800; text-align: center; }
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
dl.receipt { display: grid; grid-template-columns: max-content 1fr; gap: 4px 16px; font-size: .85rem; }
dl.receipt dt { font-weight: 600; } dl.receipt dd { margin: 0; overflow-wrap: anywhere; font-family: ui-monospace, monospace; }
table.appendix { width: 100%; border-collapse: collapse; font-size: .78rem; }
table.appendix th, table.appendix td { border: 1px solid var(--line); padding: 4px 6px; vertical-align: top; text-align: left; overflow-wrap: anywhere; }
table.appendix code { font-size: .75rem; }
@media (max-width: 720px) { section.step, section.group { grid-template-columns: 1fr; } .step-images.with-result { grid-template-columns: 1fr; } }
@media print {
  @page { size: A4; margin: 12mm; }
  body { background: #fff; font-size: 11pt; }
  main { max-width: none; padding: 0; }
  .web-only { display: none !important; }
  .parts-grid { grid-template-columns: repeat(3, 1fr); }
  article.part, figure, table.group-parts tr, table.appendix tr { break-inside: avoid; page-break-inside: avoid; }
  section.step, section.group, h2.appendix { break-before: page; page-break-before: always; border-width: 1.5pt; }
  h2.parts { break-before: page; page-break-before: always; }
  a { color: inherit; text-decoration: none; }
}
@media screen { .print-only { display: none !important; } }
"""


def img_src(model, name, out_dir, embed):
    if embed:
        data = (Path(out_dir) / "images" / name).read_bytes()
        return "data:image/png;base64," + base64.b64encode(data).decode("ascii")
    return f"images/{name}"


def callouts_svg(model, out_dir, view_id="overview"):
    """Clickable numbered callouts over a view, one per part (its largest
    projected occurrence keeps a 155-occurrence scene legible); web only."""
    hs_path = Path(out_dir) / "hotspots" / f"{view_id}.json"
    if not hs_path.is_file():
        return ""
    hs = json.loads(hs_path.read_text())
    W, H_ = hs["width"], hs["height"]
    label_of = {row["part_id"]: row["label"] for row in model["inventory"]}
    r = max(16, round(min(W, H_) * 0.022))
    out = [f'<svg class="callouts web-only" viewBox="0 0 {W} {H_}" aria-label="Clickable part callouts (web only)">']
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
        out.append(f'<a href="#part-{slug(e["part_id"])}"><title>{H.escape(e["id"])}: part {n}</title>'
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
    o.append(f"<p class=\"hint\">Scene <code>{e(model['scene']['id'])}</code>: {e(model['scene']['title'])}. Document <code>{e(model['id'])}</code>. Generated {e(model['generated_at_utc'])}.</p>")
    o.append('<div class="status" role="note">')
    o.append(f"<p class=\"state\">{e(model['review_state'])}</p>")
    for line in model["status_lines"]:
        o.append(f"<p>{e(line)}</p>")
    o.append("</div>")

    # parts: picture-led cards
    o.append('<h2 class="parts" id="parts">Parts</h2>')
    o.append(f"<p class=\"hint\">{e(model['cad_qty_note'])} Write the quantity you count in the box.</p>")
    o.append(f"<p class=\"hint\">Inventory status: {e(model['inventory_status'])}.</p>")
    o.append('<div class="parts-grid">')
    for row in model["inventory"]:
        counted = "" if row["counted"] is None else str(row["counted"])
        o.append(f'<article class="part" id="part-{slug(row["part_id"])}" data-part="{e(row["part_id"])}" data-required="{row["required"]}" data-label="{row["label"]}">')
        o.append(f'<h3><span class="label">{row["label"]}</span><span>{e(row["label_text"])}</span></h3>')
        if row.get("end_view"):
            o.append(f'<div class="pic long"><img src="{src(row["thumbnail"])}" alt="{e(row["label_text"])}, long view">'
                     f'<img src="{src(row["end_view"])}" alt="{e(row["label_text"])}, end view"></div>')
        else:
            o.append(f'<div class="pic"><img src="{src(row["thumbnail"])}" alt="{e(row["label_text"])}"></div>')
        o.append(f'<div class="size">{e(row["dimensions"])}' + (f'<br>{e(row["details"])}' if row.get("details") else "")
                 + (f'<br>{e(row["description"])}' if row["description"] else "")
                 + (f'<br><strong class="review">⚠ {e(row["review_note"])}</strong>' if row.get("review_note") else "") + "</div>")
        o.append(f'<div class="qty-row"><div class="cadqty">{row["required"]}<small>CAD qty, {e(row["unit"])}</small></div>'
                 f'<div><input class="count web-only" type="number" min="0" value="{counted}" aria-label="quantity counted for {e(row["label_text"])}">'
                 f'<span class="count-box print-only">{counted}</span><small class="hint" style="display:block;text-align:center">counted</small></div></div>')
        o.append("</article>")
    o.append("</div>")

    # subassembly inspection views
    if model["groups"]:
        o.append('<h2 id="subassemblies">Subassemblies (inspection views)</h2>')
        o.append('<p class="hint">Each view shows one subassembly alone with its parts at their CAD positions. These are parts views for inspection, not assembly steps: no order, fasteners or tool access is implied.</p>')
    for g in model["groups"]:
        gslug = slug(g["id"])
        o.append(f'<section class="group" id="group-{gslug}" data-group="{e(g["id"])}" data-index="{g["index"]}">')
        o.append(f'<header><div class="step-number">S{g["index"]}</div><div><div style="font-size:1.2rem;font-weight:700">{e(g["short_name"])}</div>'
                 f'<div class="step-title"><code>{e(g["id"])}</code>' + (f' · under <code>{e(g["parent_id"])}</code>' if g["parent_id"] else "") + "</div></div></header>")
        o.append('<figure><div class="overview-wrap">')
        o.append(f'<img src="{src(g["image"])}" alt="Subassembly {g["index"]}: {e(g["short_name"])}">')
        o.append(callouts_svg(model, out_dir, g["view_id"]))
        o.append(f'</div><figcaption>{e(g["note"])}.</figcaption></figure>')
        o.append('<table class="group-parts"><tbody>')
        for p in g["parts"]:
            o.append(f'<tr data-gpart="{e(p["part_id"])}" data-qty="{p["qty"]}"><td><span class="label">{p["label"]}</span></td>'
                     f'<td><img src="{src(p["thumbnail"])}" alt="{e(p["label_text"])}"></td><td>{e(p["label_text"])}</td><td class="qty">×{p["qty"]}</td></tr>')
        o.append("</tbody></table>")
        o.append(f'<p class="note hint">{len(g["occurrences"])} occurrence(s) in this subassembly; ids in manual.json' + (" and the appendix" if model["appendix"] else "") + ".</p>")
        o.append("</section>")

    # overview
    o.append('<h2 id="overview">Finished assembly</h2>')
    o.append('<figure><div class="overview-wrap">')
    o.append(f'<img src="{src(model["overview_image"])}" alt="Overview of the finished assembly">')
    o.append(callouts_svg(model, out_dir, "overview"))
    o.append("</div><figcaption>All parts at their CAD positions. On the web, click a numbered callout to jump to the part.</figcaption></figure>")

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

    # compact build record
    r = model["receipt"]
    rr = r["render"]
    o.append('<h2 id="record">Build record</h2>')
    o.append('<dl class="receipt">')
    o.append(f"<dt>generated</dt><dd>{e(model['generated_at_utc'])}</dd>")
    o.append(f"<dt>scene</dt><dd>{e(model['scene']['id'])}: {e(model['scene']['title'])} ({model['scene']['parts']} parts, {model['scene']['occurrences']} occurrences, {model['scene']['assemblies']} assemblies)</dd>")
    for k, v in model["scene"]["source_summary"].items():
        o.append(f"<dt>source {e(k)}</dt><dd>{e(str(v))}</dd>")
    for k, v in r["input_hashes"].items():
        if not k.startswith("assets/"):
            o.append(f"<dt>{e(k)}</dt><dd>{e(v)}</dd>")
    o.append(f"<dt>assets</dt><dd>{sum(1 for k in r['input_hashes'] if k.startswith('assets/'))} STEP files, hashes in manual.json" + (" and the appendix" if model["appendix"] else "") + "</dd>")
    if r.get("meshes"):
        m = r["meshes"]; t = m.get("tessellation") or {}
        o.append(f"<dt>FreeCAD</dt><dd>{e(str(m['freecad_version']))}; deflection {t.get('linear_deflection')} mm / {t.get('angular_deflection_deg')}°, budget {t.get('max_triangles_per_part')} triangles per part; meshes.json {e(str(m.get('sha256')))}</dd>")
    o.append(f"<dt>Blender</dt><dd>{e(str(rr.get('blender')))}, engine {e(str(rr.get('engine')))}, denoiser {e(str(rr.get('denoiser')))}, samples {rr.get('samples')}, long side {rr.get('long_side_px')} px"
             f"{', preview quality' if rr.get('preview') else ''}; line art {'on' if rr.get('lines') else 'off'} up to {rr.get('lines_max_triangles')} visible triangles; settings {e(str(rr.get('settings_sha256')))}</dd>")
    if rr.get("reused_views"):
        o.append(f"<dt>reused views</dt><dd>{len(rr['reused_views'])} of {len(r['render_views'])} images copied from {e(str(rr.get('reused_from')))} (same inputs, meshes and engine); per-view record in manual.json</dd>")
    for w in rr.get("warnings") or []:
        o.append(f"<dt>render warning</dt><dd>{e(w)}</dd>")
    o.append(f"<dt>images</dt><dd>{len(r['render_views'])} render(s), hashes in manual.json" + (" and the appendix" if model["appendix"] else "") + "</dd>")
    o.append(f"<dt>generator</dt><dd>{e('; '.join(f'{k} {v}' for k, v in r['generator'].items()))}</dd>")
    o.append("</dl>")
    o.append(f"<p class=\"hint\">Review state {e(model['review_state'])}; physical assembly not validated. Hotspot files for interactive use: {', '.join(e(v) for v in model['hotspots'].values())} (web only).</p>")

    # technical appendix
    if model["appendix"]:
        o.append('<h2 class="appendix" id="appendix">Technical appendix</h2>')
        o.append('<p class="hint">Full identities and hashes for traceability. The same data is in manual.json.</p>')
        o.append('<table class="appendix"><thead><tr><th>#</th><th>Part id, model state, source</th><th>Asset and mesh</th><th>Installed occurrences</th></tr></thead><tbody>')
        mesh_hashes = (r.get("meshes") or {}).get("mesh_hashes", {})
        for row in model["inventory"]:
            srcs = "; ".join(f"{k} {v}" for k, v in (row.get("source") or {}).items() if v not in (None, ""))
            props = "; ".join(f"{k} {v}" for k, v in (row.get("properties") or {}).items() if v not in (None, ""))
            o.append(f'<tr><td>{row["label"]}</td><td><code>{e(row["part_id"])}</code>' + (f'<br>model state {e(str(row["model_state"]))}' if row.get("model_state") else "")
                     + (f'<br>{e(srcs)}' if srcs else "") + (f'<br>{e(props)}' if props else "") + "</td>"
                     f'<td><code>{e(row["asset_path"])}</code> ({e(row["asset_units"])})<br>sha256 <code>{e(row["asset_sha256"])}</code>'
                     + (f'<br>mesh <code>{e(mesh_hashes.get(row["part_id"], ""))}</code>' if mesh_hashes.get(row["part_id"]) else "")
                     + f'<br>image <code>{e(r["render_views"].get("part-" + slug(row["part_id"]), ""))}</code></td>'
                     f'<td>{len(row["occurrences"])}: ' + "; ".join(e(x) for x in row["occurrences"])
                     + (f'<br>reference only: {"; ".join(e(x) for x in row["reference_occurrences"])}' if row["reference_occurrences"] else "") + "</td></tr>")
        o.append("</tbody></table>")
        for g in model["groups"]:
            o.append(f'<p class="hint"><strong>S{g["index"]} {e(g["id"])}</strong> (path {" / ".join(e(x) for x in g["path"])}): '
                     + "; ".join(f'{e(oc["id"])} → part {oc["label"]}' for oc in g["occurrences"]) + "</p>")
        o.append('<dl class="receipt">')
        for k, v in r["input_hashes"].items():
            o.append(f"<dt>{e(k)}</dt><dd>{e(v)}</dd>")
        for k, v in r["render_views"].items():
            d = r.get("render_view_details", {}).get(k, {})
            o.append(f"<dt>image {e(k)}</dt><dd>{e(v)}" + (f" (reused, rendered {e(str(d.get('reused_generated_at_utc')))})" if d.get("reused_from") else "") + "</dd>")
        for k, v in model["scene"]["source"].items():
            o.append(f"<dt>source {e(k)}</dt><dd>{e(str(v))}</dd>")
        o.append("</dl>")
    o.append("</main>\n</body>\n</html>\n")
    return "\n".join(o)
