# mechanical-docs living plan

## Objective

Generate visual inventories and reviewed assembly instructions from versioned
CAD geometry and structured procedures, using open-source tools. First deliver
one useful small example as HTML and PDF, then process the enclosure's accepted
STEP/assembly exports when available.

## Current checkpoint — 2026-10-21 (first implementation session, Cycles follow-up)

- [x] Record scope, requirements, architecture and incoming-agent instructions.
- [x] Review reusable joystick atlas/PDF code and shared PCB tooling (docs/reuse.md).
- [x] Define the draft-1 input contract; implement exactly its milestone subset with
  explicit rejection of everything else (`mechanical_docs/manifest.py`, 59 pytest
  tests across manifest, transforms, procedure, GLB, geometry, settings, document).
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
- [ ] Coordinate the production export contract with the CAD/Windows agent
  (request posted; Linux sent Windows a matching request on 2026-10-21T18:31Z).
- [ ] Validate an accepted enclosure subassembly; retain the joystick example as a
  second consumer/regression for the extracted rendering behaviour.
- [ ] MkDocs site assembly and the narrative Pandoc/Typst builder for prose chapters.
- [ ] Close-up views, moves/removals, tools and checkpoints in the instruction model.

## Next implementation sequence

1. Read the Windows reply to the exporter field request; adapt `scene.json`
   production fields (identity, Vault ids, BOM classification) without guessing.
2. Load a small real subassembly from per-part STEP once exported; expect
   contract changes (configurations, phantom assemblies, purchased kits).
3. Add close-ups (per-step view override), a camera per subassembly, and the
   static fallback for interactive extras in a MkDocs page.
4. Reproduce one or two joystick atlas views through the generic renderer as a
   regression; decide where shared materials live (kicad-libs overlap).
5. Review printed pages with a technician; add the physical-validation record
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
- Cycles with OpenImageDenoise is the reference look and the default engine
  (Peter's expectation; matches the joystick atlas). EEVEE Next is for previews
  and for the Guix Blender, which lacks the denoiser; receipts record both.
- Track compact inputs; large generated outputs stay in `build/` or the evidence share.
- Native CAD acceptance, stock counts and the real assembly order remain the
  project team's; the fixtures prove tooling, not an enclosure procedure.

## Verification and handoff

Observed on 2026-10-21 (Debian 13 host, Guix 1.5.0, Pixi 0.63.2): Python 3.12.12,
PyYAML 6.0.3, pytest 9.0.2 (59 passed), FreeCAD 1.1.3, Blender 4.5.10 from Guix
(no denoiser) and bpy 4.5.14 from PyPI (OpenImageDenoise), Typst 0.15.0, Poppler
22.09, ImageMagick 6.9.13. Cycles, 64 adaptive samples, 1600 px: three-part
fixture 8 views in 132 s (steps about 11 s, overview with floor 54 s), 6-page
PDF, 16 checks passed; two-bases fixture 10 views in 150 s, 8-page PDF, 16 checks
passed. EEVEE on the Guix Blender renders the same views in under a second each.
Cycles and EEVEE images were compared by eye (contact shadows and shading differ;
layout, outlines and arrows identical); PDF pages and a headless-Chromium
screenshot of the HTML were inspected; greyscale copies remain legible.
Not run: a real browser print test, any production geometry, any physical build.
Inside a Guix shell Pixi needs `CONDA_OVERRIDE_GLIBC` set to the host glibc. Evidence and the mailbox reply are
under the shared coordination area named in the ignored local handoff. No
commits, pushes or publication were made.
