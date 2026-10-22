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

### Production fields (accepted since 2026-10-21, after the first Windows per-part export)

The Windows adapter's `part-assets/scene.json` (37 parts, 16 groups, 155
occurrences) added provenance and native-structure fields. They are accepted as
optional fields and validated; none of them changes geometry or quantities:

| Where | Field | Rule |
| --- | --- | --- |
| `coordinate_system` | `up_axis: "+Y"` with `basis_to_z_up` | A +Y-up native scene must declare the rigid matrix taking native coordinates to the +Z-up scene frame; it must map +Y to +Z with no translation. It is applied **once, at the root**; every resolved world transform, camera and approach offset is then in the +Z-up frame. Instruction views are authored in that frame. `note` is free text. |
| `source` | any scalar-valued keys | Provenance (Vault ids, exporter, scope note) is carried as data; nested structures are rejected. |
| `parts[]` | `model_state`, `bodies{surface_bodies, solid_bodies, visible_solid_bodies}`, `volume_mm3`, `bom_structure_default`, `properties{…}`, `source{…}` | Scalars only inside `properties`/`source`; `identifying_dimensions_mm.extent` may be a three-number box. When `extent` or `volume_mm3` is present the CAD stage compares it with the imported geometry. |
| `assemblies[]` | `document`, `bom_structure`, `model_state`, `suppressed`, `visible`, `flexible` | `suppressed: true` is rejected (omit the group or extend the contract). |
| `occurrences[]` | `transform_world`, `position_overridden_vs_definition`, `parent_flexible`, `visible`, `visible_effective`, `suppressed`, `grounded`, `mirrored`, `bom_structure`, `model_state` | `transform_world` (native frame) must equal the composed parent chain (checked, 1e-6 relative). `suppressed: true` and `mirrored: true` are rejected. `bom_structure: "Reference"` marks reference-only geometry: rendered for context, never installed, excluded from `required`. |

Identifiers are any non-empty strings without control characters or surrounding
whitespace (Vault paths, `name|[ModelState]` keys and `A:1/B:2` occurrence paths
are fine); file names derive from them through `names.slug`. A UTF-8 byte-order
mark at the start of a manifest is tolerated. `instructions.json` is optional:
without it the pipeline produces the parts inventory and overview only, and the
outputs say so. `python3 -m mechanical_docs inventory-template PROJECT` writes a
draft inventory whose `required` equals the installed occurrences per part;
that is an installed quantity, not a purchase list or stock.

