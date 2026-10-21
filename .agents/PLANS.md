# mechanical-docs living plan

## Objective

Generate visual inventories and reviewed assembly instructions from versioned
CAD geometry and structured procedures, using open-source tools. First deliver
one useful small example as HTML and PDF, then process the enclosure's accepted
STEP/assembly exports when available.

## Current checkpoint — 2026-10-21

- [x] Record scope, requirements, architecture and incoming-agent instructions.
- [x] Review reusable joystick atlas/PDF code and shared PCB tooling; record
  source commits, assumptions and extraction boundaries in docs/reuse.md.
- [x] Define a clearly marked draft input contract with separate part assets,
  occurrence transforms, instructions and inventory.
- [x] Generate/check the synthetic two-part/three-occurrence STEP fixture.
  FreeCAD 1.1.3 exported/reimported two valid solids with expected dimensions and
  volumes; nested pin positions are -25/+25 mm and final base/pin overlap is zero.
  Required quantities and the three sample additions reconcile. Receipt:
  `examples/three-part-fixture/geometry-validation.json`.
- [ ] Implement a real import/inspect command and useful schema/identity checks.
- [ ] Produce a visual inventory and three rendered steps for that fixture.
- [ ] Build matching local HTML and PDF; inspect images, links and page breaks.
- [ ] Coordinate the production export contract with the CAD/Windows agent.
- [ ] Validate an accepted enclosure subassembly and retain the joystick example
  as a second consumer/regression case for extracted shared rendering behavior.

## First implementation sequence

1. Read the handoff and original sources. Propose the smallest concrete commands
   and any draft-contract changes; communicate exporter needs through the mailbox.
2. Validate fixture paths/hashes, identities, hierarchy and units. Import STEP in
   FreeCAD/OCCT, check geometry and emit render meshes with occurrence mappings.
3. Extract a small configurable part of the existing Blender renderer. Produce
   part thumbnails and three cumulative steps with consistent cameras, highlights,
   approach arrows and per-step part quantities. Add focused regressions for the
   data and geometry behaviors being introduced.
4. Reuse the Pandoc/Typst publishing pipeline and MkDocs/site patterns. Generate
   the web and PDF views from the same step data. Keep interactive viewing optional.
5. Test a second scene, including nested/repeated parts and explicit scale/frame
   conversion. Review representative renders and print pagination. Report actual
   versions, hashes, commands and remaining limitations.
6. Obtain a complete accepted production scene and explicit procedure decisions;
   validate on a physical build before claiming a final assembly manual.

## Decisions and boundaries

- A broad repository name with assembly manuals as the first feature.
- Reuse existing renderer, overlays and PDF code gradually; no wholesale move of
  project scripts or large assets. Existing source projects remain operational.
- Keep KiCad and Autodesk adapters separate. Linux documentation generation must
  not require proprietary CAD software at render/publish time.
- Draft-1 is an illustrative contract, not a frozen API. Stable identities and
  explicit coordinate conventions take priority over compatibility by guessing.
- Track compact inputs; large generated outputs go outside ordinary Git history.
- Native production CAD acceptance, inventory counts and actual assembly order
  remain the project team's responsibilities, supported by tooling evidence.

## Verification and handoff

Fixture geometry checks passed as recorded above. The base Guix environment
was verified with Python 3.12.12, PyYAML 6.0.3 and Git. Local documentation links,
JSON parsing and fixture/asset receipt hashes were checked. Renderer, site, PDF,
general validation and production assembly checks have not been implemented/run.
The next agent should update this plan as it works and report via the shared
coordination area described in the ignored local handoff. No extra agent starts
automatically and no commits, pushes or publication are part of this scaffold.
