# mechanical-docs living plan

## Objective

Generate visual inventories and reviewed assembly instructions from versioned
CAD geometry and structured procedures, using open-source tools, as matching
HTML and PDF.

The direction of the wider mechanical CAD work is in the sibling
`mechanical-cad` repository (`docs/direction.md`). Finished checkpoints, with
their measurements and evidence runs, are in .agents/HISTORY.md.

## Current state (2026-11-10)

- The pipeline is implemented end to end: manifest loader, FreeCAD mesh stage,
  Blender render stage, optional viewer export, document stage (HTML and Typst
  PDF from one `manual.json`), output checker. README.md lists the commands and
  docs/next-agent.md the modules.
- Three synthetic fixtures build end to end. The enclosure snapshot (37 parts,
  155 occurrences) was last built on 2026-10-23 as the draft phase-1 manual:
  compact PDF 59 pages, appendix 77 pages, 33 checks passed each. That package
  is published by the enclosure project; nothing of it is tracked here.
- Everything the enclosure manual says is `draft`. Its step order was written by
  the project and has not been reviewed. Peter is assembling the enclosure from
  it and taking notes.
- Run on 2026-11-10: the pure-Python suite, 124 passed and 2 skipped (the two
  FreeCAD-gated tests, outside the CAD role), before and after PyYAML was taken
  out of the base and publish Guix roles (nothing imports it). Not run that day:
  the fixtures, the CAD stage, any render or manual build.
- Layout proposal (`mechanical-cad/docs/layout-proposal.md`, not accepted): the
  enclosure is to be re-exported as one directory per Vault file, and this
  pipeline keeps reading a `scene.json`, then written by a flatten step in
  `mechanical-cad`. No change is planned here for it. Render reuse is gated on
  the hashes of the scene and asset files, so a re-keyed or re-exported project
  renders every view once more; that one full render is planned after the
  re-export. On 2026-11-10 a dry-run conversion of the enclosure was flattened
  by `mechanical-cad` and loaded here with `inspect`, with the phase-1
  manifests re-keyed to the new part ids: same counts, same finding, same
  inventory, build scope and steps as the original project. Only `inspect`
  ran; nothing was meshed or rendered.

## Next work

1. Peter's notes from the physical build and his corrected `instructions.json`.
   Re-render with `--reuse` on the latest receipt (only the overview and the
   steps whose state changed are rendered), rebuild both manuals, run `check`,
   inspect the changed pages. Publication into the project is the project's
   step (`assembly/publish_manual.py` there).
2. Whatever his notes ask of the documents themselves (cards, labels, views,
   step pages). Nothing is known yet.
3. After the layout is accepted and the enclosure re-exported: one full render
   from the flattened scene, and a comparison of that manual with today's by
   parts, quantities, steps and checks.

## Open items

Proposed to Peter on 2026-11-10, not approved, not started:

- A single-part preview: render one STEP without a hand-written scene, so
  authored parts can be looked at with this renderer.
- Reading the project's `materials.json` for appearances (assigned to this
  pipeline by `vault-cad-tools/docs/authoring-and-materials.md`, section 5).
- Taking the STEP validity, unit and volume checks of `cad_mesh.py` from
  `mechanical-cad` once it has them.

Carried from earlier checkpoints:

- Instruction model: close-up views, per-step view overrides, moves and
  removals, tools, checkpoints.
- Line art on full-assembly views. Freestyle is off above the line budget, so
  the overview and the exploded view have no outlines. Evaluate Grease Pencil
  Line Art in background mode. Not blocking.
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
