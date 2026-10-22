"""Typst source for the printed manual from manual.json.

Image-led pages: a grid of parts cards (large picture or a wide picture plus
end view for long parts, short label, overall size, the CAD quantity labelled
as such, a paper count box), a table of supplementary items (not modelled in
CAD; existing-design rows only, new-design rows in the appendix), one page per
subassembly inspection view and per joint close-up, each with its "hardware
to review" list, the overview, one page per step (parts needed with
quantities, the step image, the result image), a compact build record and,
when the model asks for it, a technical appendix. Text tokens `Step N`,
`Subassembly N`, `Joint N`, `[step-id]`, the cards' `CAD qty N unit` and the
supplementary rows' item ids are what checks.py reads back from the PDF.
"""
from __future__ import annotations

import json


def raw(s):
    """An identifier set verbatim as inline raw text: `#raw("…")` with the string
    escaped, so backslashes, underscores and brackets in ids print as they are."""
    return '#raw("' + str(s).replace("\\", "\\\\").replace('"', '\\"') + '")'


def esc(s):
    """Escape Typst markup specials in plain text."""
    out = []
    for ch in str(s):
        if ch in "\\#*_`$<>@[]~":
            out.append("\\" + ch)
        else:
            out.append(ch)
    return "".join(out)


# A card never breaks across pages and its rows have fixed heights, so the
# quantity line sits at the same place on every card (the PDF text check reads
# the cards in content order); over-long labels and details are clipped on the
# card and complete in the HTML, manual.json and the appendix.
CARD_HEIGHT_MM = 84      # three rows per A4 page with the 4 mm gutters
HEAD_HEIGHT_MM = 12
PIC_HEIGHT_MM = 34
TEXT_HEIGHT_MM = 16      # six 7.5 pt lines: size, details, description, stock record, configuration flag, review note


