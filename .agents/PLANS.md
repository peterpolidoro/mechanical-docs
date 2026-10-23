# mechanical-docs living plan

## Objective

Generate visual inventories and reviewed assembly instructions from versioned
CAD geometry and structured procedures, using open-source tools. First deliver
one useful small example as HTML and PDF, then process the enclosure's accepted
STEP/assembly exports when available.

## Current checkpoint — 2026-10-23 (Peter's manual review, front page, site viewer data, phase-1 scope)

Linux message `to-documentation/20261023T140613Z-…` (Peter reviewed the
supplement-03 manual: "looks pretty good" plus the items below) and the
phase-1 assignment `20261022T185753Z-…`. Order fixed by Linux: A, then B,
then C, then phase 1; a reply after each stage. Everything stays `draft`; no
assembly order is asserted anywhere.

- [x] A1 "counted" label clipped on every PDF card: the label now sits beside
  the box in a horizontal stack (never wrapped under it), the card's rows are
  spaced by the explicit gaps only (default paragraph/block spacing overflowed
  the fixed 84 mm and the clip cut the quantity row), and the text box grew to
  20 mm so six 7.5 pt lines fit (the tank card's two-line coincident note and
  the "14 bodies" card checked at 110 and 300 dpi). The HTML card keeps its
  label under the box (confirmed in the markup, no change).
