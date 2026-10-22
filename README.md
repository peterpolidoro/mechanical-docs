# mechanical-docs

Open-source tools for generating visual documentation from mechanical CAD models
and structured project information. The first use case is a visual parts inventory
and LEGO-style assembly manual, with matching web and printable PDF versions.
Future uses include maintenance, replacement, disassembly and inspection guides.

**Status: inventory-only manuals from the first production snapshot; technician-facing
layout and subassembly inspection views (2026-10-22).** A validated draft-1 manifest
loader, a FreeCAD STEP-to-mesh stage, a Blender render stage (Cycles with
OpenImageDenoise through the `bpy` wheel, EEVEE on the Guix Blender), and a
document stage that writes one `manual.json` and generates HTML and a Typst PDF
from it, with an output checker. Three synthetic fixtures build end to end, and
the enclosure snapshot (37 parts, 155 occurrences) builds as a draft parts
inventory with subassembly inspection views. No assembly sequence has been
authored or reviewed for production geometry, and nothing is physically validated.

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
inspect (Python)  ->  cad_mesh.py (FreeCADCmd)  ->  render.py (Blender)  ->  manual (Python + Typst)  ->  check
validated manifests   GLB per part + meshes.json    PNGs + render-receipt.json   manual.json, index.html, PDF   agreement, links, rasters
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
python3 -m mechanical_docs manual examples/three-part-fixture --renders build/renders --out build/manual --meshes build/meshes/meshes.json [--appendix]
python3 -m mechanical_docs check build/manual
```

`--groups` (or `inspection_groups` in `render.json`) renders named subassemblies
alone as inspection views; `--reuse` copies views from an earlier complete
receipt made from the same inputs, meshes and engine, so changing a few
thumbnails does not mean rendering the whole assembly again (each copied view
is marked `reused_from` in the receipt). `--appendix` prints the technical
appendix; without it the printed document stays compact and the full
identities live in `manual.json` and `build-receipt.json`. Two occurrences of
one part at the same pose are kept and counted but reported as a finding on
the status block and the part's card (a CAD ambiguity to review before the
count becomes stock).

Every stage writes a receipt with input hashes and tool versions and refuses
inputs whose hashes do not match the receipt it consumes. `build/` is ignored
by Git; representative outputs go to the shared evidence area.

A project without `instructions.json` still builds: the output is the parts
inventory and the overview, and both documents say that no assembly sequence
has been authored. That is how a CAD snapshot is processed before anyone has
reviewed an order. The loader also accepts the production fields the Windows
exporter writes (per-asset inch/mm/cm units, a declared +Y-up basis, Vault
provenance, BOM structure, flexible-instance flags); see the contract.

## What the manual contains

A status block with the review state; picture-led parts cards (badge, a large
picture, or a wide picture plus an end view for long profiles and panels, a
short label, the overall size with inch equivalents for inch parts, the CAD
quantity labelled as a CAD instance count rather than a purchase quantity, and
a blank box for the counted quantity); one page per subassembly inspection
view (the group's parts at their CAD positions with a parts list, explicitly
not an assembly step); the finished assembly with web-only clickable
callouts; one page per step (parts needed with quantities, the step image with
the previous parts subdued and the new part highlighted, an approach arrow and
a result image when the step has a hint); a compact build record; and, with
`--appendix`, a technical appendix with full part ids, Vault ids, occurrence
lists and every hash. The checker compares HTML, PDF and `manual.json` for the
same inventory, CAD quantities, subassembly sections and step order.

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
