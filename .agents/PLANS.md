# mechanical-docs living plan

## Objective

Generate visual inventories and reviewed assembly instructions from versioned
CAD geometry and structured procedures, using open-source tools. First deliver
one useful small example as HTML and PDF, then process the enclosure's accepted
STEP/assembly exports when available.

## Current checkpoint — 2026-10-22 (technician inventory, subassembly inspection views, unit regression)

Work packet from the Linux CAD agent (`to-documentation/20261022T131939Z-…`),
done while Peter was away; all output stays `draft`.

- [x] Picture-led parts inventory: one card per part (badge, large picture, short
  label from the exporter's name, overall size with inch equivalents for inch
  assets, the CAD instance count labelled `CAD qty` with a note that it is not a
  purchase quantity, a blank counted box). Vault ids, occurrence paths and hash
  tables moved to `manual.json`/`build-receipt.json` and to an optional printed
  technical appendix (`manual --appendix`); the default build record is compact.
- [x] Long-part thumbnails: a part whose longest extent is at least 4× the next is
  turned with its long axis along X and drawn 2:1 wide, plus an end view looking
  straight along the axis (`part-<id>-end.png`); the inventory shows both. Seven
  enclosure extrusions qualified; all other thumbnails were reused unchanged.
- [x] Isolated subassembly inspection views (`render.json` `inspection_groups` or
  `--groups`): every occurrence under the group at its canonical pose, framed
  alone, hotspots, occurrence ids/parent/path in the receipt; one page each with
  a parts list and the statement that it is not an assembly step. Nothing is
  exploded or hidden inside a group. Rendered for CASTER ASSEMBLY:1, PANEL
  ASSEMBLY:1 and TOGGLE CLAMP ASSEMBLY:1 of the accepted snapshot.
- [x] `--reuse DIR`: views copied from an earlier complete receipt made from the
  same inputs, meshes, engine and quality, each marked `reused_from`; the
  enclosure rebuild rendered only the changed and new views and kept the
  32-minute Freestyle overview. The enclosure's local `render.json` caps line
  art at 400 000 visible triangles so no full-assembly view runs Freestyle.
- [x] Unit regression: `examples/units-fixture` (a real inch STEP written as
  Inventor writes it, a centimetre STEP, the millimetre original; an inch, +Y-up
  scene with a nested group and inch approach offsets). Pure-Python tests pin the
  derivation (coordinates byte-identical, only the unit context rewritten) and
  the world poses; `tests/test_cad_stage.py` runs FreeCAD on it (254/1000/10 mm
  read back) and requires an asset declared in the wrong unit to be refused.
  82 pure-Python tests, 2 FreeCAD-gated.
- [x] Contract wording: flexible assembly occurrences already have their own
  group ids and child poses (definitions may be shared, instance poses may not);
  occurrence ids are snapshot-scoped and labelled so. Status wording updated:
  the geometry is accepted as a CAD reference by the CAD agent; quantities are
  CAD instance counts, not stock or an approved BOM.
- [x] Added priority (Linux, 13:29 and 13:46 UTC): inspection views of the three
  frames as well (TANK SUPPORT FRAME:1, CAMERA FRAME:1, FREE STANDING FRAME:1:
  tank supports, camera/spring plates, extrusion joints, casters on the frame);
  coincident same-part occurrences recorded by the loader as a finding, printed
  on the status block and the part's card (the enclosure's two coincident tanks:
  the CAD count of 3 is flagged, no source instance deleted); an interface for a
  supplementary (non-geometric) inventory proposed in the mailbox, not
  implemented until the Linux agent confirms the field names.
