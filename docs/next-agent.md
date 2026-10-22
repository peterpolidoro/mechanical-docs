# Incoming documentation agent

The first slice exists, runs on both synthetic fixtures and on the first
production snapshot (inventory-only). Read AGENTS.md, README.md,
docs/input-contract.md (implemented subset, production fields, stage outputs,
exporter field request), docs/environment.md (roles, FreeCAD and Blender quirks,
render cost and budgets) and .agents/PLANS.md. Use .agents/handoff.local.md for
the mailbox and evidence paths; the tracked documentation stays usable without
them.

## What exists

- `mechanical_docs/`: `manifest.py` (validation, production fields, +Y-up basis),
  `names.py` (slugs for free-form ids), `stepinfo.py` (declared STEP unit),
  `transforms.py`, `procedure.py`, `gltf.py`, `geometry.py`, `receipts.py`,
  `render_settings.py`, `cad_mesh.py` (FreeCADCmd, triangle budget), `render.py`
  (Blender, Cycles default, line budget), `document.py` + `html.py` + `typst.py`,
  `checks.py`, `cli.py` (`inspect`, `inventory-template`, `manual`, `check`).
  `tests/` has 76 pytest tests that need only the base role.
- `examples/three-part-fixture/` and `examples/two-bases-fixture/`, both building
  with `tools/build-fixture.sh` into `build/<fixture>/`.
- The enclosure snapshot (Windows per-part export, 37 parts, 155 occurrences)
  builds as an inventory-only manual from an ignored copy under
  `build/enclosure-snapshot-991056/project/`; the evidence runs on the share hold
  its outputs. It is not an accepted BOM and has no assembly sequence.
- Receipts at every stage; later stages refuse stale, partial or failed inputs.

## Before changing the renderer or contract

Run both fixtures and the tests first; they are the regression baseline. Keep the
rule that `approach` offsets are hints, that canonical poses are restored and
verified after each view, that asset units and scene units convert separately,
and that FreeCAD geometry is millimetres whatever the STEP declares (the declared
unit is provenance, compared with the manifest, never applied to coordinates).
If a production field is needed, add it to docs/input-contract.md and the
validator together, and tell the Windows agent through the mailbox.

## Suggested next work

1. Review the enclosure inventory output with Peter (labels, long Vault ids,
   thumbnails of long framing versus small hardware, missing McMaster part numbers).
2. A reviewed sequence for one small subassembly from the project team; then
   per-step view overrides and close-ups, `tools` and `checkpoints` per step,
   moves/removals as declared operations.
3. Line art on production scenes: Freestyle is the cost driver (see
   docs/environment.md). Evaluate Grease Pencil Line Art in background mode as a
   replacement before raising the budgets.
4. A tracked example in the production format with a real inch STEP, if Peter
   agrees to track the Windows two-panel exporter fixture (two occurrences, one
   25 kB Inventor STEP in inches, +Y up) from the pilot-02 evidence run; FreeCAD
   here cannot write inch STEP files, so the fixtures cannot generate one.
5. A MkDocs wrapper page with the static fallback, reusing the atlas and PCB
   site templates; a joystick atlas view through `render.py` as a regression.

## What remains with the CAD/project agents

Accepted Inventor/Vault versions, export completeness, production placements,
stock counts, a technician-reviewed order and a physical walkthrough. A
refresh-stable occurrence key is the one unmet exporter request. Nothing
rendered here says the enclosure is complete or buildable.

## Finish a session

Update .agents/PLANS.md, write evidence under a fresh UTC-dated directory on the
share, post a timestamped reply in the mailbox and refresh
`status/documentation.json`. Leave commits and publication to Peter.
