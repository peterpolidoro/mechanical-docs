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

## Implemented subset (2026-10-21)

`mechanical_docs/manifest.py` implements exactly the fields above and rejects
everything else with one combined error listing every problem. Accepted:

| File | Fields |
| --- | --- |
| scene | `schema_version` (`draft-1`), `id`, `title`, `units` (mm, cm, m, in), `coordinate_system` (`handedness` must be `right`, `up_axis` must be `+Z`, `origin`), `source` (`kind`, `generator`, `qualification`, `revision`, `exporter`, `exported_at`), `parts[]` (`id`, `name`, `asset{path, format=step, units, sha256}`, `identifying_dimensions_mm`, `description`), `assemblies[]` (`id`, `parent_id`, `transform`, `name`), `occurrences[]` (`id`, `part_id`, `parent_id`, `transform`, `name`) |
| instructions | `schema_version`, `scene`, `id`, `title`, `review_state` (draft, cad-reviewed, physically-validated), `views[]` (`id`, `projection`, `eye`, `target`, `up`), `steps[]` (`id`, `requires`, `add`, `view`, `caption`, `approach{occurrence_id, start_offset, end_offset, validation}`) |
| inventory | `schema_version`, `scene`, `status`, `items[]` (`part_id`, `required`, `unit`, `counted`) |

Rejected, each with a message naming the field: unknown fields, a wrong schema
version, an absolute or root-escaping asset path, a missing file, a SHA-256
mismatch, duplicate ids (assemblies and occurrences share one namespace),
unknown parts/parents/views/occurrences, a hierarchy without exactly one root
or with a cycle, a non-rigid transform (scale, shear, or a reflection: mirror
a geometry variant explicitly instead), a prerequisite that is not an earlier
step, an occurrence installed twice or never, an assembly group listed as an
installed part, an approach hint for an occurrence the step does not add, a
non-zero `end_offset`, a `validation` other than `unverified-render-hint`,
an inventory `required` that differs from the installed occurrence count, and
a part without an inventory row. Identifiers match `[A-Za-z0-9][A-Za-z0-9._-]*`.

Unit handling: asset bounds and meshes are in the asset's declared units; the
scene's transforms, camera coordinates and approach offsets are in the scene's
units. Each is converted to metres with its own factor exactly once
(`geometry.py`), and the render stage checks the imported mesh bounds against
the CAD stage's record so a double or missing conversion fails loudly. The
`examples/two-bases-fixture` scene (centimetres, millimetre assets, a station
rotated 90°) exercises this.

### Illustration settings (`render.json`, optional)

Per project, beside the manifests. Only appearance: `looks` (part id → palette
name), `palette` additions, `engine`, `samples`, image sizes, `aspect`, `fill`,
outline and arrow styling. Unknown fields and unknown look names are rejected.
It cannot change geometry, identity, quantities or order.

### Stage outputs

| File | Written by | Content |
| --- | --- | --- |
| `inspect.json` | `python3 -m mechanical_docs inspect` | validated parts, occurrences with world transforms, steps with cumulative state, inventory reconciliation, input hashes |
| `meshes/<part>.glb`, `meshes/meshes.json` | `cad_mesh.py` (FreeCADCmd) | one GLB per part (metres, +Y up, conversion recorded in the asset extras), STEP validity/bounds/volume, mesh winding and volume checks, hashes |
| `renders/*.png`, `renders/hotspots/*.json`, `renders/render-receipt.json` | `render.py` (Blender) | thumbnails, overview, step and result images; projected occurrence boxes; versions, engine, denoiser, settings hash, per-view hashes, mesh-bounds and pose-restoration checks |
| `manual/manual.json`, `index.html`, `manual.typ`, `<id>.pdf`, `build-receipt.json` | `python3 -m mechanical_docs manual` | the single document model and both outputs generated from it |
| `manual/check-report.json`, `manual/checks/` | `python3 -m mechanical_docs check` | HTML/PDF/manual.json agreement, link and image resolution, page rasters and greyscale copies |

Each stage refuses inputs whose hashes differ from the receipt it consumes, and
refuses receipts that report failed checks or partial renders.

## Exporter fields requested from the Windows adapter

The Windows pilot's `placement-report.json` already carries occurrence names,
document paths and hashes, grounded/suppressed/visible flags and row-major 4×4
matrices in centimetres. To feed this contract without guessing, the per-part
STEP plus manifest export should add:

1. A stable occurrence identity that survives a refresh (the Inventor
   occurrence's persistent reference key or at least the full occurrence path),
   with the document's Vault master/version ids and native SHA-256.
2. A part key per distinct document + model state (+ mirror/configuration
   variant), the STEP exported for that key, its SHA-256 and units.
3. The parent occurrence for every occurrence, so nested subassemblies and
   their transforms are preserved rather than flattened; a statement of whether
   each matrix is parent-relative or root-relative and column- or row-vector.
4. Native BOM structure (structured/phantom/purchased/reference), quantity
   fields, suppressed and reference-only flags, and unit of measure, kept raw.
5. Part number, description, material and any fastener specification where the
   iProperties actually have them; `null` where they do not.

Grounding, constraints and surface-body counts are useful evidence but are not
part of the documentation contract. Until these fields exist, the synthetic
fixtures stand in; nothing in the pilot's export has been loaded as a project.
