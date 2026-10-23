# mechanical-docs

Open-source tools for generating visual documentation from mechanical CAD models
and structured project information. The first use case is a visual parts inventory
and LEGO-style assembly manual, with matching web and printable PDF versions.
Future uses include maintenance, replacement, disassembly and inspection guides.

**Status: inventory-only manuals from the first production snapshot; technician-facing
layout, subassembly inspection views, a supplementary-items manifest and joint
close-ups (2026-10-22).** A validated draft-1 manifest loader (scene,
inventory with an optional stock record, instructions, and `supplement.json`
for items not modelled in CAD), a FreeCAD STEP-to-mesh stage, a Blender render
stage (Cycles with OpenImageDenoise through the `bpy` wheel, EEVEE on the Guix
Blender), and a document stage that writes one `manual.json` and generates
HTML and a Typst PDF from it, with an output checker. Three synthetic fixtures
build end to end, and the enclosure snapshot (37 parts, 155 occurrences)
builds as a draft parts inventory with six subassembly inspection views. No
assembly sequence has been authored or reviewed for production geometry, and
nothing is physically validated.

## Start here

An incoming agent should read [AGENTS.md](AGENTS.md), then:

1. [Next-agent handoff](docs/next-agent.md): what exists, what to do next.
2. [Requirements](docs/requirements.md): what technicians should receive.
3. [Architecture](docs/architecture.md) and the [draft input contract](docs/input-contract.md),
   including the implemented subset and the fields requested from the CAD exporter.
4. [Existing tools to reuse](docs/reuse.md): what was extracted from the joystick atlas and what was not.
5. [Environment](docs/environment.md), the [living plan](.agents/PLANS.md) and the fixtures:
   [three-part](examples/three-part-fixture/README.md), [two-bases](examples/two-bases-fixture/README.md),
   [units](examples/units-fixture/README.md) (a real inch STEP, a centimetre STEP, an inch Y-up scene).

## Pipeline

```text
inspect (Python)  ->  cad_mesh.py (FreeCADCmd)  ->  render.py (Blender)  ->  [viewer.py (bpy)]  ->  manual (Python + Typst)  ->  check
validated manifests   GLB per part + meshes.json    PNGs + render-receipt.json   viewer GLBs + anchors   manual.json, index.html, PDF, viewer/   agreement, links, rasters
```

```sh
tools/build-fixture.sh --renderer pixi                   # all stages, Cycles via the bpy wheel -> build/three-part-fixture/
tools/build-fixture.sh examples/two-bases-fixture --renderer pixi
tools/build-fixture.sh examples/units-fixture --renderer pixi --appendix   # inch/cm/mm assets; prints the technical appendix too
tools/build-fixture.sh                                   # Guix Blender: EEVEE (that package has no denoiser)
tools/build-fixture.sh . --preview                       # small fast images
guix shell --pure -m manifest.scm -- python3 -B -m pytest -q tests                                   # pure-Python suite
guix shell --pure -m manifest.scm -m .guix/manifest-cad.scm -- python3 -B -m pytest -q tests/test_cad_stage.py   # FreeCAD unit checks
```

The Pixi route needs `pixi install -e render` once (and, inside a Guix shell,
`CONDA_OVERRIDE_GLIBC` set to the host glibc); see [docs/environment.md](docs/environment.md).

Or stage by stage, each in its Guix role (see [docs/environment.md](docs/environment.md)):

```sh
python3 -m mechanical_docs inventory-template PROJECT      # draft inventory.json from a scene (required = installed occurrences)
python3 -m mechanical_docs inspect examples/three-part-fixture --json build/inspect.json
FreeCADCmd mechanical_docs/cad_mesh.py --pass examples/three-part-fixture build/meshes [--max-triangles 50000]
pixi run -e render render examples/three-part-fixture build/meshes/meshes.json build/renders [--preview] [--engine BLENDER_EEVEE_NEXT] [--no-lines] [--groups pin-pair] [--reuse build/renders-old]
blender -b --python mechanical_docs/render.py -- examples/three-part-fixture build/meshes/meshes.json build/renders --engine BLENDER_EEVEE_NEXT
.pixi/envs/render/bin/python mechanical_docs/viewer.py examples/three-part-fixture build/meshes/meshes.json build/renders [--budget 200000]   # optional: viewer GLBs beside the renders
python3 -m mechanical_docs manual examples/three-part-fixture --renders build/renders --out build/manual --meshes build/meshes/meshes.json [--appendix]
python3 -m mechanical_docs check build/manual
```

