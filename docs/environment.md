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

Line art is the expensive part on production geometry, not path tracing.
Freestyle builds a view map over every visible edge and its cost grows
superlinearly with edge count: the first enclosure overview (155 occurrences,
5.2 million triangles at 0.05 mm deflection, threaded hardware included) took
93 minutes for one 1600 px image while a 320-vertex panel thumbnail took 10 s
and a 132 000-triangle corner cube 123 s. Two budgets keep this bounded:
`cad_mesh.py --max-triangles` (default 50 000 per part) re-meshes a part from a
freshly read shape with the deflections coarsened by 1.6 per attempt until it
fits, recording every attempt in `meshes.json`; and `lines.max_triangles` in
the render settings (default 3 million visible triangles, 400 000 for
previews) renders a view without Freestyle when the visible geometry exceeds
it, with a warning in the receipt and `lines: false` on the view record.
`--no-lines` turns Freestyle off for a whole run. Measured after the budgets
on the same enclosure (2.44 million triangles, 37 parts, 155 occurrences): CAD
stage 2 min 22 s, thumbnails 9.5 to 23 s each, overview 51 s without lines and
32 min with them. Grease Pencil Line Art is the candidate replacement if that
is still too slow for step views; it has not been tried in background mode here.

Two mechanisms keep a production rebuild short. `render.py --reuse DIR` copies
every planned view that an earlier complete receipt holds for the same scene,
asset and instruction hashes, mesh hashes, engine and quality (the inventory
and the supplement never change an image, so a new stock record or supplement
row does not invalidate a receipt; image hash re-verified, `reused_from`
and `reused_generated_at_utc` on the view record naming the receipt that
rendered it; a view copied again in a later pass keeps that original
provenance and lists the intermediate receipts in `reused_via`) and renders
only the views named in `--views`, absent from that receipt, or stale under
the current settings (`reuse.py`: a joint close-up whose occurrences, context,
context style or explicit direction changed, and any view drawn without
outlines that the current `lines.max_triangles` would now outline; a lower
budget never discards an outlined image, so the 32-minute overview survives;
the receipt lists the stale ones in `stale_reused_views`; other appearance
changes such as looks, group directions or `--no-lines` still need `--views`); the enclosure's project-side `render.json` caps line art at
400 000 visible triangles, so no full-assembly view runs Freestyle. Measured on
2026-10-22 on the enclosure (Cycles, denoiser, 64 adaptive samples): seven wide
1200 × 600 thumbnails of long extrusions 21 to 22 s each with the floor, their
600 px end views 3.4 to 3.9 s each, three subassembly inspection views
(1600 × 1200, floor, Freestyle on 55 000 to 91 000 visible triangles) 62 to
82 s each; 17 views rendered and 31 reused in 6 min 25 s for the whole receipt,
against 39 min for the full first render.

The shadow-catcher floor sits just under the lowest visible point of a view;
a camera at or below that plane (a joint seen from below the frame) would see
only the catcher, so such a view is rendered without the floor, recorded per
view in `floor_shadow_catcher`. Freestyle on a frame context at the 600 000
budget: the camera frame group (472 340 triangles) took 446 s and the
free-standing frame (546 280) 233 s on 2026-10-22, against 147 s for the
tank support frame at 343 000.

A joint close-up (`joint_views`) costs about what a subassembly view costs
at the same size: on the three-part fixture at 1600 × 1200 with the floor,
the `pin_to_base` close-up (two subject occurrences, one faded context
occurrence, Freestyle on) took 57 s against 59 s for the `pin-pair`
inspection view and 58 s for the overview (Cycles, denoiser, 64 adaptive
samples; the floor's second pass dominates on so small a scene). On the
enclosure a close-up of a few parts will stay well under the line budget, so
it renders with outlines even where the frame views do not.

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
