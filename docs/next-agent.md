# Incoming documentation agent

The first slice exists and runs. Read AGENTS.md, README.md, docs/input-contract.md
(implemented subset, stage outputs, exporter field request), docs/environment.md
(roles, FreeCAD and Blender quirks) and .agents/PLANS.md. Use
.agents/handoff.local.md for the mailbox and evidence paths; the tracked
documentation stays usable without them.

## What exists

- `mechanical_docs/`: `manifest.py` (validation), `transforms.py`, `procedure.py`,
  `gltf.py`, `geometry.py`, `receipts.py`, `render_settings.py`, `cad_mesh.py`
  (FreeCADCmd), `render.py` (Blender), `document.py` + `html.py` + `typst.py`,
  `checks.py`, `cli.py`. `tests/` has 59 pytest tests that need only the base role.
- `examples/three-part-fixture/` and `examples/two-bases-fixture/`, both building
  with `tools/build-fixture.sh` into `build/<fixture>/`.
- Receipts at every stage; later stages refuse stale or failed inputs.

## Before changing the renderer or contract

Run both fixtures and the tests first; they are the regression baseline. Keep the
rule that `approach` offsets are hints, that canonical poses are restored and
verified after each view, and that asset units and scene units convert separately.
If a production field is needed, add it to docs/input-contract.md and the
validator together, and tell the Windows agent through the mailbox.

## Suggested next work

1. Act on the Windows reply about exporter fields; load the first real
   per-part STEP + manifest export as a third example, outside Git if large.
2. Per-step view overrides and close-ups; a `tools` and `checkpoints` list per
   step rendered in both outputs; moves/removals as declared operations.
3. A MkDocs wrapper page with the static fallback, reusing the atlas and PCB
   site templates, so the manual can sit beside project prose.
4. Reproduce a joystick atlas view through `render.py` from a GLB-backed part
   list, to keep the extracted behaviour honest against its origin.
5. Optional: Pixi `render` environment with the `bpy` wheel for denoised Cycles.

## What remains with the CAD/project agents

Accepted Inventor/Vault versions, export completeness (503 native surface bodies
versus 479 reimported solids is still open), per-part/configuration mapping,
production placements, stock counts, a technician-reviewed order and a physical
walkthrough. Nothing rendered here says anything about the enclosure.

## Finish a session

Update .agents/PLANS.md, write evidence under a fresh UTC-dated directory on the
share, post a timestamped reply in the mailbox and refresh
`status/documentation.json`. Leave commits and publication to Peter.