- [ ] Peter's review of the new inventory pages; the project team's choice of
  which further group instances need inspection views; the supplementary
  inventory contract (after the Linux agent's answer).

## Previous checkpoint — 2026-10-21 (first implementation session, Cycles follow-up, first production snapshot)

- [x] Record scope, requirements, architecture and incoming-agent instructions.
- [x] Review reusable joystick atlas/PDF code and shared PCB tooling (docs/reuse.md).
- [x] Define the draft-1 input contract; implement exactly its milestone subset with
  explicit rejection of everything else (`mechanical_docs/manifest.py`; 76 pytest
  tests across manifest, transforms, procedure, GLB, geometry, settings, document,
  STEP units, names).
- [x] Synthetic three-part fixture generated and geometry-checked (FreeCAD 1.1.3).
- [x] `inspect` command: validated parts, occurrences with resolved world transforms
  (pins at X = −25/+25 mm under the +10 mm parent), steps with cumulative state,
  inventory reconciliation, input hashes.
- [x] CAD stage `cad_mesh.py` (FreeCADCmd): STEP validity, bounds, volume; per-face
  tessellation; winding by signed volume; mesh volume within 0.13 % of the B-rep;
  one GLB per part in metres/+Y up with the conversion recorded; `meshes.json`.
- [x] Render stage `render.py` (Blender 4.5.10, EEVEE Next): part thumbnails,
  overview, step and result images with subdued previous parts, highlighted
  additions, approach arrows, one fixed orthographic camera per procedure;
  hotspots; mesh-bounds and pose-restoration checks in `render-receipt.json`.
- [x] Document stage: `manual.json` → static HTML (web-only callouts and count
  inputs, print rules) and Typst → PDF (one page per step); build receipt.
- [x] `check` command: HTML/PDF/manual.json agreement (inventory, quantities, step
  order, review state), link/image resolution, page rasters, greyscale copies.
- [x] Second scene `examples/two-bases-fixture` (centimetre scene, millimetre assets,
  nested groups, a station rotated 90°, six occurrences, a two-part step). It
  caught an asset-vs-scene unit bug in the render stage, now fixed and unit-tested.
- [x] Both fixtures build end to end with `tools/build-fixture.sh`; all checks pass.
- [x] Pixi `render` environment with the official `bpy` 4.5.14 wheel (`pixi.toml`,
  `pixi.lock`, linux-64): OpenImageDenoise verified by assignment. Cycles is now
  the default engine; the Guix Blender route stays on EEVEE (no denoiser there).
  Shadow-catcher floor only on thumbnails and the overview (it quadruples a
  Cycles view's time). Both fixtures rebuilt with Cycles; all checks pass.
- [x] First production sample loaded: Windows `part-assets/` export (37 parts, 16
  groups, 155 occurrences, inch/mm/cm assets, +Y-up native frame). The loader
  now accepts its provenance/BOM/flag fields, applies a declared `basis_to_z_up`
  once at the root, checks exporter world matrices against the hierarchy
  (max 1.7e-11 mm), allows free-form ids (slugs for file names), tolerates a
  UTF-8 BOM, and builds without `instructions.json` (inventory and overview only).
  `inventory-template` writes a draft inventory. 76 tests.
- [x] CAD stage hardened on real geometry: declared STEP unit read from the file
  and compared with the manifest (21 in, 15 mm, 1 cm, all agree); FreeCAD's
  millimetre normalisation; optimal bounding boxes (exporter extents agree
  within 1.445 mm); two tessellations compared (a B-rep volume integral that
  disagrees with both is a recorded warning, seen on MCMASTER 47065T245);
  mesher fallbacks for sliver faces. Enclosure meshes build; see the evidence run
  for the inventory document.
- [x] Production-scale render cost bounded. The first enclosure overview took 93
  minutes: Freestyle over 5.2 million triangles (threaded McMaster hardware at
  0.05 mm deflection), not Cycles. Now `cad_mesh.py --max-triangles` (default
  50 000 per part, deflections coarsened ×1.6 per attempt from a fresh shape,
  attempts recorded) brings the scene to 2.4 million triangles, and
  `lines.max_triangles` (3 million; 400 000 for previews) renders a view without
  line art when the visible geometry exceeds it, recorded per view and warned.
  `--no-lines` for timing runs. The normal-orientation check measures disagreeing
  mesh area (slivers are many but tiny; a thread modelled as one B-spline face
  folds about 1 % at any deflection) and is a problem only above 5 %: shading,
  not identity. The inventory-only manual no longer fails the greyscale check
  (not-run); the PDF build record wraps.
- [x] Coordinate the production export contract with the CAD/Windows agent:
  the two open questions (per-asset units: yes; flexible instances: one group
  definition with per-instance placements) answered via the mailbox and the
  wording clarified in docs/input-contract.md; a refresh-stable occurrence key
  remains the one unmet request (ids are snapshot-scoped and labelled so).
- [ ] Author and review a real assembly sequence for a small enclosure subassembly
  with the project team (not this tool's call); until then production output is
  inventory-only.
- [ ] Retain the joystick example as a second consumer/regression for the
  extracted rendering behaviour.
- [ ] MkDocs site assembly and the narrative Pandoc/Typst builder for prose chapters.
- [ ] Close-up views, moves/removals, tools and checkpoints in the instruction model.

## Next implementation sequence

1. Review the picture-led inventory and subassembly pages with Peter: card
   size, labels, inch equivalents, which long parts need the end view, which
   McMaster rows lack part numbers, and whether purchased kits need a separate
   inventory classification.
2. Ask the project team for a first reviewed sequence (one subassembly, e.g. the
   caster or panel assembly that already has an inspection view) and author
   `instructions.json` for it; add per-step close-ups, tools and checkpoints to
   the instruction model.
3. Evaluate Grease Pencil Line Art in background mode against Freestyle on the
   enclosure overview (32 min with Freestyle at 2.4 M triangles, 51 s without);
   full-assembly views stay without outlines under the 400 000-triangle budget
   until then. Not blocking.
4. Inspection views for further group instances when the project team names
   them (CASTER ASSEMBLY:2-4, the frames); a camera direction per group in
   `render.json` if the default direction hides something.
5. Supplementary inventory (hardware not modelled in CAD, consumables, tools)
   as a separate validated manifest derived from the project's procurement
   sheets: listed per joint under the subassembly pages, quantities unknown
   until confirmed, never summed with CAD counts, no geometry invented.
   Implement once the Linux agent confirms the proposed field names.
6. Add close-ups (per-step view override) and the static fallback for
   interactive extras in a MkDocs page.
7. Reproduce one or two joystick atlas views through the generic renderer as a
   regression; decide where shared materials live (kicad-libs overlap).
8. Review printed pages with a technician; add the physical-validation record
   fields before any manual claims more than `draft`.

## Decisions and boundaries

- A broad repository name with assembly manuals as the first feature.
- Reuse existing renderer, overlays and PDF code gradually; no wholesale move of
  project scripts or large assets. Existing source projects remain operational
  and untouched (joystick checkout still at 22aa7544, clean).
- Keep KiCad and Autodesk adapters separate. Linux documentation generation
  requires no proprietary CAD software.
- Draft-1 is an illustrative contract; stable identities and explicit units/frames
  take priority over compatibility by guessing. `approach.end_offset` must be zero.
  Production fields are accepted as optional data, never as licence to guess:
  suppressed or mirrored occurrences are rejected, reference-only geometry is
  never counted as installed, and `required` means installed occurrences.
- The enclosure snapshot's geometry is accepted as a CAD reference by the Linux
  CAD agent (2026-10-22); its stock, BOM and sequence are not approved, and the
  inventory document says on its first page that quantities are CAD instance
  counts. The local copy lives under ignored `build/enclosure-snapshot-991056/`,
  not in Git; its `render.json` (line budget, inspection groups) is project
  configuration and goes to the Linux agent as an overlay through the mailbox.
- Subassembly inspection views are parts views: canonical poses, nothing
  exploded, hidden or reordered, labelled as not a step. The Windows two-panel
  exporter fixture is no longer needed as a tracked inch example: the units
  fixture provides a real inch STEP without copying project data.
- Cycles with OpenImageDenoise is the reference look and the default engine
  (Peter's expectation; matches the joystick atlas). EEVEE Next is for previews
  and for the Guix Blender, which lacks the denoiser; receipts record both.
- Track compact inputs; large generated outputs stay in `build/` or the evidence share.
- Native CAD acceptance, stock counts and the real assembly order remain the
  project team's; the fixtures prove tooling, not an enclosure procedure.

## Verification and handoff

Observed on 2026-10-22 (Debian 13 host, Guix 1.5.0, Pixi 0.63.2): Python 3.12.12,
pytest 9.0.2 (84 passed, 2 skipped outside the CAD role; the 2 FreeCAD-gated
tests pass in `guix shell -m manifest.scm -m .guix/manifest-cad.scm`), FreeCAD
1.1.3, bpy 4.5.14 (Cycles, OpenImageDenoise), Typst 0.15.0, Poppler 22.09.
Enclosure snapshot (pilot-02, 37 parts, 155 occurrences, meshes of 2026-10-21
reused): seven wide thumbnails 21 to 22 s, seven end views 3.4 to 3.9 s, three
subassembly views 62 to 82 s (Freestyle on 55 000 to 91 000 triangles), 17
views rendered and 31 reused in 6 min 25 s; the three group views were then
re-rendered with the flat-group camera rule (103 to 127 s each while the
fixtures were rebuilding in parallel), 45 reused; then the three frames (tank
support frame 147 s with outlines at 343 000 triangles; camera frame 75 s and
free-standing frame 49 s without outlines, over the 400 000 budget), 48 reused.
Compact inventory PDF 16 pages (five card pages, six subassembly pages,
overview, build record), with appendix 25 pages; 17 checks passed, 2 not
applicable without steps, for both. The loader's coincident-occurrence finding
reports the two coincident tanks (deviation 2.5e-12 mm) on the status block and
the tank's card.
Fixtures rebuilt end to end with Cycles after every change: three-part 8 views
190 s, 6 pages, 18 checks; two-bases 10 views 163 s, 8 pages, 18 checks;
units 10 views 340 s (one `stand` inspection view, wide pin thumbnail and end
view), 8 pages, 19 checks; all passed. FreeCAD reads the units fixture as
254 × 254 × 762, 1000 × 600 × 80 and 10 × 10 × 30 mm. Card pages, subassembly
pages, the long-part thumbnails and end views were inspected by eye at 60 dpi
and at full size. Not run: a real browser print test, any physical build,
Grease Pencil Line Art, a technician review. Inside a Guix shell Pixi needs
`CONDA_OVERRIDE_GLIBC` set to the host glibc; concurrent `pixi run` invocations
in one workspace can fail, so the second renderer was started through the
environment's Python directly. Evidence and the mailbox reply are under the
shared coordination area named in the ignored local handoff. No commits, pushes
or publication were made.