- [x] A2 subassembly instance counts: every group page states the definition
  (from the exporter's `document`, else the id stem) and how many instances
  the project has ("CASTER ASSEMBLY (4 in this project)"), lists the shown and
  the other instance ids, adds a "for all N" column when the instances are
  identical in content (same part set and quantities, none flexible or
  position-overridden; otherwise "each instance" lists every instance's count
  and the page says why they differ); `manual.json` carries `definition`,
  `definition_basis`, `definition_document`, `instance_ids`, `instance_count`,
  `instances_identical`, `instance_detail`; a document/id-stem grouping
  disagreement is a finding on the status block; `check` compares the counts
  in HTML (`data-instance-count`) and PDF ("(N in this project)" tokens).
  Enclosure rebuilt from the existing renders: caster, panel and toggle-clamp
  definitions 4 instances each with totals, tank support frame 2, camera and
  free-standing frames 1 (flexible, overridden positions: no total needed).
- [x] B front page: the overview follows the status block on page 1
  (height-limited so it shares the page); page 2 draws the subassemblies
  apart. `render.json` `exploded_view` (`enabled` true/false/auto, `direction`,
  `spread` default 0.8, `fill`, `groups[].offset_mm` overrides; `explode.py`):
  every child assembly of the root with all its occurrences, and the parts
  directly under the root as `root-parts`, move as rigid bodies along the line
  from the root bounds centre to their own centre by `spread` times that
  distance (at least their own width along the line; a large concentric group
  stays as the reference, a small one lifts). Offsets recorded in the receipt
  with their source and in `hotspots/exploded.json`; `reuse.py` re-renders the
  view when they change. Callouts: one per subassembly definition (its page
  number) on the instance that shows best, at the centre of its largest
  occurrence box; the root parts as the next number; PDF badges placed in mm
  with a key whose page numbers come from Typst labels and are checked back
  against the heading pages; HTML callouts and key link to the sections.
  Fixture first (pins lift 30 mm, base drops 11 mm under its spread 1.0),
  then the enclosure (one 1600 px view with `--reuse`, no outlines over the
  600 000 budget like the overview).
- [x] C viewer data: `viewer.py` (bpy) writes `renders/viewer/assembled.glb`
  and `exploded.glb` (metres, +Y up, one mesh per part shared through nodes,
  node names = occurrence ids, one parent node per subassembly instance
  nested as in the scene, `root-parts`, one flat material; collapse
  decimation to a 200 000-triangle budget per file with small parts kept
  whole and normals split at 30°; `gltf.write_scene_glb`) and a receipt with
  per-part counts, hashes, the offsets and one anchor per instance in both
  states (bounds centre projected onto the nearest surface with its normal).
  `manual` copies the GLBs hash-checked and writes `viewer/hotspots.json` in
  the schema agreed with Linux; `manual.json` gains `exploded_view` and
  `viewer`; `check` verifies files, hashes, numbers and anchors. Linux
  generates the site pages from these; the page generator stays theirs.
- [x] Phase 1 contract: `build-scope.json` (schema 1; `phase`, `title`,
  `decided_by`, `review_state`, `deferred_occurrence_ids`, `conditional_groups`
  `{id, rule, decided}`, `backlight`, `deferred_design`, `note`; unknown fields
  refused; the recipe's own scene path accepted by file name) loaded with the
  manifests and hashed into every receipt. Every installed occurrence is in
  this build, conditional or deferred; cards print the this-build quantity as
  the large number with the CAD count and the conditional/deferred shares
  beside it, parts with nothing in the build move to a "Deferred (not in this
  build)" section; a one-page verification checklist lists every part with
  blank count/by/date/location/missing boxes; a step adding only deferred
  occurrences prints in a final "Deferred steps" chapter and is not
  accumulated by later steps, a step adding only conditional occurrences
  prints CONDITIONAL with its rule, a build step names its deferred
  additions; the status block states the phase, the counts, the note, the
  backlight sentence and the deferred design items. The scope is a
  non-render input: `reuse.py` re-renders a step whose additions or
  installed-before set changed, and the overview and steps when the
  instructions changed, while the thumbnails, groups, joints and exploded
  view are reused. `check` verifies the partition of the CAD counts, the
  checklist, the step chapters and the PDF tokens. Fixture: pin B deferred.
- [x] Step images ghost what is already installed (`step_context_alpha`,
  default 0.3: the flat context colour over transparency) because the first
  phase-1 render hid every addition behind the hung panels from step 13 on;
  joint close-ups keep their opaque faded context. A step with many part
  types shrinks its parts-needed pictures so the column stays on the page.
- [x] Phase 1 build: the Linux overlay of 2026-10-22 18:57 (`instructions.json`
  with 18 draft steps, `build-scope.json`) staged in the ignored enclosure copy
  and validated (110 of 155 installed occurrences in this build, 42
  conditional, 3 deferred; one part deferred entirely; one deferred step, two
  conditional). Rendered with `--reuse` on the front-page receipt: the overview
  (now the first step's camera) and the 18 step images, 67 views reused
  (308 s); the steps once more with the installed parts ghosted (289 s, 68
  reused). Compact PDF 59 pages, appendix 77 pages, 33 checks passed each,
  none failed. The reply carries a bounding-box reading of the draft order
  (the camera frame needs a side entry before the panels; the conditional tank
  support frames cannot go in after the panels, the camera frame and the top
  panel) for Peter to confirm at the bench.

## Previous checkpoint — 2026-10-22, second packet (supplementary items, stock record, joint close-ups)

Decisions from the Linux CAD agent (`to-documentation/20261022T161838Z-…`),
implemented against the three-part fixture first as asked; the enclosure build
is untouched until the Linux agent writes its CSV mapping and joint overlay.

- [x] `supplement.json` (schema_version integer 1): 23 explicit fields per row,
  quantities integer or null and never coerced to 0, `included_with` null or a
  discriminated object (`scene_part` id checked against the scene, `kit` free
  text), `intended_configuration_confirmed` an explicit boolean, one stock
  authority (`on_hand_each` with `counted_by`/`counted_date` required when it
  is a number; `on_order_each` separate), `item_kind` family/sku with family
  rows forbidden integer quantities, status rules (`covered` needs
  `included_with`; `specified` needs sku + supplier part number + verified),
  `attaches_to` validated against assembly/occurrence ids with `[]` allowed.
  Loaded with the other manifests, hashed into every receipt, summarised by
  `inspect`.
- [x] Inventory stock record: optional `on_hand_each`, `counted_by`,
  `counted_date`, `stock_location`, `intended_configuration_confirmed` per
  item with the same rules; the deprecated `counted` key is accepted only as
  null and `inventory-template` no longer writes it. The printed counted box
  is paper only; recorded stock prints as text on the card; the configuration
  flag prints beside the coincident finding and is never derived from it.
- [x] Printing: a separate "Supplementary items (not modelled in CAD)" section
  (scope `existing`), "Hardware to review at this joint (not an approved BOM)"
  under each subassembly whose id or descendants a row attaches to and under
  each joint close-up sharing the row's `joint_id`, never inside a parts table;
  `new_design` rows in the appendix only; the status block says supplementary
  quantities are never added to CAD quantities; the appendix prints every
  field of every row. `check` compares HTML, PDF and `manual.json` for the
  rows and the lists and confirms no row collides with a CAD part id.
- [x] `joint_views` in `render.json`: `joint_id`, `occurrence_ids`, optional
  `direction`, `context` (default deepest common ancestor), `context_style`
  faded/hidden, `id`; the view frames the union bounds of the listed
  occurrences at canonical poses with the rest of the context subdued; the
  receipt carries joint id, occurrence ids, context assembly and context
  occurrences; one page per joint, labelled an inspection view, not a step.
- [x] Fixture: three supplementary rows (a family with null quantities and a
  kit `included_with`, a specified SKU with integers, a counted stock record
  and a scene-part `included_with`, an unplaced new-design row), the
  `pin-pair` inspection view and a `pin_to_base` close-up; negative tests for
  a bare-string `included_with`, zero coercion, unknown ids, a family with an
  integer quantity, a count without `counted_by`, string booleans, status
  rules, duplicate ids, the schema version. 102 pure-Python tests, 2
  FreeCAD-gated.
- [x] Enclosure built with the Linux agent's overlay (17:03 UTC:
  `render.json` with the six groups and 16 `joint_views`, `inventory.json` with
  a stock record on all 37 parts, `supplement.json` with 20 family rows, 16
  existing / 4 new design): 16 joint close-ups rendered, 51 views reused
  from the 14:12 receipt in 838 s; compact PDF 36 pages, appendix 54 pages,
  23 checks passed each, none failed. Receipt checks scoped per stage so the
  new inventory and supplement did not force a CAD or full render re-run.
- [x] Second enclosure build with the Linux agent's adjusted overlay (17:37 UTC:
  seven joint views redirected along the review, `lines.max_triangles`
  600 000, one project note in `inventory.json`): 12 views rendered in two
  passes (12 found stale by `reuse.py`: changed joint specifications and
  outlines newly within budget; two views rendered again after the
  below-floor floor fix), the rest reused, 1354 s + 73 s; compact PDF
  36 pages, appendix 54 pages, 23 checks passed each, none
  failed; the project note prints on the status block. Frame groups with
  outlines at 600 000: camera frame 446 s, free-standing frame 233 s.
