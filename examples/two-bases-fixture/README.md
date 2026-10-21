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

It is a documentation fixture only: not a product, not a manufactured design and
not a validated procedure. Build it with `tools/build-fixture.sh examples/two-bases-fixture --renderer pixi`
(Cycles) or without `--renderer` for the Guix Blender's EEVEE.
