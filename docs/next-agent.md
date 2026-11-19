# Incoming documentation agent

The pipeline exists and runs on three synthetic fixtures and on the first
production snapshot: the enclosure builds as a draft phase-1 manual (front page
with the exploded view, parts cards, six subassembly inspection views, 16 joint
close-ups, 18 draft steps, viewer data).
Read AGENTS.md, README.md, docs/input-contract.md (implemented subset,
production fields, flexible instances, the inventory stock record, the
supplement contract, `joint_views`, stage outputs, exporter field request),
docs/environment.md (roles, FreeCAD and Blender quirks, render cost, budgets
and view reuse) and .agents/PLANS.md. Use .agents/handoff.local.md for the
mailbox and evidence paths; the tracked documentation stays usable without them.

## Direction since 2026-11-10

Read `mechanical-cad/docs/direction.md` and `docs/layout-proposal.md` in the
sibling repository before planning anything here. In short:

- The direction of the mechanical CAD work now lives there, and work that spans
  repositories runs from an agent session rooted there. An agent started here
  is the documentation role.
- The enclosure is to be re-exported into a new layout: one directory per Vault
  file, with a manifest per assembly. Under the proposal this pipeline keeps
  reading a `scene.json`; it becomes a derived file produced by a flatten step
  in `mechanical-cad`. The loader, renderer and manual are expected to stay as
  they are, and the project's curated manifests get a one-time re-key of part
  ids. Nothing here changes until Peter accepts the layout.
- Peter is assembling the enclosure from the published phase-1 manual and
  taking notes. Those notes, and his corrected `instructions.json`, are the next
  real input for this repository.
- Licence: 3-clause BSD, copyright Howard Hughes Medical Institute (`LICENSE`).
- Finishes and pictures outside a manual (2026-11-19, stage 7 of
  `mechanical-cad`'s plan; Peter decided that a project's finishes are one
  hand-edited file for the whole project). `mechanical-cad` derives
  `finishes.json` from it beside the scene; this pipeline reads that file
  (`manifest.py` `load_finishes`), draws a part in its finish unless
  `render.json` names a look for it (`looks.py`), records the look of every
  part in the render receipt and judges reuse by it (`reuse.py`), and draws a
  scene alone from a named side (`still.py`, `views.py`; the CAD stage meshes
  a directory without an inventory). Shown on `examples/two-bases-fixture`,
  whose base is translucent. docs/input-contract.md, "Finishes", has the
  contract and what the high-key studio does to a finish's colour. The
  manual's viewer models carry the looks as glTF materials since the same day
  (`viewer.py`, `looks.viewer_materials`); a project that chose no look has
  the one flat material and the same bytes as before. Read back into Blender,
  the materials are there with their numbers; nobody has looked at such a
  model in a browser. Not done: a finish per body or per occurrence, and a
  look at how a manual's own views should be exposed when a project has
  finishes.