- [x] Third enclosure build (Linux overlay of 18:31 UTC: `clamp_mount_to_frame`
  with the list context `["FREE STANDING FRAME:1"]`): one view rendered in 64 s,
  66 reused; compact PDF 36 pages, appendix 54 pages, 23 checks passed each.
  All sixteen joint close-ups now show their attachment, fourteen with
  outlines; the enclosure's joint-view set is complete for this snapshot.
- [x] Renderer fixes found by this build: no shadow-catcher floor for a camera
  at or below the floor plane (a view from below saw only the catcher);
  joint `context` may be a list of assembly/occurrence ids not containing the
  subject (a joint between two groups can fade one frame); recorded joint
  directions compared with a tolerance.

## Previous checkpoint — 2026-10-22 (technician inventory, subassembly inspection views, unit regression)

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
- [x] Supplementary inventory contract answered by the Linux agent (16:18 UTC)
  and implemented in the second packet above; no further group instances
  beyond `:1` for now.
- [ ] Peter's review of the new inventory pages.

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

1. Build the enclosure with the Linux agent's `supplement.json` (20 family
   rows from its CSV mapping) and `joint_views` overlay (instances and
   directions per joint id) when they arrive; review the supplementary
   section and the per-joint close-ups; report. Nothing of either is invented
   here.
