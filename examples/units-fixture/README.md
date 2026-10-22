# Units fixture

Three parts, three declared units, one small scene, so that a unit or frame
mistake anywhere in the pipeline shows up as a 10× or 25.4× size error that
the CAD stage's extent check and the render stage's bounds check catch:

| Part | File | Declared unit | Geometry as read |
| --- | --- | --- | --- |
| `pin-in` | `assets/pin-in.step` | inch (`CONVERSION_BASED_UNIT('INCH')`, 25.4 mm, as Inventor writes it) | Ø254 × 762 mm |
| `base-cm` | `assets/base-cm.step` | centimetre (`SI_UNIT(.CENTI.,.METRE.)`) | 1000 × 600 × 80 mm |
| `pin-mm` | `assets/pin-mm.step` | millimetre (unchanged) | Ø10 × 30 mm |

The scene is in **inches**, its native frame is **+Y up** with a declared
`basis_to_z_up`, each occurrence rotates the part's Z axis onto native Y, and
the two pins sit in a nested `stand` group translated −10 in; the expected
+Z-up world positions are in `fixture-receipt.json`. A three-step draft
sequence with inch approach offsets and a `stand` inspection view exercise the
camera, arrow and group paths in scene units.

FreeCAD cannot write STEP files in inches or centimetres, so the inch and
centimetre files are the three-part fixture's millimetre files with **only
their unit context rewritten**; every coordinate is byte-identical
(`tests/test_units_fixture.py` checks this and the hashes). They are synthetic
fixtures, not products; the 10-inch pin is not a part of anything.

```sh
python3 examples/units-fixture/generate_fixture.py                                   # rewrite the derived files
guix shell --pure -m manifest.scm -- python3 -B -m pytest -q tests/test_units_fixture.py
guix shell --pure -m manifest.scm -m .guix/manifest-cad.scm -- python3 -B -m pytest -q tests/test_cad_stage.py   # FreeCAD reads 254/1000/10 mm
tools/build-fixture.sh examples/units-fixture --renderer pixi                          # full build into build/units-fixture/
```

`tests/test_cad_stage.py` also declares the inch file as millimetres in a copy
and requires the stage to refuse it, naming both units.
