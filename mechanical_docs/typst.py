"""Typst source for the printed manual from manual.json.

Image-led pages: a parts table with thumbnails and count boxes, the overview,
one page per step (parts needed with quantities, the step image, the result
image), then the build record. Text tokens `Step N` and `[step-id]` and the
parts table's `required N` cells are what checks.py reads back from the PDF.
"""
from __future__ import annotations

import json


def esc(s):
    """Escape Typst markup specials in plain text."""
    out = []
    for ch in str(s):
        if ch in "\\#*_`$<>@[]~":
            out.append("\\" + ch)
        else:
            out.append(ch)
    return "".join(out)


def render(model):
    L = []
    w = L.append
    w('#set page(paper: "a4", margin: (x: 14mm, y: 14mm))')
    w("#set text(size: 10.5pt)")
    w("#show heading.where(level: 1): set text(size: 20pt)")
    w("#show heading.where(level: 2): it => { v(4pt); text(size: 15pt, it); v(2pt) }")
    w("#show figure: set block(breakable: true)")
    w("#let countbox = box(width: 16mm, height: 9mm, stroke: 1.2pt + black)")
    w("#let badge(n) = box(width: 8mm, height: 8mm, radius: 4mm, stroke: 1.5pt + black, align(center + horizon, text(weight: \"bold\", size: 11pt, str(n))))")
    w(f"= {esc(model['title'])}")
    w(f"Scene `{esc(model['scene']['id'])}`: {esc(model['scene']['title'])}. Instructions `{esc(model['id'])}`. Generated {esc(model['generated_at_utc'])}.")
    w("")
    w("#block(width: 100%, stroke: 1.5pt + black, inset: 8pt)[")
    w(f"  #text(weight: \"bold\", size: 12pt)[{esc(model['review_state']).upper()}]")
    for line in model["status_lines"]:
        w(f"  \\ {esc(line)}")
    w("]")
    w("")
    # parts
    w("== Parts")
    w(f"{esc(model['inventory_status'])}. Write the quantity found in the box.")
    w("")
    w("#table(")
    w("  columns: (auto, 30mm, 1fr, 22mm, 20mm),")
    w("  align: (center + horizon, center + horizon, left + horizon, center + horizon, center + horizon),")
    w("  stroke: 0.6pt + luma(120),")
    w("  table.header([*\\#*], [*Picture*], [*Part*], [*Required*], [*Found*]),")
    for row in model["inventory"]:
        found = "countbox" if row["counted"] is None else f"[{row['counted']}]"
        desc = f" \\ #text(size: 8.5pt, fill: luma(80))[{esc(row['description'])}]" if row["description"] else ""
        details = f" \\ #text(size: 8.5pt, fill: luma(80))[{esc(row['details'])}]" if row.get("details") else ""
        inst = ", ".join(row["occurrences"][:6]) + (f", … ({len(row['occurrences'])} total)" if len(row["occurrences"]) > 6 else "")
        w(f"  [#badge({row['label']})], [#image(\"images/{row['thumbnail']}\", width: 28mm)],")
        w(f"  [*{esc(row['name'])}* \\ #text(size: 9pt)[{esc(row['dimensions'])}]{details}{desc} \\ #text(size: 7.5pt, fill: luma(80))[id `{esc(row['part_id'])}`, installed as {esc(inst)}]],")
        w(f"  [#text(size: 16pt, weight: \"bold\")[{row['required']}] \\ #text(size: 7.5pt)[required {row['required']} {esc(row['unit'])}]], [#{found}],")
    w(")")
    w("")
    # overview
    w("== Finished assembly")
    w(f"#figure(image(\"images/{model['overview_image']}\", width: 100%), caption: [All parts installed.])")
    # steps
    if not model["steps"]:
        w(""); w("== Steps"); w("No assembly sequence has been authored for this scene."); w("")
    for s in model["steps"]:
        w("#pagebreak()")
        w(f"== Step {s['index']}")
        w(f"#text(size: 8pt, fill: luma(90))[\\[{esc(s['id'])}\\]" + (f" after {esc(', '.join(s['requires']))}" if s["requires"] else "") + "]")
        w("")
        w("#grid(columns: (34mm, 1fr), column-gutter: 6mm, row-gutter: 4mm,")
        # parts needed column
        w("  block(stroke: (paint: luma(120), dash: \"dashed\"), inset: 5pt, width: 100%)[")
        w("    #text(size: 7.5pt, fill: luma(80))[PARTS NEEDED] \\")
        for n in s["parts_needed"]:
            w(f"    #badge({n['label']}) #h(2pt) #text(size: 16pt, weight: \"bold\")[×{n['qty']}] \\")
            w(f"    #image(\"images/{n['thumbnail']}\", width: 26mm) \\")
        w("  ],")
        # images
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
    # record
    w("#pagebreak()")
    w("== Build record")
    r = model["receipt"]
    w("#set text(size: 8pt)")
    w("#table(columns: (34%, 1fr), stroke: 0.4pt + luma(160), align: left + horizon,")
    for k, v in r["input_hashes"].items():
        w(f"  [{esc(k)}], [`{v}`],")
    if r.get("meshes"):
        w(f"  [FreeCAD], [{esc(str(r['meshes']['freecad_version']))}; tessellation {esc(json.dumps(r['meshes']['tessellation']))}],")
        for k, v in r["meshes"]["mesh_hashes"].items():
            w(f"  [mesh {esc(k)}], [`{v}`],")
    rr = r["render"]
    w(f"  [Blender], [{esc(str(rr.get('blender')))}, engine {esc(str(rr.get('engine')))}, denoiser {esc(str(rr.get('denoiser')))}, samples {rr.get('samples')}, long side {rr.get('long_side_px')} px{', preview quality' if rr.get('preview') else ''}],")
    for wmsg in rr.get("warnings") or []:
        w(f"  [render warning], [{esc(wmsg)}],")
    for k, v in r["render_views"].items():
        w(f"  [image {esc(k)}], [`{v}`],")
    gen = r["generator"]
    w(f"  [generator], [{esc('; '.join(f'{k} {v}' for k, v in gen.items()))}],")
    w(")")
    w(f"Review state {esc(model['review_state'])}; physical assembly not validated.")
    return "\n".join(L) + "\n"