2. Review the picture-led inventory, subassembly pages and the supplementary
   section with Peter: card size, labels, inch equivalents, which long parts
   need the end view, which McMaster rows lack part numbers.
3. Ask the project team for a first reviewed sequence (one subassembly, e.g. the
   caster or panel assembly that already has an inspection view) and author
   `instructions.json` for it; add per-step view overrides, tools and
   checkpoints to the instruction model.
4. Evaluate Grease Pencil Line Art in background mode against Freestyle on the
   enclosure overview (32 min with Freestyle at 2.4 M triangles, 51 s without);
   full-assembly views stay without outlines under the 400 000-triangle budget
   until then. Not blocking.
5. Further group instances only when the project team names them (none beyond
   `:1` for now); a camera direction per group in `render.json` if the default
   direction hides something.
6. The static fallback for interactive extras in a MkDocs page.
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
  exploded, hidden or reordered, labelled as not a step. Joint close-ups frame
  named occurrences and subdue or hide the rest of their context; they too are
  inspection views, never steps. The Windows two-panel exporter fixture is no
  longer needed as a tracked inch example: the units fixture provides a real
  inch STEP without copying project data.
- Supplementary items are a separate manifest produced by the project's
  recipe, validated and printed here, never read from the project's sheets,
  never drawn, never added to CAD quantities; an unknown quantity stays null
  and prints as unknown. The one stock authority is `on_hand_each` with its
  attribution; the printed counted box is paper only. A family row cannot
  carry an integer quantity; a `specified` row needs a verified supplier part
  number. Rows with `scope: new_design` are appendix-only.
