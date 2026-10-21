# Architecture and extraction boundaries

The intended pipeline is:

```text
STEP parts + explicit assembly/part metadata
                  |
            validated scene
                  |
       CAD tessellation + instance map
                  |
     Blender renders and projected callouts
                  |
inventory + reviewed steps + image assets
                  |
      matching static web and PDF output
```

## Scene and procedure data

A part definition describes reusable geometry and identifying metadata. An
occurrence describes a particular installed copy and its placement. Assemblies
group occurrences under explicit transforms. Geometry version, identity,
inventory and instruction numbering are separate concepts.

The canonical scene is the final installed arrangement. The instruction document
describes additions, prerequisites, views and approach hints; derive each rendered
state without changing the canonical transforms. Inventory tracks required and
physically counted quantities separately. See the draft contract for an example.

## Input adapters

Start with per-part STEP plus a sidecar assembly manifest. A full assembly STEP
may also be supported once hierarchy, names and placements are demonstrably
preserved; if identities are missing, require an explicit mapping. Existing GLB
assets can feed the render side with declared identities/units/provenance.

Use FreeCAD/Open CASCADE to inspect and tessellate STEP. Blender consumes meshes,
not STEP directly. Preserve asset/occurrence mappings through tessellation and
document basis/unit conversion. Export tolerance and mesh quality belong in the
build receipt; meshes are derived visualization assets, not replacement CAD.

Inventor/Vault adapters stay in vault-cad-tools. PCB source parsing, KiCad exports,
parts classification and electrical documentation stay in kicad-libs. Consume
their declared outputs without importing their server or application requirements
into the generic rendering core.

## Rendering

Extract studio setup, materials, camera fitting, isolation/ghosting, outline
styles, hotspot projection and view restoration from the existing atlas. Replace
its station assumptions with scene groups/occurrences and explicit frames.
Retain quick previews and selective rendering. Add per-output freshness and
existence checks so partial rendering cannot qualify a full manual release.

An exploded-layout algorithm is useful for arranging an illustration. It is not
an assembly planner. Human-authored steps may carry motion hints; separately
record geometry/path checks and physical validation before claiming feasibility.

## Publishing

Start with existing MkDocs/HTML templates and the Pandoc/Typst PDF builder.
Render both outputs from the same inventory and ordered procedure. Add a template
for image-led steps with quantities, arrows and checkpoints. Bundle static image
fallbacks for web-only content and use predictable local asset paths in PDFs.

Project titles, navigation, explanatory prose, source repositories and cover pages
are configuration/templates, not hard-coded application behavior. Keep publication
separate from building local artifacts. Generated outputs identify the scene,
instructions and software versions that produced them.

## Reproducibility and storage

Hash accepted input assets, instructions and relevant rendering/template settings.
Track outputs per view/page where practical, and invalidate affected results on
change. Do not equate timestamp differences in PDF/PNG/STEP metadata with geometric
or visual changes. Compare the meaningful output and inspect representative pages.

Keep compact source data, scripts and small synthetic fixtures in Git. Ignore
large caches and generated production artifacts. Carry versioned source identities
and build receipts so a saved manual can be traced to its exact design snapshot.
