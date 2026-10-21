# mechanical-docs

Open-source tools for generating visual documentation from mechanical CAD models
and structured project information. The first use case is a visual parts inventory
and LEGO-style assembly manual, with matching web and printable PDF versions.
Future uses include maintenance, replacement, disassembly and inspection guides.

**Status: development handoff and sample inputs.** There is no general importer,
renderer, instruction validator, website builder or PDF command here yet. A small
synthetic STEP fixture is included so development can proceed before production
assembly exports are ready.

## Start here

An incoming agent should read [AGENTS.md](AGENTS.md), then:

1. [Next-agent handoff](docs/next-agent.md): the first implementation task and
   what counts as a useful result.
2. [Requirements](docs/requirements.md): what technicians should receive.
3. [Architecture](docs/architecture.md) and [draft input contract](docs/input-contract.md).
4. [Existing tools to reuse](docs/reuse.md): inspected source files and caveats.
5. [Living plan](.agents/PLANS.md) and [synthetic fixture](examples/three-part-fixture/README.md).

## First milestone

Process the included STEP parts and occurrence manifest into a visual inventory
and three illustrated assembly steps. Render with Blender, build a local HTML
manual and a PDF from the same instruction data, and record source hashes and
tool versions. Reuse the existing joystick atlas and publishing tools where
practical. Keep real assembly order explicitly reviewed by people.

The fixture has two distinct part assets and three installed occurrences, including
two copies of one pin under a transformed parent assembly. This exercises quantities,
identity and parent-relative transforms without depending on Vault or Inventor.

## Development environment

The base Guix manifest provides Python, PyYAML and Git:

```sh
guix shell --pure -m manifest.scm
```

An optional CAD role can regenerate and geometrically check the example:

```sh
guix shell --pure -m .guix/manifest-cad.scm -- FreeCADCmd examples/three-part-fixture/generate_fixture.py
```

That command rewrites the example's derived STEP files, scene manifest and geometry
receipt. Hand-authored instructions and inventory are separate. STEP metadata can
change file hashes on regeneration; the receipt must describe the actual files.

Rendering/publishing environments are the next agent's work. The joystick source
already supplies a locked Pixi setup with Blender's `bpy` wheel, MkDocs,
Pandoc and Typst; adapt and lock it when adding real tasks. Do not assume those
tools are installed by this repository's base manifest. No Pixi configuration or
lock is claimed here yet. See [environment guidance](docs/environment.md).

## Ownership

- This repository: reusable scene preparation, rendering, visual procedures,
  inventory presentation and publishing tools; small synthetic regression fixtures.
- Project repositories: their CAD assets, identifiers, inventory, procedures,
  camera choices and validation records.
- `vault-cad-tools`: Autodesk-specific acquisition/export/publication.
- `kicad-libs`: KiCad-specific extraction and PCB documentation.

Generated production meshes, renders, PDFs and sites belong in ignored build
directories or explicitly published releases. Keep the accepted CAD and compact
instruction sources versioned; do not save a complete duplicate CAD assembly for
every instruction step. This scaffold creates no publication workflow.