- Moving pictures (2026-11-19, stage 7.2 of `mechanical-cad`'s plan):
  `motion.py` draws a turntable, an exploded sequence or the steps of a
  project as frames and as a video, from the directory a still is made from;
  `timeline.py` has what needs no Blender (where the camera stands at each
  frame, the one scale of a turn, how far apart the groups are, where a
  step's additions come from). Blender's own FFmpeg writes the video on both
  routes, so no package was added. A joint moved through its range and one
  pose going over into another are built against a draft (the same day,
  later): `mechanical-cad` derives `motion.json` beside the scene from a
  record of joints that is not yet part of its layout, `joints.py` reads it
  and says where a joint puts what it moves, `motion.py joint NAME` and
  `pose FROM TO` draw it (of the whole scene, or of one subassembly with
  `--group`), and `still.py --pose NAME` or `--at JOINT=VALUE,...` draws one
  position. A frame with whole poses is `Renderer.render_frame(worlds=...)`,
  and a turntable's lights go round its camera's axis
  (`Renderer.turn_lights(angle, pivot)`). Shown on the three-part fixture
  with a file written by hand, and on `mechanical-cad`'s mechanical example,
  the first real joints drawn here: a lever with its two gears, and a unit
  turning in its arc slot.
- The CAD stage takes its own options under FreeCADCmd since 2026-11-19,
  after a bare `--` (`--pass PROJECT OUT -- --max-triangles 20000`); before,
  FreeCADCmd took them for its own and stopped. One of them,
  `--surface-parts PART_ID,...`, names the parts that are models of
  surfaces: a part without a solid stays a problem, which stops the render
  stage, unless it is named there, and a named part that has a solid is a
  problem too.
- `--up` of `still.py` and `motion.py` (2026-11-19) names what points up in
  a picture whose camera stands still. A scene is drawn in the frame it
  declares; one that is declared Z up and stands otherwise, as the
  mechanical example's does, comes out lying on its side without it.
- Outlines on full-assembly views: Grease Pencil Line Art is built into
  `render.py` since 2026-11-19, behind `lines.outliner` in `render.json`
  (`freestyle`, the default; `line-art`; `mixed`) and `--outliner` of
  `render.py`, `still.py` and `motion.py`. It draws the enclosure's overview in a quarter
  of a minute where Freestyle took 32. A view's record says what drew its
  outlines, and `reuse.py` judges by it. No project has switched it on.
  docs/environment.md has what was found on the way and the measurements.
- Still open here: a single-part preview (render one STEP without a
  hand-written scene), proposed on 2026-11-10 and neither approved nor
  started; `mechanical-cad`'s `tools/picture.py` draws a part without this
  pipeline. Reading the project's `materials.json` for appearances, proposed
  the same day, is overtaken by the finishes above.
- The shared directory's location on Peter's workstation is in the ignored
  `.agents/handoff.local.md`. Paths in older notes and messages may no longer
  exist there.

The sections below describe the state of 2026-10-23 and remain accurate for the
code.

## What exists

- `mechanical_docs/`: `manifest.py` (validation, production fields, +Y-up basis,
  the inventory stock record, `supplement.json`), `names.py` (slugs for
  free-form ids), `stepinfo.py` (declared STEP unit), `transforms.py`,
  `procedure.py`, `gltf.py` (single-mesh and multi-node GLB writers),
  `geometry.py`, `receipts.py`, `reuse.py` (which earlier views are stale
  under new settings or looks), `looks.py` (what each part is drawn with:
  the look `render.json` names, else its finish, else the default),
  `views.py` (the named camera positions of a still), `timeline.py` (a
  moving picture's frames: a turntable's camera, an exploded sequence, the
  steps, a joint's or a pose's values), `joints.py` (`motion.json`: the
  joints and poses of a scene, and where a joint puts what it moves),
  `explode.py` (which
  top-level groups the exploded
  view moves and by how much), `render_settings.py` (looks, budgets,
  long-part thumbnail rules, `inspection_groups`, `joint_views`,
  `exploded_view`), `cad_mesh.py` (FreeCADCmd, triangle budget), `render.py`
  (Blender, Cycles default, line budget, wide thumbnails and end views for long
  parts, `--groups` subassembly inspection views, `joint_views` close-ups,
  the exploded view, `--reuse` of earlier views), `still.py` (Blender: a
  picture of a scene alone, outside a manual), `motion.py` (Blender: a
  turntable, an exploded sequence, a project's steps, a joint or a pose as
  frames and video),
  `viewer.py` (bpy: the two
  viewer GLBs with decimation and anchors), `document.py` + `html.py` + `typst.py`
  (front page with the overview and the exploded view with page references,
  picture-led parts cards, supplementary items, subassembly pages with the
  definition's instance count and totals, joint pages with hardware lists,
  compact build record, `viewer/hotspots.json`, the build scope's phase
  quantities, checklist and step chapters, `--appendix`), `checks.py`,
  `cli.py` (`inspect`, `inventory-template`, `manual`, `check`). `tests/` has
  221 pure-Python tests (all passing on 2026-11-19) plus six in
  `tests/test_cad_stage.py`, which run FreeCAD on the units fixture when
  `FreeCADCmd` is on PATH (the CAD role) and are skipped otherwise.
- `examples/three-part-fixture/` (now with `supplement.json`: three synthetic
  supplementary rows, a `render.json` with the `pin-pair` inspection view,
  one `pin_to_base` joint close-up and an exploded-view spread, and a
  `build-scope.json` deferring pin B), `examples/two-bases-fixture/` (since
  2026-11-19 with a `finishes.json`: a translucent base, and a pin whose
  finish `render.json` overrides) and
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

1. The enclosure now builds as the phase-1 draft manual: front page (overview,
   exploded subassembly view with page references), picture-led cards with
   this-build/conditional/deferred quantities, the verification checklist,
   subassembly pages with instance counts, joint close-ups, 18 draft steps
   (two conditional, one deferred) and the viewer data (`viewer/`) that the
   Linux agent's `assembly/site_pages.py` turns into the site. Evidence runs
   `2026-10-23-documentation-manual-fixes-01`, `-front-page-and-viewer-01`,
   `-phase-1-01`. A corrected `instructions.json` after Peter's physical build
   re-renders only the steps whose state changed (`--reuse` on the latest
   receipt); a changed `build-scope.json` needs no render unless a step's
   additions or installed-before set change. Do not invent rows, views or order.
2. Peter's review of the front page, the phase-1 cards and checklist, the
   step pages and the exploded view's default offsets (`exploded_view.groups`
   overrides in `render.json` if he wants the toggle clamps closer).
3. Open the viewer GLBs in a browser (model-viewer) once Linux's site build
   is up; fix normals, scale or anchor placement if anything looks wrong.
4. Line art on full-assembly views: Freestyle stays off above the budget (the
   overview and the exploded view are without outlines), and Grease Pencil
   Line Art draws them when the project's `render.json` says
   `"lines": {"outliner": "mixed"}` or `"line-art"`. Whether the enclosure's
   manual is drawn so is Peter's to say; four of its views both ways are on
   one sheet in that project's ignored `.cache/pictures/line-art-comparison.png`.
5. No further group instances beyond `:1` as inspection views for now
   (Linux, 2026-10-22); the pages already count every instance of a definition.
6. The site pages are generated by the Linux agent from `manual.json` and
   `viewer/hotspots.json`; a later move of that generator into this
   repository is expected, not now. A joystick atlas view through
   `render.py` as a regression.

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
