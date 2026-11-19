# Two-bases synthetic fixture

A second regression scene built from the three-part fixture's STEP assets (copied,
same hashes). It exists to show that the core has no two-station, fixed-name or
model-size unit heuristics:

- Scene units are **centimetres** while both assets are in millimetres; the pipeline
  must convert each exactly once (translations, camera, approach offsets).
- Two nested levels under each station (`station-b` → `station-b-pins`), and
  `station-b` is **rotated 90° about Z** and moved 12 cm in X. World pin positions
  are derived through the rotation, not assumed on the X axis.
- Two bases and four pins: repeated geometry reused, six independent occurrences.
- One step installs two occurrences at once; two steps carry approach hints.
- `place-base-b` requires only `place-base-a`, so prerequisites are not a chain.
- `finishes.json` (since 2026-11-19) says what a picture draws each part
  with, in the form `mechanical-cad`'s flatten step writes it from a
  project's `finishes.toml`; this one is written by hand. The base is
  `clear-acrylic`, a finish of opacity 0.35, and is drawn so: the pins show
  through it. The pin's finish is `brass`, and `render.json` names the look
  `red-plastic` for it, which holds: the pin is drawn red. So the fixture
  runs both the finish and the precedence of `render.json` through a real
  render, and changing the base's colour is the case to try `--reuse` on (it
  renders again the five views that show a base in its look and copies the
  six that show pins).

It is a documentation fixture only: not a product, not a manufactured design and
not a validated procedure. Build it with `tools/build-fixture.sh examples/two-bases-fixture --renderer pixi`
(Cycles) or without `--renderer` for the Guix Blender's EEVEE. A picture of
it outside a manual, after the build has made the meshes:
`pixi run -e render still examples/two-bases-fixture build/two-bases-fixture/meshes/meshes.json build/two-bases-fixture/stills --views iso,+z`.
