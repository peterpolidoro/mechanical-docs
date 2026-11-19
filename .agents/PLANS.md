# mechanical-docs living plan

## Objective

Generate visual inventories and reviewed assembly instructions from versioned
CAD geometry and structured procedures, using open-source tools, as matching
HTML and PDF.

The direction of the wider mechanical CAD work is in the sibling
`mechanical-cad` repository (`docs/direction.md`). Finished checkpoints, with
their measurements and evidence runs, are in .agents/HISTORY.md.

## Current state (2026-11-19)

- The pipeline is implemented end to end: manifest loader, FreeCAD mesh stage,
  Blender render stage, optional viewer export, document stage (HTML and Typst
  PDF from one `manual.json`), output checker, and since 2026-11-19 pictures
  of a scene outside a manual. README.md lists the commands and
  docs/next-agent.md the modules.
- Three synthetic fixtures build end to end; all three were built on
  2026-11-19 at preview quality with the Guix Blender, and all their checks
  passed.
- **The enclosure.** Its published manual is the draft phase-1 package of
  2026-10-23 (compact PDF 59 pages, appendix 77 pages, 33 checks passed
  each), published by the enclosure project; nothing of it is tracked here.
  Everything it says is `draft`; its step order was written by the project
  and has not been reviewed. Peter is assembling the enclosure from it and
  taking notes. The project was converted to the layout of `mechanical-cad`
  and merged on 2026-11-12: its scene is now flattened there
  (`make reference-scene` in the project), with readable part keys and AP242
  files. This pipeline ran on the converted project that day, the whole of
  it at preview quality (staging, inspect, meshes, 88 renders, manual,
  check: all passed), and the manual has the steps, joints, quantities and
  groups of the published one. No full-quality render has been made of it.
  On 2026-11-19 the manual was built again from the project as it stands,
  with the code as committed that morning and from a clean clone: 86 views
  with Cycles at preview quality in 41 minutes (the two largest subassembly
  views, with outlines, about 11 minutes each), a PDF of 59 pages as the
  published one has, and all 32 checks passed; the viewer stage was not
  run. It is in the project's ignored `.cache/manual-preview-2026-11-19/`.
