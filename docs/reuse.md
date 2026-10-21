# Existing tools to reuse

Source review performed 2026-10-21. These are extraction candidates, not dependencies already installed by this repository.

Peter identified three existing repositories to review before building
`mechanical-docs`. The recommendation is to extract reusable code gradually from
the mechanical atlas and PDF builder, consume the PCB tooling's published assets,
and retain project-specific content in its existing repositories. This is a
review and extraction plan; no tools were moved and no additional agent started.

## Sources inspected

Repository-relative paths below refer to sibling checkouts. Machine-specific locations are in the ignored local handoff:

| Repository | Inspected HEAD |
| --- | --- |
| mouse-joysticks-mech | 22aa7544fd1065927901ea3d3c6b253825883662 |
| mouse-joystick-pcb | 6927256cd283d8d9a2e73bcf9fd00cd74354e434 |
| camera-gpio-interface-pcb | 99817a813444e16289da89cfb0e8e5ad941790da |
| kicad-libs (shared implementation reached from the PCB Makefiles) | 36caa25d9838c47bb39abeacfde10adb56cf7645 |

The three requested repositories were clean before and after the review.
`mouse-joysticks-mech/atlas/build.py --check` returned 0 with `renders current`;
`atlas/bom.py --check` returned 0 with `every part node is covered`. These ran
read-only with Python/PyYAML in a temporary managed Guix shell, with bytecode
writing disabled. Pixi was not on this session's PATH and the repository's local
Pixi environment was absent, so it was not installed to perform these checks.
Existing brake-isolation and exploded-station PNGs were also inspected. Full
Blender renders, PDF generation and site builds were not rerun in this review.
These checks establish neither native CAD completeness nor assembly feasibility.

## Reuse candidates and boundaries

| Existing implementation | Recommended use |
| --- | --- |
| `mouse-joysticks-mech/atlas/build.py` | Extract registry resolution, render-job generation and input hashing. Keep the distinction between render-affecting fields and documentation-only fields. Parameterize roots/paths and validate outputs as well as inputs. |
| `mouse-joysticks-mech/atlas/render.py` | Extract Blender import, scene setup, material application, camera fitting, outlines, isolation, occluder ghosting, projected hotspots and GLB export. Keep exploded-layout placement as an illustration feature. |
| `mouse-joysticks-mech/atlas/overlay.py` | Extract clickable SVG callouts and legends, with configurable numbering/selection. Generalize the rules that currently suppress the mirrored station's duplicate labels. |
| `mouse-joysticks-mech/atlas/bom.py` and `components.yaml` | Reuse the registry/coverage design, vendor references and confirmation fields. Replace station-specific counting with explicit part/occurrence records and arbitrary nested subassemblies. Add duplicate-assignment checks and actual-stock fields. |
| `mouse-joysticks-mech/manual/build.py` and `manual/header.typ` | Extract the manifest-driven document assembly, image staging, link/heading rewriting, source appendix and Pandoc-to-Typst PDF workflow. This is already a substantial cross-repository publishing implementation. |
| `mouse-joysticks-mech/atlas/pages.py`, `atlas/site_pages.py`, `mkdocs.yml` | Reuse templates/patterns for component pages and the interactive viewer with a static/print fallback. The embedded rig prose, links, firmware mapping and board-specific pages remain project content. |
| PCB `docs/hooks/outward_links.py`, `mkdocs.yml`, `.github/workflows/pages.yml` | Reuse the site template and link-rewriting behavior; the hooks and Pages workflow are byte-identical between the two inspected PCB repositories. Preserve strict broken-link checking. Publishing remains an explicit action. |
| `kicad-libs/bin/orb-weaver-kicad-docs` | Keep as the KiCad adapter. It generates BOMs, schematic/layout documents, dimensioned drawings, assembled STEP/GLB, render manifests, blocks/subsystems and board views. Consume its outputs in mechanical-docs instead of moving the whole generator. |
| `kicad-libs/scripts/model_materials.py`, `blender_materials.py`, `board_view.py`, `png_rows.py` | Reuse existing PCB materials/export behavior through the adapter. Consider extracting generic PBR application, studio lighting, framing and overlay utilities after both consumers work. Keep KiCad model classification/palette ownership and PCB parsing in kicad-libs. |

The PCB exporter already records provenance and supplies GLB files that the rig
atlas copies through `atlas/boards.py`. That separation is a useful pattern for
Inventor/STEP inputs as well. The renderer should accept a common scene plus
explicit metadata, without requiring Inventor or KiCad at render time.

## Assumptions to remove before calling the code generic

- `atlas/render.py` and `atlas/bom.py` infer left/right stations from position,
  assume station/rig categories and use specific station axes for explosion.
  `overlay.py` suppresses left-side callouts in rig views. Replace these with
  arbitrary component groups, stable occurrence IDs and declared frames.
