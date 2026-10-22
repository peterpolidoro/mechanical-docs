# Incoming documentation agent

The first slice exists, runs on three synthetic fixtures and on the first
production snapshot (inventory and six subassembly inspection views, no
sequence); the supplementary-items manifest and per-joint close-ups are
implemented and proven on the three-part fixture, not yet on the enclosure.
Read AGENTS.md, README.md, docs/input-contract.md (implemented subset,
production fields, flexible instances, the inventory stock record, the
supplement contract, `joint_views`, stage outputs, exporter field request),
docs/environment.md (roles, FreeCAD and Blender quirks, render cost, budgets
and view reuse) and .agents/PLANS.md. Use .agents/handoff.local.md for the
mailbox and evidence paths; the tracked documentation stays usable without them.

## What exists

- `mechanical_docs/`: `manifest.py` (validation, production fields, +Y-up basis,
  the inventory stock record, `supplement.json`), `names.py` (slugs for
  free-form ids), `stepinfo.py` (declared STEP unit), `transforms.py`,
  `procedure.py`, `gltf.py`, `geometry.py`, `receipts.py`, `reuse.py` (which
  earlier views are stale under new settings), `render_settings.py`
  (looks, budgets, long-part thumbnail rules, `inspection_groups`,
  `joint_views`), `cad_mesh.py` (FreeCADCmd, triangle budget), `render.py`
  (Blender, Cycles default, line budget, wide thumbnails and end views for long
  parts, `--groups` subassembly inspection views, `joint_views` close-ups,
  `--reuse` of earlier views), `document.py` + `html.py` + `typst.py`
  (picture-led parts cards, supplementary items, subassembly and joint pages
  with hardware lists, compact build record, `--appendix`), `checks.py`,
  `cli.py` (`inspect`, `inventory-template`, `manual`, `check`). `tests/` has
  102 pure-Python tests plus `tests/test_cad_stage.py`, which runs FreeCAD on
  the units fixture when `FreeCADCmd` is on PATH (the CAD role) and is skipped
  otherwise.
- `examples/three-part-fixture/` (now with `supplement.json`: three synthetic
  supplementary rows, and a `render.json` with the `pin-pair` inspection view
  and one `pin_to_base` joint close-up), `examples/two-bases-fixture/` and
  `examples/units-fixture/` (a real inch STEP and a centimetre STEP derived from
  the millimetre fixture by rewriting the unit context, in an inch, +Y-up scene
  with a nested group), all building with `tools/build-fixture.sh`.
- The enclosure snapshot (Windows per-part export, 37 parts, 155 occurrences)
  builds as a draft inventory with six subassembly inspection views (caster,
  panel and toggle-clamp assemblies, the three frames) from an ignored copy
  under `build/enclosure-snapshot-991056/project/` (its local `render.json`
  sets the 400 000-triangle line budget and the inspection groups; the Linux
  agent adopts it as `project-overlay/render.json`); the evidence runs on the
  share hold its outputs. The CAD agent accepts that geometry as a CAD
  reference; stock, BOM and sequence are not approved, and the documents say
  so. The enclosure's `supplement.json`, `joint_views` and inventory stock
  record come from the Linux agent's recipe (its 2026-10-22 overlay, staged in
  the ignored copy and recorded in the evidence run); nothing of them is
  authored here.
- Receipts at every stage; later stages refuse stale, partial or failed inputs.

## Before changing the renderer or contract

Run the fixtures and the tests first; they are the regression baseline. Keep the
rule that `approach` offsets are hints, that canonical poses are restored and
verified after each view, that an inspection view never moves, hides or
reorders anything inside its group, that asset units and scene units convert
separately, and that FreeCAD geometry is millimetres whatever the STEP declares
(the declared unit is provenance, compared with the manifest, never applied to
coordinates). If a production field is needed, add it to docs/input-contract.md
and the validator together, and tell the Windows agent through the mailbox.
Any new `render.json` knob or CLI flag goes to the Linux CAD agent too, which
owns the project-side configuration.

## Suggested next work

1. The enclosure now builds with the Linux agent's overlay (`supplement.json`
   with 20 family rows, 16 `joint_views`, a stock record on every inventory
   row; evidence run `2026-10-22-documentation-enclosure-supplement-01`). Next:
   the Linux agent adjusts joint instances or directions from the per-view
   notes in that reply; rebuild with `--reuse` (only changed close-ups render).
   Do not invent rows or views.
2. Peter's review of the picture-led inventory, the subassembly pages and the
   new supplementary section (labels, card size, inch equivalents, whether
   the supplementary table belongs in the technician PDF as decided).
3. A reviewed sequence for one small subassembly from the project team (the
   caster or panel assembly already has an inspection view); then per-step view
   overrides, `tools` and `checkpoints` per step, moves/removals as declared
   operations.
4. Line art on full-assembly views: Freestyle stays off above the budget (the
   enclosure overview is reused from the 32-minute run). Evaluate Grease Pencil
   Line Art in background mode before raising it; do not block on it.
5. No further group instances beyond `:1` for now (Linux, 2026-10-22); add
   them only when the project team names them.
6. A MkDocs wrapper page with the static fallback, reusing the atlas and PCB
   site templates; a joystick atlas view through `render.py` as a regression.

## What remains with the CAD/project agents

Accepted Inventor/Vault versions, export completeness, production placements,
stock counts (the inventory stock record and the supplement rows are produced
by the project's recipe from its sheets; this repository only validates and
prints them), the joint classifications and the supplementary rows' statuses,
a technician-reviewed order and a physical walkthrough. A refresh-stable
occurrence key is the one unmet exporter request (occurrence ids are
snapshot-scoped and labelled so). Nothing rendered here says the enclosure is
complete or buildable, and no supplementary row is an approved purchase.

## Finish a session

Update .agents/PLANS.md, write evidence under a fresh UTC-dated directory on the
share, post a timestamped reply in the mailbox and refresh
`status/documentation.json`. Leave commits and publication to Peter.