- **Finishes (2026-11-19).** Peter decided that day that what a picture draws
  each part with is one hand-edited file for the whole project
  (`finishes.toml`, in `mechanical-cad`'s layout). `mechanical-cad`'s flatten
  step derives `finishes.json` from it beside `scene.json`, and this
  pipeline reads that file: a part is drawn in the look `render.json` names
  for it, else in its finish, else in the default look (`looks.py`). A
  finish is a colour written in sRGB, how metallic, how rough and how
  opaque; a translucent part shows what lies behind it. The file is a render
  input and no geometry input. The render receipt records what every part
  was drawn with, and `--reuse` judges every view by the parts it shows in
  their own looks, so a changed finish, or a changed `looks` entry, renders
  only those views again. On the two-bases fixture, 11 views: a changed
  finish of the base rendered 5 and copied 6; a changed finish of the pin,
  which `render.json` overrides, rendered none. docs/input-contract.md,
  "Finishes", is the contract.
- **A picture outside a manual (2026-11-19).** `mechanical_docs/still.py`
  draws a scene alone, or one subassembly of it, from a named side, with no
  inventory and no instructions; the CAD stage meshes such a directory. The
  view names are those of `mechanical-cad`'s `tools/picture.py`. It has its
  own exposure (`still_exposure`, -2.5 stops): the studio of the render
  stage lights a face that looks up about seven times as brightly as its
  colour, so that at exposure 0 a mid-grey finish is white on top. A
  manual's own views keep exposure 0.
- **Motion (2026-11-19), stage 7.2 of `mechanical-cad`'s plan.**
  `mechanical_docs/motion.py` draws three sequences from the directory a
  still is made from and writes each as frames, a video and a receipt: a
  turntable of the scene or of one subassembly, at one scale for the whole
  turn and with the lights turning with the camera; the top-level groups
  moving apart to the offsets of the exploded view, and back; and, for a
  project with instructions, the steps in the manual's order, what each
  adds arriving at its seat. Blender's own FFmpeg writes the video on both
  routes (H.264, or VP9 with `--webm`), and the file is read back and held
  to its frame count. Outlines and the floor are off in frames unless asked
  for. What needs no Blender is in `timeline.py`, with tests. On the
  enclosure, Cycles at preview quality, 960 x 720: a turntable of one tank
  support frame (72 frames, 296 s), of the whole enclosure (72 frames,
  176 s) and the exploded sequence there and back (95 frames, 275 s); with
  EEVEE the whole enclosure takes 0.7 s a frame. And the steps of the
  enclosure's staged project, its eighteen draft steps in their order: 468
  frames, 19.5 s of video, in 129 s with EEVEE in the Guix Blender; the
  frame, the camera frame, the panels and the top arrive in that order. A
  joint moved through its range is not built: the layout has no record for
  joints. Not run: a video at full quality, and a steps sequence with a
  perspective view.
- **Smaller, the same day.** The CAD stage takes its own options after a
  bare `--` (`--pass PROJECT OUT -- --max-triangles 20000`), which
  FreeCADCmd 1.1.3 otherwise takes for its own. The manual's viewer models
  give a part the look that was chosen for it, in `render.json` or in
  `finishes.json`, as a glTF material named after it; a project that chose
  nothing gets the same bytes as before. Nobody has looked at such a model
  in a browser.
- **Outlines on whole assemblies, measured and not built** (2026-11-19).
  Grease Pencil Line Art runs without a window in both Blenders and draws
  the whole enclosure, 2.44 million triangles, in under a minute where
  Freestyle took 32 minutes; drawn in front, it reads like a Freestyle
  picture. Left open before it can stand in: some edges of the thin-walled
  tank come out broken, two widths for subject and context, perspective
  views, and what `--reuse` makes of a view that gains lines. The modifier
  must be added only for the render call, or it is worked out again at
  every scene update. docs/environment.md has the measurements.
- Run on 2026-11-19: the pure-Python suite, 168 passed and 4 skipped; with
  FreeCAD, 172 passed. Rendered that day with Cycles and with EEVEE: stills
  of the two-bases fixture and of a scratch scene. And of the enclosure,
  from its scene flattened by `mechanical-cad` with the project's draft
  finishes into a scratch directory and meshed there (37 parts, every check
  passed), with Cycles at preview quality, 1200 x 900: the whole enclosure,
  155 occurrences, in 10 s without outlines (2.4 million visible triangles
  are over the preview budget for them), and one tank support frame alone,
  its clear tank and platform seen through, with outlines, in 225 s. Not
  run: `viewer.py` (only a message changed in it), a manual with Cycles, a
  manual of a project that has finishes other than the fixture, a
  full-quality render of anything but stills of a fixture.

## Next work

1. Peter's notes from the physical build and his corrected `instructions.json`.
   Render the converted project at full quality (its part ids and files
   changed with the conversion, so every view is rendered once), rebuild
   both manuals, run `check`, inspect the changed pages. After that a
   corrected instruction file needs `--reuse` only. Publication into the
   project is the project's step (`assembly/publish_manual.py` there).
2. Whatever his notes ask of the documents themselves (cards, labels, views,
   step pages). Nothing is known yet.
3. How a manual's own views are exposed when a project has finishes. With
   the studio as it is, a finish lighter than a dark grey comes out white on
   top in every view of a manual, as the palette's light entries do. Until
   Peter has seen it and said what he wants, a project's finishes are for
   stills and videos, and the enclosure's recipe does not hand
   `finishes.json` to the manual. For him to look at: six of the
   enclosure's views as the manual draws them today, and with the project's
   finishes at exposure 0, -1.5 and -2.5, on one sheet in that project's
   ignored `.cache/pictures/manual-views-finishes-and-exposure.png`. At 0
   the light finishes are white as before and black ABS is a mid grey; at
   -1.5 the colours read and the pages stay light; at -2.5 the colours are
   nearest their finishes and the pictures are heavy. A thin framing
   extrusion is dark at every setting: its outlines fill it.
4. A joint moved through its range, as video: it waits for joints and poses
   as records in the layout, which is Peter's word in `mechanical-cad`.
5. Outlines on whole assemblies with Line Art, if the four points left open
   above are worth settling: the published manual's overview and most of
   its steps have no outlines today.

## Open items

Proposed to Peter on 2026-11-10, not approved, not started:

- A single-part preview: render one STEP without a hand-written scene, so
  authored parts can be looked at with this renderer. Since then
  `mechanical-cad`'s `tools/picture.py` draws a part without this pipeline,
  and `still.py` draws a scene alone; one part through this renderer still
  needs a scene written for it.
- Taking the STEP validity, unit and volume checks of `cad_mesh.py` from
  `mechanical-cad` once it has them.

Overtaken: reading the project's `materials.json` for appearances (proposed
the same day). A project's finishes are what gives a part its look.

