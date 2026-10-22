# mechanical-docs living plan

## Objective

Generate visual inventories and reviewed assembly instructions from versioned
CAD geometry and structured procedures, using open-source tools. First deliver
one useful small example as HTML and PDF, then process the enclosure's accepted
STEP/assembly exports when available.

## Current checkpoint — 2026-10-21 (first implementation session, Cycles follow-up, first production snapshot)

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
- [ ] Coordinate the production export contract with the CAD/Windows agent:
  the two open questions (per-asset units: yes; flexible instances: one group
  definition with per-instance placements) answered via the mailbox; a
  refresh-stable occurrence key remains the one unmet request.
- [ ] Author and review a real assembly sequence for a small enclosure subassembly
  with the project team (not this tool's call); until then production output is
  inventory-only.
- [ ] Retain the joystick example as a second consumer/regression for the
  extracted rendering behaviour.
- [ ] MkDocs site assembly and the narrative Pandoc/Typst builder for prose chapters.
- [ ] Close-up views, moves/removals, tools and checkpoints in the instruction model.

## Next implementation sequence

1. Review the enclosure inventory output with Peter: part labels, thumbnails of
   large framing versus small hardware, which McMaster rows lack part numbers,
   and whether purchased kits need a separate inventory classification.
2. Ask the project team for a first reviewed sequence (one subassembly, e.g. a
   caster assembly or panel assembly) and author `instructions.json` for it;
   add per-step close-ups, tools and checkpoints to the instruction model.
3. Evaluate Grease Pencil Line Art in background mode against Freestyle on the
   enclosure overview (32 min with Freestyle at 2.4 M triangles, 51 s without);
   step views of a full assembly are not affordable with Freestyle.
4. Decide with Peter whether the Windows two-panel exporter fixture (one 25 kB
   Inventor inch STEP, two occurrences, +Y up) becomes a tracked example; it
   would give the regression suite a real inch import, which FreeCAD cannot write.
5. Add close-ups (per-step view override), a camera per subassembly, and the
   static fallback for interactive extras in a MkDocs page.
6. Reproduce one or two joystick atlas views through the generic renderer as a
   regression; decide where shared materials live (kicad-libs overlap).
7. Review printed pages with a technician; add the physical-validation record
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
- The enclosure snapshot is not an accepted BOM or geometry baseline (Linux CAD
  agent's call); the inventory document says so on its first page. The local copy
  lives under ignored `build/enclosure-snapshot-991056/`, not in Git.
- Cycles with OpenImageDenoise is the reference look and the default engine
  (Peter's expectation; matches the joystick atlas). EEVEE Next is for previews
  and for the Guix Blender, which lacks the denoiser; receipts record both.
- Track compact inputs; large generated outputs stay in `build/` or the evidence share.
- Native CAD acceptance, stock counts and the real assembly order remain the
  project team's; the fixtures prove tooling, not an enclosure procedure.

## Verification and handoff

Observed on 2026-10-21 (Debian 13 host, Guix 1.5.0, Pixi 0.63.2): Python 3.12.12,
PyYAML 6.0.3, pytest 9.0.2 (76 passed), FreeCAD 1.1.3, Blender 4.5.10 from Guix
(no denoiser) and bpy 4.5.14 from PyPI (OpenImageDenoise), Typst 0.15.0, Poppler
22.09, ImageMagick 6.9.13. Cycles, 64 adaptive samples, 1600 px: three-part
fixture 8 views in 132 s (steps about 11 s, overview with floor 54 s), 6-page
PDF, 16 checks passed; two-bases fixture 10 views in 150 s, 8-page PDF, 16 checks
passed; both rebuilt after the production changes. EEVEE on the Guix Blender
renders the same views in under a second each. Enclosure snapshot (pilot-02,
37 parts, 155 occurrences): CAD 2 min 22 s, 37/37 parts pass with 9 recorded
warnings; 38 Cycles views in 39 min (thumbnails 9.5 to 23 s, overview 32 min
with Freestyle, 51 s without); 12-page inventory PDF; 14 checks passed, 2 not
applicable without steps. Images and PDF pages were inspected by eye (coarsened
hardware thumbnails still read correctly at 600 px).
Not run: a real browser print test, any physical build, Grease Pencil Line Art.
Inside a Guix shell Pixi needs `CONDA_OVERRIDE_GLIBC` set to the host glibc. Evidence and the mailbox reply are
under the shared coordination area named in the ignored local handoff. No
commits, pushes or publication were made.