Flexible subassemblies: every assembly *occurrence* already has its own group
id (`CAMERA FRAME:1`, `FREE STANDING FRAME:1/CASTER ASSEMBLY:2`) and its own
child poses in `scene.json`. What may be shared between instances is the
definition (the document and the parts' geometry); what may not be shared is
the instance poses, so the exporter writes the instance transforms of a
flexible occurrence's children and records that they differ from the
definition with `parent_flexible` and `position_overridden_vs_definition`.
Nothing further is needed from the exporter: no second set of group ids, and
no per-definition geometry variant.

Occurrence ids are **snapshot-scoped paths**: they are stable within one
export (`source.occurrence_id_scope` says so) and may change when the native
assembly is refreshed. Documents, receipts and evidence therefore name the
snapshot (scene id, Vault version) with every occurrence id, and nothing
compares occurrence ids across snapshots. A refresh-stable key remains an
open exporter request.

Per-asset units: accepted and preferred over re-export. FreeCAD imports every
STEP as millimetres whatever the file declares, so the CAD stage reads the
file's own unit from the `LENGTH_UNIT` referenced by
`GLOBAL_UNIT_ASSIGNED_CONTEXT` (`stepinfo.py`), requires it to equal the
manifest's asset unit, and records bounds in millimetres with the factor to
metres; a manifest `extent` must then match the imported extent within the
larger of 2 mm and 1 % (Inventor's range boxes are conservative on curved
faces; the enclosure's 37 parts deviate by at most 1.445 mm). The declared
unit is provenance and a consistency check only; it is never applied to the
kernel's coordinates (a 47-inch panel reads back as 1193.8 mm and stays so).

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
a part without an inventory row, a suppressed or mirrored occurrence, a declared
world matrix that disagrees with the hierarchy, and an installed-occurrence count
that includes reference-only geometry.

Findings that are not errors: two occurrences of one part at the same world
pose (within 1e-6 of the scene's extent) are a CAD ambiguity, not a rejected
input. The loader keeps and counts both, records the pair
(`Scene.coincident`, `inspect` prints a FINDING line), and the documents say
on their status block and on the part's card that the count needs review
before it becomes stock. The enclosure snapshot has one such pair (the tank at
the root and the tank under the upper support frame, deviation 2.5e-12 mm),
which the Linux CAD agent's independent FreeCAD survey also found.

Unit handling: each asset declares its own unit, which the CAD stage verifies
against the STEP file and normalises to millimetres; the scene's transforms,
camera coordinates and approach offsets are in the scene's units. Each is
converted to metres with its own factor exactly once (`geometry.py`), and the
render stage checks the imported mesh bounds against the CAD stage's record so
a double or missing conversion fails loudly. The `examples/two-bases-fixture`
scene (centimetres, millimetre assets, a station rotated 90°), the
`examples/units-fixture` scene (an inch, +Y-up scene with a real inch STEP, a
centimetre STEP and a millimetre STEP, derived from the millimetre fixture by
rewriting only the unit context; `tests/test_cad_stage.py` runs FreeCAD on it
and also requires an asset declared in the wrong unit to be refused) and the
enclosure snapshot (inch, mm and cm assets, +Y-up native frame) exercise this.

### Illustration settings (`render.json`, optional)

Per project, beside the manifests. Only appearance and which illustrative
views exist: `looks` (part id → palette name), `palette` additions, `engine`,
`samples`, image sizes, `aspect`, `fill`, outline and arrow styling, the
line-art budget (`lines.max_triangles`, above which a view is drawn without
Freestyle and the receipt says so), the long-part thumbnail rules
(`thumbnail_long_aspect`, default 4: a part whose longest extent is at least
four times the next is turned with its long axis along X, drawn in a wide
image and given an end view `part-<id>-end.png` looking straight along that
axis; `thumbnail_long_px`, `thumbnail_long_direction`, `thumbnail_end_view`),
and `inspection_groups`: assembly ids rendered alone as subassembly inspection
views (`group-<id>.png`, every occurrence under the group at its canonical
pose, framed from `group_direction`). The render CLI's `--groups` adds to that
list. Unknown fields, unknown look names and unknown assembly ids are
rejected. It cannot change geometry, identity, quantities or order, and an
inspection view is never an assembly step: nothing is exploded, hidden or
reordered inside the group, and the receipt records the group's occurrence
ids, parent and path.

### Stage outputs

| File | Written by | Content |
| --- | --- | --- |
| `inspect.json` | `python3 -m mechanical_docs inspect` | validated parts, occurrences with world transforms, steps with cumulative state, inventory reconciliation, input hashes |
| `meshes/<part>.glb`, `meshes/meshes.json` | `cad_mesh.py` (FreeCADCmd) | one GLB per part (metres, +Y up, conversion recorded in the asset extras), declared STEP unit versus manifest unit, STEP validity/bounds/volume, mesh winding and volume checks, tessellation attempts under the per-part triangle budget, hashes |
| `renders/*.png`, `renders/hotspots/*.json`, `renders/render-receipt.json` | `render.py` (Blender) | thumbnails (wide ones plus end views for long parts), overview, subassembly inspection views (`group-*.png` with occurrence ids, parent and path), step and result images; projected occurrence boxes; versions, engine, denoiser, settings hash, per-view hashes, visible triangles and whether line art was drawn, which views were copied from an earlier receipt (`--reuse`, same inputs/meshes/engine only, `reused_from` per view), mesh-bounds and pose-restoration checks |
| `manual/manual.json`, `index.html`, `manual.typ`, `<id>.pdf`, `build-receipt.json` | `python3 -m mechanical_docs manual [--appendix]` | the single document model and both outputs generated from it: picture-led parts cards (CAD quantity labelled as such, blank counted box), one page per subassembly inspection view, overview, steps, a compact build record; `--appendix` adds the technical appendix (full part ids, Vault ids, occurrence lists, every hash), which manual.json always carries |
| `manual/check-report.json`, `manual/checks/` | `python3 -m mechanical_docs check` | HTML/PDF/manual.json agreement (parts, CAD quantities, subassembly sections and their part counts, step order), link and image resolution, page rasters and greyscale copies |

Each stage refuses inputs whose hashes differ from the receipt it consumes, and
refuses receipts that report failed checks or partial renders.

## Exporter fields requested from the Windows adapter

Status 2026-10-21: items 1 to 5 below are met by `Export-PartAssets.ps1`'s
output except a refresh-stable occurrence key (ids are snapshot-scoped paths,
declared as such in `source.occurrence_id_scope`); the raw inventory file
(`inventory-raw.json`) serialised as a PowerShell type name and is not used.

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
