# mechanical-docs

Open-source tools for generating visual documentation from mechanical CAD models
and structured project information. The first use case is a visual parts inventory
and LEGO-style assembly manual, with matching web and printable PDF versions.
Future uses include maintenance, replacement, disassembly and inspection guides.

**Status: first working slice on synthetic fixtures (2026-10-21).** A validated
draft-1 manifest loader, a FreeCAD STEP-to-mesh stage, a Blender render stage
(Cycles with OpenImageDenoise through the `bpy` wheel, EEVEE on the Guix Blender),
and a document stage that writes one `manual.json` and generates HTML and a Typst
PDF from it, with an output checker. Two synthetic fixtures build end to end.
No production CAD has been processed, and no procedure is physically validated.

## Start here

An incoming agent should read [AGENTS.md](AGENTS.md), then:

1. [Next-agent handoff](docs/next-agent.md): what exists, what to do next.
2. [Requirements](docs/requirements.md): what technicians should receive.
3. [Architecture](docs/architecture.md) and the [draft input contract](docs/input-contract.md),
   including the implemented subset and the fields requested from the CAD exporter.
4. [Existing tools to reuse](docs/reuse.md): what was extracted from the joystick atlas and what was not.
5. [Environment](docs/environment.md), the [living plan](.agents/PLANS.md) and the fixtures:
   [three-part](examples/three-part-fixture/README.md), [two-bases](examples/two-bases-fixture/README.md).

## Pipeline

```text
inspect (Python)  ->  cad_mesh.py (FreeCADCmd)  ->  render.py (Blender)  ->  manual (Python + Typst)  ->  check
validated manifests   GLB per part + meshes.json    PNGs + render-receipt.json   manual.json, index.html, PDF   agreement, links, rasters
```

```sh
tools/build-fixture.sh --renderer pixi                   # all stages, Cycles via the bpy wheel -> build/three-part-fixture/
tools/build-fixture.sh examples/two-bases-fixture --renderer pixi
tools/build-fixture.sh                                   # Guix Blender: EEVEE (that package has no denoiser)
tools/build-fixture.sh . --preview                       # small fast images
guix shell --pure -m manifest.scm -- python3 -B -m pytest -q tests
```

The Pixi route needs `pixi install -e render` once (and, inside a Guix shell,
`CONDA_OVERRIDE_GLIBC` set to the host glibc); see [docs/environment.md](docs/environment.md).

Or stage by stage, each in its Guix role (see [docs/environment.md](docs/environment.md)):

```sh
python3 -m mechanical_docs inspect examples/three-part-fixture --json build/inspect.json
FreeCADCmd mechanical_docs/cad_mesh.py --pass examples/three-part-fixture build/meshes
pixi run -e render render examples/three-part-fixture build/meshes/meshes.json build/renders [--preview] [--engine BLENDER_EEVEE_NEXT]
blender -b --python mechanical_docs/render.py -- examples/three-part-fixture build/meshes/meshes.json build/renders --engine BLENDER_EEVEE_NEXT
python3 -m mechanical_docs manual examples/three-part-fixture --renders build/renders --out build/manual --meshes build/meshes/meshes.json
python3 -m mechanical_docs check build/manual
```

Every stage writes a receipt with input hashes and tool versions and refuses
inputs whose hashes do not match the receipt it consumes. `build/` is ignored
by Git; representative outputs go to the shared evidence area.

## What the manual contains

A status block with the review state, a parts table (thumbnail, label, name,
identifying dimensions, required quantity, a box for the quantity found), the
finished assembly with web-only clickable callouts, one page per step (parts
needed with quantities, the step image with the previous parts subdued and the
new part highlighted, an approach arrow and a result image when the step has a
hint), and a build record with hashes and versions. The checker compares HTML,
PDF and `manual.json` for the same inventory, quantities and step order.

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
