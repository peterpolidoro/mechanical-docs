# Environment plan

Four small Guix roles, one per stage, exchanging files only. They use the
session's Guix package set (no channel pin yet); the versions below were
observed on 2026-10-21 and are also recorded in every stage's receipt.

| Role | Definition | Verified contents | Used by |
| --- | --- | --- | --- |
| Base | `manifest.scm` | Python 3.12.12, PyYAML 6.0.3, pytest 9.0.2, Git | `inspect`, the test suite |
| CAD | `.guix/manifest-cad.scm` | FreeCAD 1.1.3 (`FreeCADCmd`) | fixture generator, `cad_mesh.py` |
| Render | `.guix/manifest-render.scm` | Blender 4.5.10 LTS: EEVEE Next, Cycles CPU, Freestyle, glTF I/O; **no OpenImageDenoise** | `render.py` |
| Publish | `.guix/manifest-publish.scm` | Typst 0.15, Poppler 22.09 (`pdftotext`, `pdfinfo`, `pdftoppm`, `pdfimages`), ImageMagick 6.9 | `manual`, `check` |

```sh
guix shell --pure -m manifest.scm -- python3 -B -m pytest -q tests
tools/build-fixture.sh                      # all five stages on examples/three-part-fixture
tools/build-fixture.sh examples/two-bases-fixture --preview
```

`--pure` shells contain only the manifest's packages: there is no `sh`, `env`
or coreutils unless listed, so the wrapper script runs each tool directly.

## FreeCAD

`FreeCADCmd script.py --pass ARGS` runs the script with `sys.argv` equal to
`['FreeCADCmd', 'script.py', '--pass', ARGS...]`; positional arguments without
`--pass` are opened as documents. The script runs in FreeCAD's own namespace,
not as `__main__`, and an uncaught exception is printed as one line while the
process still exits 0, so `cad_mesh.py` prints its own traceback and the
pipeline tests for the receipt file rather than the exit status. FreeCAD's
Python ABI is separate from Blender's; the two stages share only files.

## Blender

The Guix `blender` package renders headless (also with no `DISPLAY`) with
EEVEE Next, Cycles on the CPU, Freestyle lines and the glTF importer. Its
Cycles has no denoiser (`scene.cycles.denoiser` has an empty enum), which the
joystick atlas worked around with the official `bpy` wheel through Pixi. The
render stage therefore defaults to **EEVEE Next**: noise-free, about 0.7 s per
1600 px view on this machine, and sufficient for flat instruction illustration
with Freestyle outlines. `--engine CYCLES` works and records
`"denoiser": null` plus a warning in the receipt. A Pixi `bpy` environment
remains an option when photographic shading matters; none is set up here.

## Typst and Poppler

Typst compiles the generated `manual.typ` with its bundled fonts (no network).
Poppler reads the PDF back for the agreement checks and rasterises pages for
inspection; ImageMagick writes greyscale copies of the step images. A headless
browser is not part of any role; the HTML was checked structurally and the PDF
visually. The checks report which tools were absent as `not-run`, never as
passed.

No Pixi configuration or lock has been added. If one is added, mirror the
joystick repository's `render` feature (Python 3.11 + `bpy` 4.5) and verify the
denoiser before claiming parity with its images.
