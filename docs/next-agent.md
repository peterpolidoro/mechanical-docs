# Incoming documentation agent

Your task is to implement the first working slice of mechanical-docs. Start with
the included synthetic STEP assembly, then adapt the tools to accepted production
data when it arrives. You can make progress now without a Vault account, Inventor
installation or finished enclosure design.

## Read and inspect first

Read the repository guidance, requirements, draft contract, architecture, reuse
review and living plan linked from README.md. Use .agents/handoff.local.md for
the current local paths and mailbox; the tracked documentation should remain
usable on a machine without those paths.

Inspect the existing code listed in docs/reuse.md. The joystick atlas already
renders isolated/ghosted parts, exploded illustrations and clickable callouts;
its PDF builder already combines revision-pinned documents through Pandoc/Typst.
Generalize these in small steps, keeping project-specific YAML/prose in its
source project. Do not reset or migrate a sibling checkout while another agent
or Peter is using it.

## First deliverable

Use `examples/three-part-fixture/` to produce:

- A visual parts inventory: one base, two pins, thumbnails, identifying sizes,
  required quantities and a place to record quantities found.
- Three assembly steps with a stable camera, pictured parts needed, subdued
  previous parts, highlighted additions and downward pin-insertion arrows.
- A local HTML manual and a printable PDF with the same sequence and images.
- A build receipt linking input files/hashes, renderer/tool versions and outputs,
  plus an honest validation record. No production buildability claim.

Before rendering, report the two part types, three occurrences, nominal sizes,
resolved transforms and source hashes. Check that nested transforms put pins at
X=-25 and +25 mm despite their parent's +10 mm translation. Repeated part geometry
should be reused while instances remain independently selectable.

The example manifests use a proposed `draft-1` format. Implement only the fields
needed for this milestone, with explicit rejection of unsupported data. If a
different format better fits the existing code, revise the example and contract
together and communicate the changes before the Windows adapter depends on it.
Do not pretend an implemented exporter already supplies these files.

## Acceptance evidence

1. STEP dimensions, validity, identities, quantities and placements survive the
   conversion into the render scene. Preserve the known fixture clearances.
2. Each physical occurrence is installed exactly once; missing prerequisites or
   duplicate/unknown IDs cause a clear failure. Future steps' parts are hidden
   unless a deliberate contextual view says otherwise.
3. Rendering a later view cannot leave prior exploded offsets in the next view.
   Frame the visible components and arrows without clipping. Inspect a few
   generated images; do not rely solely on successful process exit codes.
4. Both documents show the same BOM and step order, with legible monochrome output,
   self-contained static images, usable page breaks and no broken image/link paths.
   Distinguish interactive web extras from the printed instructions.
5. A second scene or the joystick example demonstrates that no two-station,
   fixed-name or model-size unit heuristic remains in the extracted core.
6. The plan and handoff identify implemented, failed and unrun checks separately.

## Work that remains with the CAD/project agents

They own accepted Inventor/Vault source versions, assembly export completeness,
per-part/configuration mapping, production placements and project design decisions.
The existing enclosure export is provisional: its 503 native unfiltered surface
bodies versus 479 reimported solids still need reconciliation. A valid shape does
not establish a complete BOM. The project also needs a technician-reviewed order,
actual stock counts, tool access and a physical assembly walkthrough.

Send a small exporter contract request early: identifiers, relative asset paths,
hashes, units/local frames, part variants, occurrence parents/transforms, source
revision and BOM classifications. Report any field that remains unknown explicitly.
Proceed with fixture/renderer/publishing work while that coordination continues.

## Finish the first session

Leave runnable managed commands for the implemented functions, update the plan,
record representative output and verification, and post a timestamped progress
message in the agreed mailbox. Use your own status file. Leave commits/pushes
to Peter unless he asks otherwise. Site/release publication is a separate action;
the first milestone only needs local outputs and reviewable evidence.