def render(model):
    L = []
    w = L.append
    w('#set page(paper: "a4", margin: (x: 12mm, y: 12mm))')
    w("#set text(size: 10.5pt)")
    w("#show heading.where(level: 1): set text(size: 20pt)")
    w("#show heading.where(level: 2): it => { v(4pt); text(size: 15pt, it); v(2pt) }")
    w("#show figure: set block(breakable: true)")
    w("#let countbox = box(width: 16mm, height: 9mm, stroke: 1.2pt + black)")
    w("#let badge(n) = box(width: 7.5mm, height: 7.5mm, radius: 4mm, stroke: 1.5pt + black, align(center + horizon, text(weight: \"bold\", size: 10pt, str(n))))")
    w("#let sbadge(s) = box(height: 6.5mm, radius: 1mm, inset: (x: 1.5mm), stroke: (paint: black, thickness: 1pt, dash: \"dashed\"), align(center + horizon, text(weight: \"bold\", size: 8.5pt, s)))")
    w(f"= {esc(model['title'])}")
    w(f"Scene {raw(model['scene']['id'])}: {esc(model['scene']['title'])}. Document {raw(model['id'])}. Generated {esc(model['generated_at_utc'])}.")
    w("")
    w("#block(width: 100%, stroke: 1.5pt + black, inset: 8pt)[")
    w(f"  #text(weight: \"bold\", size: 12pt)[{esc(model['review_state']).upper()}]")
    for line in model["status_lines"]:
        w(f"  \\ {esc(line)}")
    w("]")
    w("")
    # parts cards
    w("== Parts")
    w(f"#text(size: 9pt)[{esc(model['cad_qty_note'])} Write the quantity you count in the box.]")
    w("")
    w("#grid(columns: (1fr, 1fr, 1fr), column-gutter: 4mm, row-gutter: 4mm,")
    for row in model["inventory"]:
        found = "#countbox"
        w(f"  block(width: 100%, height: {CARD_HEIGHT_MM}mm, stroke: 1pt + black, inset: 4pt, clip: true, breakable: false)[")
        w(f"    #box(width: 100%, height: {HEAD_HEIGHT_MM}mm, clip: true)[#badge({row['label']}) #h(2pt) #text(weight: \"bold\", size: 9pt)[{esc(row['label_text'])}]]")
        w("    #v(1pt)")
        if row.get("end_view"):
            w(f"    #grid(columns: (2fr, 1fr), column-gutter: 1.5mm, image(\"images/{row['thumbnail']}\", width: 100%, height: {PIC_HEIGHT_MM}mm, fit: \"contain\"), "
              f"image(\"images/{row['end_view']}\", width: 100%, height: {PIC_HEIGHT_MM}mm, fit: \"contain\"))")
        else:
            w(f"    #image(\"images/{row['thumbnail']}\", width: 100%, height: {PIC_HEIGHT_MM}mm, fit: \"contain\")")
        w("    #v(1pt)")
        size = esc(row["dimensions"])
        extra = " \\ " + esc(row["details"]) if row.get("details") else ""
        extra += " \\ " + esc(row["description"]) if row["description"] else ""
        if row.get("stock_text"):
            extra += " \\ " + esc(row["stock_text"])
        if row.get("intended_configuration_confirmed") is not None:
            extra += " \\ intended configuration confirmed: " + ("yes" if row["intended_configuration_confirmed"] else "no")
        if row.get("review_note"):
            extra += " \\ #text(weight: \"bold\", fill: rgb(\"#b4400a\"))[⚠ " + esc(row["review_note"]) + "]"
        w(f"    #box(width: 100%, height: {TEXT_HEIGHT_MM}mm, clip: true)[#text(size: 7.5pt, fill: luma(60))[{size}{extra}]]")
        w("    #v(1fr)")
        w("    #line(length: 100%, stroke: 0.4pt + luma(150))")
        w("    #grid(columns: (1fr, auto), align: (left + horizon, right + horizon),")
        w(f"      [#text(size: 17pt, weight: \"bold\")[{row['required']}] #h(2pt) #text(size: 6.5pt, fill: luma(60))[CAD qty {row['required']} {esc(row['unit'])}]],")
        w(f"      [{found} #h(1pt) #text(size: 6.5pt, fill: luma(60))[counted]])")
        w("  ],")
    w(")")
    w(f"#text(size: 8pt, fill: luma(90))[{esc(model['count_box_note'])}]")
    w("")
    # supplementary items: existing-design rows; new-design rows only in the appendix
    sup = model["supplement"]
    printed = [r for r in sup["rows"] if not r["appendix_only"]]
    if sup["present"]:
        w("#pagebreak(weak: true)")
        w("== Supplementary items (not modelled in CAD)")
        w(f"#text(size: 9pt)[{esc(sup['note'])}" + (f" Status: {esc(sup['status'])}." if sup["status"] else "") + "]")
        w("")
        if printed:
            w("#set text(size: 8pt)")
            w("#table(columns: (9mm, 1fr, 24mm, 25mm, 30mm, 25mm, 12mm, 17mm), stroke: 0.5pt + luma(140), align: left + top,")
            w("  table.header([*\\#*], [*Item*], [*Kind, status*], [*Required*], [*Stock*], [*Included with*], [*Config. confirmed*], [*counted*]),")
            for r in printed:
                item = f"*{esc(r['title'])}* \\ {raw(r['item_id'])} \\ joint {raw(r['joint_id'])} \\ attaches to: {esc(r['attaches_text'])}"
                if r["specification"] and r["title"] != r["specification"]:
                    item += f" \\ {esc(r['specification'])}"
                w(f"  [#sbadge[{r['label']}]], [{item}], [{esc(r['kind_text'])} \\ {esc(r['status_text'])}], [{esc(r['required_text'])}], [{esc(r['stock_text'])}],"
                  f" [{esc(r['included_with_text']) or '—'}], [{'yes' if r['intended_configuration_confirmed'] else 'no'}], [#box(width: 14mm, height: 8mm, stroke: 1pt + black)],")
            w(")")
            w("#set text(size: 10.5pt)")
        else:
            w("No supplementary items for the existing design.")
        if sup["new_design"]:
            w(f"#text(size: 8pt, fill: luma(90))[{len(sup['new_design'])} new-design row(s) are in the appendix" + ("" if model["appendix"] else " (not printed in this compact document)") + ".]")
        w("")

    def hardware(items):
        if not items:
            return
        w(f"#text(size: 9pt, weight: \"bold\", fill: rgb(\"#b4400a\"))[{esc(sup['hardware_heading'])}]")
        for h in items:
            w(f"- #sbadge[{h['label']}] {esc(h['title'])} · {esc(h['status_text'])} · {esc(h['required_text'])} · joint {raw(h['joint_id'])}")
        w("")

    # subassembly inspection views
    for g in model["groups"]:
        w("#pagebreak(weak: true)")
        w(f"== Subassembly {g['index']}: {esc(g['short_name'])}")
        w(f"#text(size: 8pt, fill: luma(90))[{raw(g['id'])}" + (f" under {raw(g['parent_id'])}" if g["parent_id"] else "") + "]")
        w("")
        w(f"#text(size: 9pt)[{esc(g['note'])}.]")
        w("")
        w(f"#figure(image(\"images/{g['image']}\", width: 100%), caption: [Subassembly {g['index']}: {esc(g['short_name'])}, parts at their CAD positions (inspection view).])")
        w("")
        w("#table(columns: (auto, 22mm, 1fr, 22mm), align: (center + horizon, center + horizon, left + horizon, center + horizon), stroke: 0.5pt + luma(140),")
        w("  table.header([*\\#*], [*Picture*], [*Part*], [*In this subassembly*]),")
        for p in g["parts"]:
            w(f"  [#badge({p['label']})], [#image(\"images/{p['thumbnail']}\", width: 20mm, height: 14mm, fit: \"contain\")], [{esc(p['label_text'])}], [#text(size: 14pt, weight: \"bold\")[×{p['qty']}]],")
        w(")")
        w(f"#text(size: 8pt, fill: luma(90))[{len(g['occurrences'])} occurrence(s); ids in manual.json" + (" and the appendix" if model["appendix"] else "") + ".]")
        w("")
        hardware(g.get("hardware", []))
    # joint close-ups
    for j in model["joints"]:
        w("#pagebreak(weak: true)")
        w(f"== Joint {j['index']}: {esc(j['joint_id'])}")
        w(f"#text(size: 8pt, fill: luma(90))[context {raw(j['context_assembly'])} ({esc(j['context_style'])}, {len(j['context_occurrences'])} other occurrence(s))]")
        w("")
        w(f"#text(size: 9pt)[{esc(j['note'])}.]")
        w("")
        w(f"#figure(image(\"images/{j['image']}\", width: 100%), caption: [Joint {j['index']}: {esc(j['joint_id'])}, occurrences at their CAD positions (inspection view, not a step).])")
        w("")
        w("#table(columns: (auto, 22mm, 1fr), align: (center + horizon, center + horizon, left + horizon), stroke: 0.5pt + luma(140),")
        w("  table.header([*\\#*], [*Picture*], [*Occurrence in this joint*]),")
        for oc in j["occurrences"]:
            w(f"  [#badge({oc['label']})], [#image(\"images/{oc['thumbnail']}\", width: 20mm, height: 14mm, fit: \"contain\")], [{esc(oc['label_text'])} \\ #text(size: 7.5pt, fill: luma(90))[{raw(oc['id'])}]],")
        w(")")
        w("")
        hardware(j["hardware"])
        if not j["hardware"]:
            w("#text(size: 8pt, fill: luma(90))[No supplementary items are recorded for this joint.]")
            w("")
    # overview
    w("#pagebreak(weak: true)")
    w("== Finished assembly")
    w(f"#figure(image(\"images/{model['overview_image']}\", width: 100%), caption: [All parts at their CAD positions.])")
    # steps
    if not model["steps"]:
        w(""); w("== Steps"); w("No assembly sequence has been authored for this scene."); w("")
    for s in model["steps"]:
        w("#pagebreak()")
        w(f"== Step {s['index']}")
        w(f"#text(size: 8pt, fill: luma(90))[\\[{esc(s['id'])}\\]" + (f" after {esc(', '.join(s['requires']))}" if s["requires"] else "") + "]")
        w("")
        w("#grid(columns: (34mm, 1fr), column-gutter: 6mm, row-gutter: 4mm,")
        w("  block(stroke: (paint: luma(120), dash: \"dashed\"), inset: 5pt, width: 100%)[")
        w("    #text(size: 7.5pt, fill: luma(80))[PARTS NEEDED] \\")
        for n in s["parts_needed"]:
            w(f"    #badge({n['label']}) #h(2pt) #text(size: 16pt, weight: \"bold\")[×{n['qty']}] \\")
            w(f"    #image(\"images/{n['thumbnail']}\", width: 26mm) \\")
        w("  ],")
        if s["result_image"]:
            w("  grid(columns: (2.2fr, 1fr), column-gutter: 4mm,")
            w(f"    figure(image(\"images/{s['image']}\", width: 100%), caption: [Approach {esc(s['approach']['direction_text'])}; the arrow is an unverified hint.]),")
            w(f"    figure(image(\"images/{s['result_image']}\", width: 100%), caption: [Result]),")
            w("  ),")
        else:
            w(f"  figure(image(\"images/{s['image']}\", width: 100%), caption: [Place as shown.]),")
        w(")")
        w("")
        w(f"#text(size: 12pt)[{esc(s['caption'])}]")
        w("")
    # compact build record
    w("#pagebreak(weak: true)")
    w("== Build record")
    r = model["receipt"]; rr = r["render"]
    w("#set text(size: 8pt)")
    w("#table(columns: (30%, 1fr), stroke: 0.4pt + luma(160), align: left + horizon,")
    w(f"  [generated], [{esc(model['generated_at_utc'])}],")
    w(f"  [scene], [{esc(model['scene']['id'])}: {esc(model['scene']['title'])} ({model['scene']['parts']} parts, {model['scene']['occurrences']} occurrences, {model['scene']['assemblies']} assemblies)],")
    for k, v in model["scene"]["source_summary"].items():
        w(f"  [source {esc(k)}], [{esc(str(v))}],")
    for k, v in r["input_hashes"].items():
        if not k.startswith("assets/"):
            w(f"  [{esc(k)}], [`{v}`],")
    n_assets = sum(1 for k in r["input_hashes"] if k.startswith("assets/"))
    w(f"  [assets], [{n_assets} STEP files; hashes in manual.json" + (" and the appendix" if model["appendix"] else "") + "],")
    if r.get("meshes"):
        m = r["meshes"]; t = m.get("tessellation") or {}
        w(f"  [FreeCAD], [{esc(str(m['freecad_version']))}; deflection {t.get('linear_deflection')} mm / {t.get('angular_deflection_deg')}°, budget {t.get('max_triangles_per_part')} triangles per part; meshes.json {raw(str(m.get('sha256')))}],")
    w(f"  [Blender], [{esc(str(rr.get('blender')))}, engine {esc(str(rr.get('engine')))}, denoiser {esc(str(rr.get('denoiser')))}, samples {rr.get('samples')}, long side {rr.get('long_side_px')} px"
      f"{', preview quality' if rr.get('preview') else ''}; line art {'on' if rr.get('lines') else 'off'} up to {rr.get('lines_max_triangles')} visible triangles; settings {raw(str(rr.get('settings_sha256')))}],")
    if rr.get("reused_views"):
        w(f"  [reused views], [{len(rr['reused_views'])} of {len(r['render_views'])} images copied from an earlier run with the same inputs, meshes and engine ({esc(str(rr.get('reused_from')))}); per-view record in manual.json],")
    for wmsg in rr.get("warnings") or []:
        w(f"  [render warning], [{esc(wmsg)}],")
    w(f"  [images], [{len(r['render_views'])} renders; hashes in manual.json" + (" and the appendix" if model["appendix"] else "") + "],")
    if model["supplement"]["present"]:
        w(f"  [supplement.json], [{len(model['supplement']['rows'])} row(s): {len(model['supplement']['existing'])} existing design, {len(model['supplement']['new_design'])} new design; never added to CAD quantities],")
    gen = r["generator"]
    w(f"  [generator], [{esc('; '.join(f'{k} {v}' for k, v in gen.items()))}],")
    w(")")
    w(f"Review state {esc(model['review_state'])}; physical assembly not validated.")
    # technical appendix
    if model["appendix"]:
        w("#pagebreak()")
        w("== Technical appendix")
        w("Full identities and hashes for traceability; the same data is in manual.json.")
        w("")
        w("#set text(size: 6.5pt)")
        w("#table(columns: (6mm, 34%, 30%, 1fr), stroke: 0.3pt + luma(160), align: left + top,")
        w("  table.header([*\\#*], [*Part id, model state, source*], [*Asset and mesh*], [*Installed occurrences*]),")
        mesh_hashes = (r.get("meshes") or {}).get("mesh_hashes", {})
        for row in model["inventory"]:
            srcs = "; ".join(f"{k} {v}" for k, v in (row.get("source") or {}).items() if v not in (None, ""))
            props = "; ".join(f"{k} {v}" for k, v in (row.get("properties") or {}).items() if v not in (None, ""))
            cell1 = f"{raw(row['part_id'])}" + (f" \\ model state {esc(str(row['model_state']))}" if row.get("model_state") else "") + (f" \\ {esc(srcs)}" if srcs else "") + (f" \\ {esc(props)}" if props else "")
            cell2 = f"{raw(row['asset_path'])} ({esc(row['asset_units'])}) \\ sha256 `{row['asset_sha256']}`"
            if mesh_hashes.get(row["part_id"]):
                cell2 += f" \\ mesh `{mesh_hashes[row['part_id']]}`"
            img = r["render_views"].get("part-" + __import__("mechanical_docs.names", fromlist=["slug"]).slug(row["part_id"]), "")
            cell2 += f" \\ image `{img}`"
            cell3 = f"{len(row['occurrences'])}: " + "; ".join(esc(x) for x in row["occurrences"])
            if row["reference_occurrences"]:
                cell3 += " \\ reference only: " + "; ".join(esc(x) for x in row["reference_occurrences"])
            w(f"  [{row['label']}], [{cell1}], [{cell2}], [{cell3}],")
        w(")")
        for g in model["groups"]:
            w(f"*Subassembly {g['index']} {esc(g['id'])}* (path {esc(' / '.join(g['path']))}): " + "; ".join(f"{esc(oc['id'])} → part {oc['label']}" for oc in g["occurrences"]) + "\n")
        for j in model["joints"]:
            w(f"*Joint {j['index']} {esc(j['joint_id'])}* (context {esc(j['context_assembly'])}, {esc(j['context_style'])}): "
              + "; ".join(f"{esc(oc['id'])} → part {oc['label']}" for oc in j["occurrences"]) + "; context occurrences: " + (esc("; ".join(j["context_occurrences"])) or "none") + "\n")
        stock_rows = [row for row in model["inventory"] if row.get("intended_configuration_confirmed") is not None]
        if stock_rows:
            w("#table(columns: (6mm, 1fr, 1fr, 30mm), stroke: 0.3pt + luma(160), align: left + top,")
            w("  table.header([*\\#*], [*Part*], [*Stock record*], [*Configuration confirmed*]),")
            for row in stock_rows:
                w(f"  [{row['label']}], [{esc(row['label_text'])}], [{esc(row['stock_text'])}], [{'yes' if row['intended_configuration_confirmed'] else 'no'}],")
            w(")")
        if model["supplement"]["present"]:
            w("=== Supplementary items, every field")
            w(esc(model["supplement"]["note"]) + "".join(f" {esc(k)}: {esc(str(v))}." for k, v in model["supplement"]["source"].items()))
            w("")
            w("#table(columns: (6mm, 18%, 14%, 18%, 16%, 14%, 1fr), stroke: 0.3pt + luma(160), align: left + top,")
            w("  table.header([*\\#*], [*item_id, joint_id, scope*], [*kind, status*], [*family / specification*], [*quantities*], [*included_with, attaches_to*], [*supplier, cost, evidence*]),")
            for sr in model["supplement"]["rows"]:
                inc = sr["included_with"]
                inc_text = "null" if not inc else "; ".join(f"{k} {v}" for k, v in inc.items())
                nul = lambda v: "null" if v is None else str(v)  # noqa: E731
                q = f"confirmed\\_required\\_each {nul(sr['confirmed_required_each'])} \\ on\\_hand\\_each {nul(sr['on_hand_each'])}"
                if sr["on_hand_each"] is not None:
                    q += f" \\ counted\\_by {esc(sr['counted_by'])}, {esc(sr['counted_date'])}"
                if sr["stock_location"]:
                    q += f" \\ stock\\_location {esc(sr['stock_location'])}"
                q += f" \\ on\\_order\\_each {nul(sr['on_order_each'])}"
                fam = f"{esc(nul(sr['candidate_item_family']))} \\ {esc(nul(sr['specification']))}" + (f" \\ basis: {esc(sr['quantity_basis'])}" if sr["quantity_basis"] else "")
                sup_cell = (f"supplier\\_part\\_number {esc(nul(sr['supplier_part_number']))} \\ verified {str(sr['supplier_specification_verified']).lower()}"
                            f" \\ unit\\_cost {nul(sr['unit_cost'])} {esc(sr['currency'] or '')} \\ {esc(nul(sr['evidence']))} \\ next\\_check {esc(nul(sr['next_check']))}")
                w(f"  [{sr['label']}], [{raw(sr['item_id'])} \\ joint {raw(sr['joint_id'])} \\ scope {esc(sr['scope'])}], [{esc(sr['item_kind'])} \\ {esc(sr['status'])} \\ confirmed {str(sr['intended_configuration_confirmed']).lower()}],"
                  f" [{fam}], [{q}], [{esc(inc_text)} \\ attaches\\_to: {esc('; '.join(sr['attaches_to'])) or '\\[\\]'}], [{sup_cell}],")
            w(")")
        w("#table(columns: (30%, 1fr), stroke: 0.3pt + luma(160), align: left + horizon,")
        for k, v in r["input_hashes"].items():
            w(f"  [{esc(k)}], [`{v}`],")
        for k, v in r["render_views"].items():
            d = r.get("render_view_details", {}).get(k, {})
            w(f"  [image {esc(k)}], [`{v}`" + (f" (reused, rendered {esc(str(d.get('reused_generated_at_utc')))})" if d.get("reused_from") else "") + "],")
        for k, v in model["scene"]["source"].items():
            w(f"  [source {esc(k)}], [{esc(str(v))}],")
        w(")")
    return "\n".join(L) + "\n"