- Cycles with OpenImageDenoise is the reference look and the default engine
  (Peter's expectation; matches the joystick atlas). EEVEE Next is for previews
  and for the Guix Blender, which lacks the denoiser; receipts record both.
- Receipt checks are scoped to what a stage depends on: meshes.json is compared
  with the scene and asset hashes; `--reuse` and the manual stage compare
  render receipts with the scene, asset and instruction hashes (plus meshes,
  engine and quality for reuse). A changed inventory or supplement therefore
  never forces a CAD or render re-run (neither file changes a pixel); the
  manual re-reads both, and every receipt still records every input hash.
- A reused view is checked per view before it is copied (`reuse.py`): a joint
  close-up whose occurrences, context, context style or explicit direction
  changed, or any view drawn without outlines that the current line budget
  would now outline, is rendered again; a lower budget never discards an
  outlined image (the budget caps cost, it is not a look), so the 32-minute
  overview survives every rebuild. Other appearance changes need `--views`.
- Project prose stays in the project: `inventory.json` may carry `notes`
  (sentences printed verbatim on the status block, e.g. an intended build
  change), produced by the project recipe; nothing of the kind is authored in
  this repository.
- Track compact inputs; large generated outputs stay in `build/` or the evidence share.
- Native CAD acceptance, stock counts and the real assembly order remain the
  project team's; the fixtures prove tooling, not an enclosure procedure.

## Verification and handoff

Review packet of 2026-10-23, observed on the same host and tools (bpy 4.5.14
Cycles, Typst 0.15.0, Poppler 22.09): 124 pure-Python tests pass (2
FreeCAD-gated skipped in the base role). Stage A rebuilt both enclosure
manuals from the 18:38 receipt (compact 37 pages, appendix 54, 25 checks
passed each); the cards and a subassembly page inspected at 110 and 300 dpi.
Stages B and C: the fixture's exploded view (51 s) and viewer export
(two 34 kB GLBs), then one enclosure view with `--reuse` (52 s, 2 436 488
visible triangles, no outlines, 67 reused), viewer export in 4 s
(475 641 to 202 791 triangles, two 7.2 MB GLBs, 17 anchors); compact 39
pages, appendix 56, 28 checks passed each; the front pages inspected.
Phase 1: 19 views in 308 s then 18 ghosted steps in 289 s; compact 59
pages, appendix 77, 33 checks passed each; the status block, the deferred
parts section, the checklist page, three step pages and the contact sheets
of all 18 steps inspected by eye. Evidence runs
`evidence/2026-10-23-documentation-manual-fixes-01/`,
`…-front-page-and-viewer-01/`, `…-phase-1-01/`; replies in `to-linux/`
(14:48, 15:15 and the phase-1 reply); `status/documentation.json` refreshed
after each. Not run: the GLBs in a browser, a browser print test, a
technician review, any physical build. The working tree is Peter's 7e4cbef
plus these changes, uncommitted.

Third enclosure build, observed on 2026-10-22: overlay verified against its
SHA256SUMS; `reuse.py` re-rendered exactly the one view whose context changed
(63 s, 549 892 visible triangles with outlines), 66 views reused; compact PDF
36 pages and appendix 54 pages, 23 checks passed and 2 not applicable each;
the rebuilt view inspected at full size. Evidence
`evidence/2026-10-22-documentation-enclosure-supplement-03/`. The working tree
is Peter's 8172a92 plus these notes.

Enclosure build with the Linux overlay, observed on 2026-10-22 (same host and
tools): overlay files verified against their SHA256SUMS and staged beside the
accepted scene in the ignored copy; `inspect` 20 supplement rows, coincident
tank still a finding; 16 joint close-ups rendered in 838 s with 51 views reused
(18 to 118 s each; 6 of 16 with outlines, 10 over the 400 000-triangle budget:
frame contexts 472 340 and 546 280 triangles, root contexts 2 436 488); poses
restored and verified after every view; compact PDF 36 pages and appendix 54
pages, 23 checks passed and 2 not applicable each; the parts card grew to
84 mm (picture 34 mm, text 16 mm) so the stock record and configuration flag
fit above the quantity row. By eye: 5 close-ups show the attachment with
outlines, 4 are usable without, 7 do not show it (listed per view in the
reply with extents and causes). Fixture manuals rebuilt, all checks pass;
103 pure-Python tests. Evidence
`evidence/2026-10-22-documentation-enclosure-supplement-01/` (complete
compact package, appendix package without the identical images, 16 new
renders, contact sheets, receipts, logs).

Second packet, observed on 2026-10-22 (same host and tools): 102 pure-Python
tests pass (2 FreeCAD-gated skipped outside the CAD role; both pass in it).
Three-part fixture rebuilt end to end with Cycles and the denoiser: 10 views
in 255 s (the `pin-pair` inspection view 59 s, the `pin_to_base` close-up 57 s
at 1164 visible triangles with outlines, canonical poses restored and verified
after every view); compact PDF 9 pages and appendix PDF 10 pages, 25 checks
passed each (the new ones: HTML joint sections, HTML supplementary rows,
per-group and per-joint hardware lists, PDF joint headings, PDF supplementary
item ids present with new-design ids absent from the compact document,
supplementary rows separate from CAD parts). The two-bases and units manuals
were rebuilt from their existing renders with the new document code: all
checks pass. Pages inspected by eye: status block, parts cards with the paper
box, the supplementary table, the subassembly and joint pages with their
hardware lists, the appendix table of every field. Enclosure build untouched
(Linux's instruction). Evidence:
`evidence/2026-10-22-documentation-supplement-01/`; reply
`to-linux/20261022T164917Z-…`; `status/documentation.json` refreshed.

First packet, observed on 2026-10-22 (Debian 13 host, Guix 1.5.0, Pixi 0.63.2): Python 3.12.12,
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