`--groups` (or `inspection_groups` in `render.json`) renders named subassemblies
alone as inspection views; `joint_views` in `render.json` renders per-joint
close-ups (the listed occurrences framed, the rest of their context faded or
hidden); `exploded_view` in `render.json` (on by default when the root has two
or more groups) draws the subassemblies apart for the front page, every child
assembly of the root and the parts directly under it moved as a rigid body by
a recorded offset (radial default, or the project's `offset_mm`); `viewer.py`
then exports `viewer/assembled.glb` and `viewer/exploded.glb` with the same
offsets plus anchors for a web model viewer; `--reuse` copies views from an earlier complete receipt made from
the same scene, assets, instructions, meshes and engine (inventory and
supplement changes never invalidate it), so changing a few thumbnails does not
mean rendering the whole assembly again (each copied view is marked
`reused_from` in the receipt). `--appendix` prints the technical appendix;
without it the printed document stays compact and the full identities live in
`manual.json` and `build-receipt.json`. Two occurrences of one part at the
same pose are kept and counted but reported as a finding on the status block
and the part's card (a CAD ambiguity to review before the count becomes
stock). A project's optional `supplement.json` lists hardware that is not
modelled in CAD: validated, printed in its own section and under the joints
it attaches to, never added to CAD quantities, unknown quantities left
unknown (see the contract). An optional `build-scope.json` scopes one build
phase: deferred occurrences and undecided (conditional) groups, printed as
this-build, conditional and deferred quantities on the cards, a one-page
verification checklist, deferred and conditional step chapters and the phase
note on the status block; CAD counts never change.

Every stage writes a receipt with input hashes and tool versions and refuses
inputs whose hashes do not match the receipt it consumes, for the inputs that
stage depends on (meshes depend on the scene and assets; images on those plus
the instructions; the manual re-reads the inventory and supplement itself, so
a recorded count or a new supplement row needs a new manual, not a render). `build/` is ignored
by Git; representative outputs go to the shared evidence area.

A project without `instructions.json` still builds: the output is the parts
inventory and the overview, and both documents say that no assembly sequence
has been authored. That is how a CAD snapshot is processed before anyone has
reviewed an order. The loader also accepts the production fields the Windows
exporter writes (per-asset inch/mm/cm units, a declared +Y-up basis, Vault
provenance, BOM structure, flexible-instance flags); see the contract.

## What the manual contains

A status block with the review state; the finished assembly (web callouts to
the parts) and the subassemblies drawn apart with numbered callouts that are
the subassembly page numbers (links on the web, a key with page references in
the PDF); picture-led parts cards (badge, a large
picture, or a wide picture plus an end view for long profiles and panels, a
short label, the overall size with inch equivalents for inch parts, the CAD
quantity labelled as a CAD instance count rather than a purchase quantity, the
recorded stock when the inventory carries one, and a paper box for a new
count); a separate table of supplementary items not modelled in CAD (family
or SKU, status, required and on-hand quantities with unknown left unknown,
what they are included with, the configuration flag), never summed with the
CAD counts; one page per subassembly inspection view (the group's parts at
their CAD positions with a parts list, explicitly not an assembly step; the
heading names the subassembly definition and how many instances of it the
project has, the shown instance and the others, and the parts list adds a
"for all N" column when the instances are identical in content) and
per joint close-up, each listing the supplementary rows attached to it as
"hardware to review at this joint (not an approved BOM)"; the finished
assembly with web-only clickable callouts; one page per step (parts needed
with quantities, the step image with the previous parts subdued and the new
part highlighted, an approach arrow and a result image when the step has a
hint); a compact build record; `viewer/hotspots.json` with the two GLBs when
the viewer export ran (data for a site generator, not pages); and, with `--appendix`, a technical appendix
with full part ids, Vault ids, occurrence lists, every hash, every supplement
row with every field and the new-design rows. The checker compares HTML, PDF
and `manual.json` for the same inventory, CAD quantities, subassembly and
joint sections with their instance counts, exploded-view callouts and the
key's page numbers, supplementary rows and hardware lists, step order, and
the viewer files against their receipt.

## Ownership

- This repository: reusable scene preparation, rendering, visual procedures,
  inventory presentation and publishing tools; small synthetic regression fixtures.
- Project repositories: their CAD assets, identifiers, inventory, procedures,
  camera choices, looks and validation records.
- `vault-cad-tools`: Autodesk-specific acquisition/export/publication.
- `kicad-libs`: KiCad-specific extraction and PCB documentation.

Generated production meshes, renders, PDFs and sites belong in ignored build
directories or explicitly published releases. Commits, pushes and publication
are Peter's. No licence has been chosen for this repository yet.