Left by the finishes work of 2026-11-19:

- A finish belongs to a part. A finish for one body of a part or for one
  occurrence has no place, in the layout or here.
- A palette entry's coat is not carried into the viewer models, and the
  flat material stays in the file when no part uses it.
- EEVEE draws a translucent finish by blending and shows blotches in the
  shadow near it; Cycles is the reference for such a part.
- No translucent finish has been tried on anything larger than a fixture
  with the manual's views.

Carried from earlier checkpoints:

- Instruction model: close-up views, per-step view overrides, moves and
  removals, tools, checkpoints.
- Line art on full-assembly views. Freestyle is off above the line budget, so
  the overview and the exploded view have no outlines. Grease Pencil Line Art
  was measured on 2026-11-19 ("Current state"); not built in.
- The viewer GLBs were checked structurally; no record says anyone has looked
  at them in a browser. No browser print test has been run.
- A technician's review of printed pages, and the physical-validation record
  fields, before any manual claims more than `draft`.
- One or two joystick atlas views through this renderer as a regression, and a
  decision on where shared materials live (overlap with `kicad-libs`).
- Prose chapters (the Pandoc/Typst narrative builder) and a static fallback for
  interactive extras in a site page. The site generator lives in the enclosure
  project (`assembly/site_pages.py`); moving it here is expected, not scheduled.
- A refresh-stable occurrence key from the exporter. Occurrence ids are
  snapshot-scoped and labelled so.
- `pixi.toml` still lists PyYAML in its default environment. Remove it with the
  next deliberate update of `pixi.lock`, not before.
- The Guix roles use the session's package set. Pin the channels when
  `mechanical-cad` becomes a channel.

## Decisions and boundaries

- A broad repository name with assembly manuals as the first feature.
- Reuse existing renderer, overlay and PDF code gradually; no wholesale move of
  project scripts or large assets. The source projects stay operational and
  untouched.
- Keep KiCad and Autodesk adapters separate. Linux documentation generation
  requires no proprietary CAD software.
- Draft-1 is an illustrative contract; stable identities and explicit
  units/frames take priority over compatibility by guessing.
  `approach.end_offset` must be zero. Production fields are accepted as
  optional data, never as licence to guess: suppressed or mirrored occurrences
  are rejected, reference-only geometry is never counted as installed, and
  `required` means installed occurrences.
- The enclosure snapshot's geometry is accepted as a CAD reference
  (2026-10-22); its stock, BOM and sequence are not approved, and the documents
  say on their first page that quantities are CAD instance counts. A project's
  `render.json` is project configuration and belongs to the project.
- Subassembly inspection views are parts views: canonical poses, nothing
  exploded, hidden or reordered, labelled as not a step. Joint close-ups frame
  named occurrences and subdue or hide the rest of their context; they too are
  inspection views, never steps.
- Supplementary items are a separate manifest produced by the project's recipe,
  validated and printed here, never read from the project's sheets, never
  drawn, never added to CAD quantities; an unknown quantity stays null and
  prints as unknown. The one stock authority is `on_hand_each` with its
  attribution; the printed counted box is paper only. A family row cannot carry
  an integer quantity; a `specified` row needs a verified supplier part number.
  Rows with `scope: new_design` are appendix-only.
- Cycles with OpenImageDenoise is the reference look and the default engine.
  EEVEE Next is for previews and for the Guix Blender, which lacks the
  denoiser; receipts record both.
- Receipt checks are scoped to what a stage depends on: `meshes.json` is
  compared with the scene and asset hashes; `--reuse` and the manual stage
  compare render receipts with the scene, asset and instruction hashes (plus
  meshes, engine and quality for reuse). A changed inventory, supplement or
  build scope never forces a CAD or render re-run by itself; the manual
  re-reads them, and every receipt still records every input hash.
- A reused view is checked per view before it is copied (`reuse.py`). A lower
  line budget never discards an outlined image: the budget caps cost, it is not
  a look. Other appearance changes need `--views`.
- Project prose stays in the project. Nothing of the kind is authored here.
- Track compact inputs; large generated outputs stay in `build/` or on the
  shared evidence area.
- Native CAD acceptance, stock counts and the real assembly order remain the
  project team's; the fixtures prove tooling, not an enclosure procedure.
