# Three-part synthetic fixture

One base and two identical pins, designed only to exercise documentation tools.
It is not an enclosure component, a manufactured design or a validated physical
assembly procedure. No source assets from another project are copied here.

- Base: 100 × 60 × 8 mm, with two 10.5 mm through-holes at X=-25 and +25, Y=0.
- Pin: 10 mm diameter × 30 mm long; used twice.
- Root frame: mm, right-handed, XY base plane and +Z upward.
- Both parts' bottoms are at local Z=0. Pins' final bottoms are at world Z=0.
- A nested `pin-pair` assembly has X=+10 mm translation. Its children at X=-35
  and +15 mm therefore occupy world X=-25 and +25 mm.

The nominal 0.25 mm radial gap is synthetic fixture geometry, not a recommended
manufacturing fit. Final-position overlap is checked; insertion path, tools,
tolerances and a physical build are not qualified.

| File | Role |
| --- | --- |
| `generate_fixture.py` | Source geometry and scene generator using FreeCAD |
| `assets/base.step`, `assets/pin.step` | Small derived closed-solid inputs |
| `scene.json` | Generated draft part/occurrence hierarchy and input hashes |
| `instructions.json` | Hand-authored three-step example and camera |
| `inventory.json` | Hand-authored required quantities; no stock record (the deprecated `counted: null` is kept for the generator receipt's hash) |
| `supplement.json` | Hand-authored synthetic supplementary items (not modelled in CAD): a candidate family with unknown quantities and a kit `included_with`, a specified SKU with integers, a counted stock record and a scene-part `included_with`, and an unplaced new-design row; all attached to the `pin_to_base` joint and the `pin-pair` group. Nothing in it is real hardware |
| `render.json` | Illustration settings only (looks, the `pin-pair` inspection view, one `pin_to_base` joint close-up); see docs/input-contract.md |
| `geometry-validation.json` | Generated FreeCAD export/reimport and placement checks |

From the repository root:

```sh
guix shell --pure -m .guix/manifest-cad.scm -- FreeCADCmd examples/three-part-fixture/generate_fixture.py
```

The generator only rewrites its derived files beside itself. It checks the
hand-authored fixture quantities/step IDs against the known scene, but does not
implement the generic validation library. Later renderer output should go under
an ignored directory such as `build/three-part-fixture/`.

The manual shows a pictured inventory, the supplementary items table (the two
existing-design rows; the new-design row only with `--appendix`), the
`pin-pair` inspection view and the `pin_to_base` joint close-up (pin A and the
base framed, pin B faded) each with its "hardware to review" list, placement
of the base, insertion of pin A, and insertion of pin B. Previously installed
parts are subdued, the added part is highlighted, and arrows show the intended
downward approach. Web and PDF are generated from one `manual.json` and
checked against each other.

```sh
tools/build-fixture.sh --renderer pixi   # Cycles (bpy wheel) -> build/three-part-fixture/{inspect.json,meshes,renders,manual}
tools/build-fixture.sh                   # Guix Blender, EEVEE (no denoiser in that package)
tools/build-fixture.sh . --preview       # small, fast images into renders-preview/ and manual-preview/
```

`build/` is ignored by Git. Representative outputs and receipts from the first
build are kept in the shared evidence area named in the local handoff.
