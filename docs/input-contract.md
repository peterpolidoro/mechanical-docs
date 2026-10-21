# Draft input contract

**Proposal, not an implemented or frozen interface.** The included example uses
`schema_version: "draft-1"`. Coordinate changes with the CAD/Windows agent before
expecting its exports to match. This document is not a substitute for the runtime
validation the next agent must implement.

## Scene (`scene.json`)

| Field | Meaning |
| --- | --- |
| `id`, `title` | Identity and human-readable name of the scene snapshot |
| `units` | `mm` in this first fixture; all transform translations use these units |
| `coordinate_system` | Right-handed, +Z up; origin/local frames explicitly defined |
| `source` | Source kind and qualification; real adapters should add source revision/IDs |
| `parts` | Distinct geometry definitions, identifying dimensions and relative asset paths/hashes |
| `assemblies` | Group IDs, parent assembly IDs and transforms; groups have no stock quantity |
| `occurrences` | Unique installed-instance IDs, part IDs, parent assembly IDs and transforms |

Each asset declares its own format and units. Resolve its path from the directory
containing the scene manifest and reject paths that escape the declared project
root. Verify its SHA-256 before use. The sample's assets are closed-solid STEP files
in mm. Do not infer units from apparent size. Parts/configurations with different
geometry require distinct part keys even if their names are alike.

Transforms are **4 by 4 row-major arrays applied to column vectors**:

```text
p_parent = T_parent_from_child * [x, y, z, 1]^T
T_world_from_child = T_world_from_parent * T_parent_from_child
```

Translation occupies the last column; the last row is `[0, 0, 0, 1]`. The first
milestone uses rigid rotations with determinant +1, and no scale/shear. A mirrored
part should be an explicitly mirrored geometry variant or rejected as unsupported;
do not silently discard a reflection. The fixture's `pin-pair` group translates
+10 mm in X; child pin translations -35 and +15 mm yield world X=-25 and +25 mm.

The part-local frames come from the CAD assets. The fixture base is centered in
XY with its bottom at Z=0; its pin is centered on XY with its bottom at Z=0.
Declare the basis/scale conversion when tessellating to glTF (typically metres,
Y up) and importing into Blender (Z up). Apply each conversion exactly once and
preserve the occurrence-to-mesh mapping. Two instances of one asset stay distinct.

Production extensions should record source-file/version/model-state identities,
configuration/mirror variants, and native BOM classifications. Names and occurrence
paths can change across revisions; flag ambiguous identity mapping. A STEP body
is not automatically a purchased or installed part. Do not manufacture missing
metadata just to satisfy the proposed format.

## Instructions (`instructions.json`)

The document references `scene.json`, gives its review state, defines named camera
views, and lists ordered steps. Each sample step has an ID, prerequisites, the
occurrence IDs it adds, a view ID, a brief caption and an optional approach hint.
Derive cumulative state from the ordered actions; physical occurrences are added
once. Containers such as `pin-pair` are groups, not extra installed parts.

The fixture uses additions only. Moves/removals, repeated operations and branches
are later extensions to be declared and validated, not silently approximated as
additions. Review state is `draft`; the example has no approved physical procedure.
Captions support image generation; the desired pages emphasize pictures/counts.

Camera eye/target coordinates and approach offsets use scene coordinates/units.
Approach offsets are relative to the occurrence's final world pose, for visual
arrows/exploded placement. They are explicitly unverified render hints and carry
no promise of collision-free motion. Rendering must restore canonical placements.

## Inventory (`inventory.json`)

Each row names a part ID, required quantity, unit, and `counted` value. Null means
not counted. The example's one base and two pins are synthetic required quantities,
not available physical stock. Future production inventory must distinguish kits,
installed items, spares and consumables as described in the requirements.

## Receipts and checks

`geometry-validation.json` is a fixture-generator receipt. It records exported
STEP hashes/validity/bounds/volume and the known final placements/clearance check.
It is not a general schema validator, render result, site build or assembly-path
qualification. No generated fixture result establishes production acceptance.

The future build should hash the scene, instructions, inventory and relevant
render/publish settings, plus asset hashes and software versions. Reject missing
files, unknown/duplicate IDs, hierarchy cycles, bad transforms, wrong checksums,
unsatisfied prerequisites, duplicate installation and quantity inconsistencies.
Do not treat a matching input manifest as proof that every output file exists or
is current; verify those separately before a manual release.
