# Environment plan

Four small Guix roles, one per stage, exchanging files only. They use the
session's Guix package set (no channel pin yet); the versions below were
observed on 2026-10-21 and are also recorded in every stage's receipt.

| Role | Definition | Verified contents | Used by |
| --- | --- | --- | --- |
| Base | `manifest.scm` | Python 3.12.12, PyYAML 6.0.3, pytest 9.0.2, Git | `inspect`, the test suite |
| CAD | `.guix/manifest-cad.scm` | FreeCAD 1.1.3 (`FreeCADCmd`) | fixture generator, `cad_mesh.py` |
| Render | `.guix/manifest-render.scm` or Pixi `render` | Blender 4.5.10 (Guix, no denoiser) or bpy 4.5.14 wheel (Pixi, OpenImageDenoise); see below | `render.py` |
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

## Blender: two routes, one renderer

| Route | Blender | Cycles denoiser | Use |
| --- | --- | --- | --- |
| Guix `.guix/manifest-render.scm` | 4.5.10 LTS package | **none** (`scene.cycles.denoiser` cannot be set) | EEVEE Next renders, previews, machines without Pixi |
| Pixi `render` environment (`pixi.toml`, `pixi.lock`) | 4.5.14 LTS as the official `bpy` wheel, Python 3.11 | OpenImageDenoise present | **Cycles, the reference look** |

Cycles path tracing is the default engine in `render_settings.py`: contact
shadows, physically based shading and the same look as the joystick atlas.
`render.py` records `engine` and `denoiser` in the receipt, and the manual's
build record prints them. The pipeline script picks the route with
`--renderer guix|pixi`; the Guix route passes `--engine BLENDER_EEVEE_NEXT`
unless told otherwise, because Cycles without a denoiser is grainy.

```sh
export PATH="$HOME/.pixi/bin:$PATH" CONDA_OVERRIDE_GLIBC=2.41   # the override only inside a Guix shell
pixi install -e render                                            # downloads the bpy wheel once
pixi run -e render bpy-info                                       # version and denoiser check
tools/build-fixture.sh --renderer pixi                            # Cycles manual of the three-part fixture
```

The denoiser enum reads as empty in background mode even when the build has
OpenImageDenoise; `tools/bpy_info.py` tests the assignment instead. Inside a
Guix shell Pixi cannot detect the host glibc and needs `CONDA_OVERRIDE_GLIBC`
set to the host version (2.41 on this Debian 13 host); outside Guix nothing is
needed. Only linux-64 is locked and verified.

Cost, measured on this 16-core machine at 1600 px, 64 adaptive samples with
the denoiser: about 11 s per step view, about 47 s when the shadow-catcher floor
is on (Cycles renders a second pass for the catcher, whatever its size), 16 s
per 600 px thumbnail with the floor. The default therefore keeps the floor for
thumbnails and the overview only (`floor.views` in `render.json`). EEVEE Next
takes under a second per view and is used for previews; its images have no
contact shadows. Headless rendering works with or without `DISPLAY`.

## Typst and Poppler

Typst compiles the generated `manual.typ` with its bundled fonts (no network).
Poppler reads the PDF back for the agreement checks and rasterises pages for
inspection; ImageMagick writes greyscale copies of the step images. A headless
browser is not part of any role; the HTML was checked structurally and the PDF
visually. The checks report which tools were absent as `not-run`, never as
passed.

`pixi.toml` also has a default environment (Python, PyYAML, pytest) with
`test`, `inspect`, `manual` and `check` tasks for machines without Guix; the
PDF and Poppler checks still need `typst` and Poppler on PATH there. FreeCAD is
not in Pixi; the CAD stage uses the Guix role.
