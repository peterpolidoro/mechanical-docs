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
  2026-11-19 at preview quality with the Guix Blender, the last time when
  that day's work ended, and all their checks passed.
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
- **Since 2026-11-19, stage 7 of `mechanical-cad`'s plan** (the record of how
  each came about, with its measurements, is in .agents/HISTORY.md, "The
  record of 2026-11-19"):
  - *Finishes.* A part is drawn in the look `render.json` names for it, else
    in its finish of `finishes.json` (derived by `mechanical-cad` from the
    project's one `finishes.toml`, Peter's decision of that day), else in
    the default look. The receipt records the look of every part and
    `--reuse` judges each view by the parts it shows. The manual's viewer
    models carry the looks as glTF materials. docs/input-contract.md,
    "Finishes".
  - *Pictures outside a manual.* `still.py` draws a scene alone, or one
    subassembly, from a named side or a given direction, with `--up` where
    Z is not to be up in the picture, at an exposure of its own
    (`still_exposure`, -2.5 stops) that shows colours; a manual's views keep
    exposure 0.
  - *Moving pictures.* `motion.py` writes frames, a video (Blender's own
    FFmpeg) and a receipt for a turntable, an exploded sequence, a project's
    steps, a joint through its range and one pose going over into another.
    What needs no Blender is in `timeline.py` and `joints.py`.
  - *Joints and poses, against a draft.* `mechanical-cad` has a record of a
    project's joints and poses that Peter has not decided, and derives
    `motion.json` beside `scene.json` from it. `joints.py` reads it:
    a turn about a line or a slide along one, joints carrying joints, a
    joint that follows another at a ratio. `motion.py joint NAME` and
    `pose FROM TO` draw it, of the whole scene or of one subassembly
    (`--group`), and `still.py --pose NAME` or `--at JOINT=VALUE,...` draws
    one position. Nothing else reads the file. Drawn on the fixture with a
    file written by hand and on one real assembly (below).
    docs/input-contract.md, "Joints and poses", is the contract as built.
  - *Line Art.* `lines.outliner` in `render.json`, or `--outliner` of
    `render.py`, `still.py` and `motion.py`, says what draws outlines:
    `freestyle` (the default, as before), `line-art`, or `mixed` (Freestyle
    within its budget, Line Art above it). No project sets it.
    docs/environment.md has what was found and measured.
  - *A part that is surfaces.* The CAD stage calls a part without a solid a
    problem, as before, unless `--surface-parts` names it; it is then
    meshed from its faces and recorded as a surface model whose volume is
    not checked.
- **The mechanical example, the first real joints drawn here** (2026-11-19).
  `mechanical-cad`'s project made of one STEP file of an assembly, 37 parts
  and 108 occurrences, flattened with its finishes and with a `motion.json`
  of five joints from that repository's draft record. Its switch is a
  supplier's model of surfaces, so its meshes are made with
  `--surface-parts d2f-01fl`. Drawn with EEVEE in the Guix Blender at
  1280 x 720, with Line Art's outlines: the lever of the first unit through
  its range, that unit alone, the lever's gear and the motor's turning
  against each other and the rod staying on its shaft (95 frames, 238 s);
  the first unit turning on the base plate through its arc slot, seen from
  above, the knob's screw staying in the slot from one end to the other (95
  frames, 346 s); the lever from its stop to its other pose and back; and a
  still with both units at the ends of their slots (4.6 s; 20.8 s with
  Freestyle). Every receipt's checks passed. The videos, the still and
  their receipts are in that project's ignored `.cache/pictures/poses/`, in
  `mechanical-cad`'s checkout. Not run on it: Cycles.
- Run on 2026-11-19 at the end of the day: the pure-Python suite, 221 passed
  and 6 skipped; with FreeCAD, 227 passed; the three fixtures' manuals at
  preview quality with the Guix Blender, every check passed. Not run with
  the code as it stood then: `viewer.py`, a manual with Cycles, a whole
  manual with Line Art, a manual of a project that has finishes other than
  the fixture, and a full-quality render of anything but stills of a
  fixture and four views of the enclosure.

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
4. A joint moved through its range as video, one pose into another, and a
   still at a pose are built against a draft (above). Left: Peter's word on
   the record of joints in `mechanical-cad`, after which `motion.json` is
   part of the contract and not a draft. Two things the real example
   showed. A scene is drawn in the frame it declares: the example's
   assembly declares none, so it is taken as Z up though the thing stands
   Y up, and every picture of it needs `--up`; whether a project made of
   one STEP file says its up axis is `mechanical-cad`'s to settle. And what
   moves is often behind what does not: the lever's gears face the other
   unit, so its videos draw one unit alone (`--group`).
5. Whether the enclosure's manual gets its outlines from Line Art where
   Freestyle draws none (`"lines": {"outliner": "mixed"}` in the project's
   `render.json`): Peter's to say, from the sheet named above. Its
   overview, its exploded view and the steps above the budget have no
   outlines today. What Line Art leaves as Freestyle does: on the whole
   enclosure the framing's many edges run together into dark bands; and a
   step whose additions lie behind what is already installed (the tank
   support frames, steps 16 to 18) gets no outline on them, since the
   ghosted parts hide edges as opaque ones do. Line Art's material masks
   could draw such edges through the ghosts; not tried. Not run with Line
   Art: a whole manual of the enclosure, and the viewer stage.

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
  the overview and the exploded view have no outlines unless a project hands
  them to Line Art, which is built behind a setting since 2026-11-19 ("Next
  work", 5).
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