- Board placement in `render.py` guesses a scale factor from model size. Use
  explicit units. Do not carry that heuristic into a metre-scale enclosure.
- `manual/build.py` accepts a manifest, but still hard-codes the joystick
  repository in its introduction and site URL, and uses module-global staging
  paths and a fixed header location. Make project identity, staging and templates
  explicit inputs; preserve the existing image/link/source handling.
- `atlas/site_pages.py` contains project prose and fixed repository URLs. Extract
  page templates, not those particular pages as the general implementation.
- Render freshness currently compares input hashes and reports partial-render
  history. Extend this to verify requested output existence and per-view freshness
  before a manual release. The current registry check reports uncovered nodes,
  not all possible ambiguous/double mappings or physical stock discrepancies.
- Material and lighting conventions have already been shared between the atlas
  and kicad-libs. Avoid creating another independent copy; define ownership and
  adapters before migration, preserving provenance/attribution and source history.

## What still needs implementation for the enclosure

1. A STEP-to-render-mesh path with preserved units, occurrence identities,
   transforms, subassemblies and source hashes. The atlas starts with GLB today.
2. A reviewed assembly-step model: prerequisites, additions/moves/removals,
   cumulative state, temporary exploded positions, camera, insertion/rotation
   arrows, tools and checkpoints. Existing explosion factors are illustrations,
   not a validated assembly sequence or collision-free motion planner.
3. A pictorial inventory and step-page layout: thumbnails and quantities,
   distinction between required and counted stock, new/previous part styling,
   and consistent web/PDF output. The current BOM is primarily a table and the
   PDF builder compiles narrative documents; retain it while adding an image-led
   step template and a defined static fallback for interactive-only material.
4. Reconciliation with a complete accepted CAD/BOM snapshot and physical
   walkthrough. The enclosure's native/STEP body-count discrepancy remains open;
   existing joystick checks do not resolve it.

## Proposed migration order

1. Use the existing joystick atlas as a regression example. Extract one small
   renderer/configuration interface, keep project YAML/content and thin entry
   scripts in mouse-joysticks-mech, and reproduce representative views.
2. Add an enclosure subassembly as the second consumer. Require explicit units,
   nested repeated occurrences and stable identity so the abstraction is tested
   on different geometry. Demonstrate a visual BOM and three to five steps.
3. Extract the PDF builder and shared site templates around those two consumers.
   Reuse Pandoc/Typst and MkDocs before introducing another publishing stack.
4. Integrate PCB exports as assets; extract further shared utilities only when
   an actual overlap warrants it. Keep adapter-specific dependencies optional.

For that extraction, add focused regressions for source resolution/link rewriting,
duplicate or missing part mappings, transform/unit preservation, view restoration
after exploded rendering, and image/page output. Compare representative geometry,
camera framing and artifact manifests; rendered files can contain nondeterministic
metadata, so byte equality alone is not a meaningful image-quality check.

`mechanical-docs` is now the repository for this work. It should gain reusable
rendering/publishing code from these projects, while the first new feature remains
a small visual assembly manual. No repository migration or publication occurred
as part of this review.

## Extracted in the first implementation session (2026-10-21)

Adapted into `mechanical_docs/render.py` and `render_settings.py` from
`mouse-joysticks-mech` at `22aa7544` (`atlas/render.py`, `atlas/scene.yaml`):
the three-area-light studio scaled to the subject's bounding sphere, the look
palette and Principled BSDF mapping, the Freestyle subject/context line sets
with flat emissive context silhouettes, the projection-based camera fitting
loop, the `matrix_basis` restore after a displaced view, and projected
occurrence boxes for overlays. Deliberately not carried over: station roots
and left/right inference from position, board placement, the model-size scale
guess, explode chains along station axes, and the ghost ray casting (not
needed while previous parts are drawn as silhouettes; revisit for occluded
subjects). Every vector now comes from the scene manifest in declared units;
the renderer has no fixture-specific names.

Not reused yet: `manual/build.py` (the manifest-driven Markdown→Pandoc→Typst
narrative builder). The step pages needed an image-led layout, so `typst.py`
writes Typst directly from `manual.json`, following `manual/header.typ`'s
breakable-figure rule. The narrative builder is still the right starting point
for prose chapters and the sources appendix when a project needs them.
`atlas/overlay.py`'s clickable SVG became the overview callouts in `html.py`
(web-only, hidden in print). MkDocs site assembly was not started: the manual
is one static page; the atlas `mkdocs.yml` and PCB hooks remain the templates.

Attribution: the adapted code is by Peter Polidoro in `mouse-joysticks-mech`,
whose `LICENSE` covers the mechanical design files (CC-BY-SA-4.0) and does not
state a licence for the scripts. This repository has no licence file yet; the
choice for both is Peter's and was not made here.
