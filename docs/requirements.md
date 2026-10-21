# Visual documentation requirements

The first output should let a mechanical technician identify the required parts,
check actual stock, and follow small illustrated assembly steps with minimal
dependence on prose. Render the actual CAD parts. Use clear numbers, silhouettes,
arrows and symbols; include short precise labels where a picture cannot adequately
communicate a size, orientation or operation.

## Inventory and identification

- Give each part a stable label, thumbnail, required quantity and distinguishing
  dimensions/material/finish when known. Similar-looking fasteners need enough
  detail to identify the correct one.
- Separate reusable part types from individual installed occurrences. Account
  for bought assemblies/kits without counting their contents twice as purchases.
- Separate quantity required from quantity physically found. Unknown stock is
  unknown, not zero and not automatically the CAD quantity. Provide places to
  record counts and checks in both web and print versions.
- Include tools, consumables, temporary fixtures and unmodeled hardware when
  the real procedure needs them. A visually complete CAD scene may omit these.

## Assembly pages

- Show a finished overview, then clear subassemblies and numbered steps.
- At each step show the needed parts/quantities and tools, existing assembly,
  highlighted additions, approach/rotation arrows and expected result.
- Use consistent cameras and explicit view-change indicators. Add close-ups for
  small fasteners, orientation, concealed interfaces and access-sensitive actions.
- Reinforce color with outlines, patterns or symbols. Verify monochrome printing.
- Keep exploded illustration transforms separate from the final installed poses.
- Provide orientation/alignment/fastener checkpoints. A replacement or removal
  guide may share the same geometry while having a separately reviewed sequence.

## Feasibility and evidence

The procedure must account for insertion paths, tool/hand access, temporary
support, cables and relevant tolerances. Where room access restricts subassembly
size, record that as a project constraint. Do not generate an allegedly verified
order solely from final placements or reverse an exploded view and call it proven.

Check explicit prerequisites, cycles, missing/duplicate occurrence installations
and quantity reconciliation. Geometry/path checks support review but have stated
limits. Record whether each procedure is draft, CAD-reviewed or physically
validated. A technician should walk through the real build, correcting the
sequence before the final manual claims to avoid interference or rework.

## Web, PDF and traceability

The same instruction source should produce web and PDF versions with identical
part quantities and step order. Static images must be sufficient to follow the
printed instructions. Interactive 3D and clickable callouts are useful additions;
provide a static fallback and accessible labels rather than requiring WebGL.

Check images, font sizes, page breaks, arrow visibility and links in real outputs.
Record exact CAD/instruction revisions, hashes and tool versions. Distinguish an
accepted complete assembly from a provisional export. Regenerate affected output
when geometry, identity, placement or instructions change.

## First scope

One tiny example with a visual BOM and three to five steps is enough to establish
the pipeline. Then use a real subassembly. Generalizing all hardware documents,
automatically planning arbitrary assemblies or migrating every existing project
is outside that first milestone.
