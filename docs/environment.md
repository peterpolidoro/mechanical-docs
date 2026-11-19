# Environment plan

Four small Guix roles, one per stage, exchanging files only. They use the
session's Guix package set (no channel pin yet); the versions below were
observed on 2026-10-21 and are also recorded in every stage's receipt.

| Role | Definition | Verified contents | Used by |
| --- | --- | --- | --- |
| Base | `manifest.scm` | Python 3.12.12, pytest 9.0.2, Git | `inspect`, the test suite |
| CAD | `.guix/manifest-cad.scm` | FreeCAD 1.1.3 (`FreeCADCmd`) | fixture generator, `cad_mesh.py` |
| Render | `.guix/manifest-render.scm` or Pixi `render` | Blender 4.5.10 (Guix, no denoiser) or bpy 4.5.14 wheel (Pixi, OpenImageDenoise); see below | `render.py`, `viewer.py` (decimation, closest-point anchors; any bpy) |
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
pipeline tests for the receipt file rather than the exit status. FreeCADCmd
1.1.3 also reads a dashed option itself wherever it stands, even after
`--pass`, and stops with its usage text at one it does not know. So the
script's own options go after a bare `--`, which FreeCADCmd takes as the end
of its own and the script drops: `--pass PROJECT OUT -- --max-triangles 20000`
(since 2026-11-19; before that the stage's options could not be given under
FreeCADCmd at all, and every production mesh was made with the defaults).
FreeCAD's Python ABI is separate from Blender's; the two stages share only
files.

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
`cad_mesh.py -- --max-triangles N` (default 50 000 per part) re-meshes a part from a
freshly read shape with the deflections coarsened by 1.6 per attempt until it
fits, recording every attempt in `meshes.json`; and `lines.max_triangles` in
the render settings (default 3 million visible triangles, 400 000 for
previews) renders a view without Freestyle when the visible geometry exceeds
it, with a warning in the receipt and `lines: false` on the view record.
`--no-lines` turns Freestyle off for a whole run. Measured after the budgets
on the same enclosure (2.44 million triangles, 37 parts, 155 occurrences): CAD
stage 2 min 22 s, thumbnails 9.5 to 23 s each, overview 51 s without lines and
32 min with them. Grease Pencil Line Art draws such views in seconds, when a
project asks for it (below).

Line Art is built in since 2026-11-19, behind a setting that is off by
default: `lines.outliner` in `render.json`, or `--outliner` of `render.py`,
`still.py` and `motion.py`, takes `freestyle` (the default: what is described
above), `line-art` (Line Art for every view, whatever its size) or `mixed`
(Freestyle within its budget, Line Art above it). `motion.py` draws lines
only when `--lines` asks for them. One Grease Pencil object carries a Line
Art modifier for a view's context and one for its subject, each over the
collection the Freestyle line set of that name selects, with the same
colours and the same widths in pixels (`lines.subject`, `lines.context`).
What trying it on the enclosure showed, each point looked at in pictures:

- **The broken edges of the thin-walled tank were three things, and none of
  them the wall.** The lines were drawn without anti-aliasing, so the two
  edges of the rim, closer together than a line is wide, ran into each other
  in steps: the final render now samples the strokes sixteen times
  (`aa_samples` of the scene's Grease Pencil settings). The CAD stage writes
  every face of a
  part as a patch of its own, and Line Art takes an edge with one face for an
  outline, so it drew every boundary between two faces, the tangent line of
  a fillet and the seam of a cylinder among them, each twice: the meshes are
  now joined at import when Line Art may draw (`Renderer.weld`, a second for
  the enclosure's 37 meshes, 394 130 vertices to 237 111), with every
  corner's normal carried through, since Blender keeps a custom normal
  relative to the faces around its vertex and joining alone turned them (the
  overview without lines differed in 17 080 pixels of 1.9 million with the
  normals left to themselves and in 9 with them carried). And an edge the
  mesh marks as sharp is not drawn for that alone (`use_crease_on_sharp`
  off): with it every chamfer of a bought part has a line, which Freestyle
  does not draw.
- **Two widths and colours**: the subject's modifier and the context's give
  a step its thick dark and its thin grey lines as Freestyle does; the
  second modifier takes the first one's reading of the scene (`use_cache`).
- **A width holds in a perspective picture**: a stroke's radius is a length
  in the scene, and nodes after the modifiers multiply every point's radius
  by its distance in front of the camera. On the fixture with a 20 mm lens
  the lines are one width near and far with the nodes; without them every
  line is several times too wide, and wider near than far.
- **`--reuse`**: a view's record names what drew its outlines (`outliner`),
  and a view outlined by the outliner the current settings would not use for
  it is rendered again, as is a view without outlines that would now have
  them (reuse.py). Under `mixed` a picture Freestyle outlined is kept
  whatever its size.

Three more things the pictures and the clock showed. Line Art reads every
mesh of the scene, the ones a view hides from the render too: they hide no
line (the pictures are the same to the pixel) and cost their triangles, eight
seconds for a thumbnail of the tank's 604 triangles; each hidden object is
taken out by its own switch (`lineart.usage`) for the call. The strokes are
lit by the studio unless told otherwise, which turned the dark line a pale
blue-grey. And a line comes out as wide as the modifier's `radius`, not
twice that (measured in the Guix Blender; the other one's pictures agree).
The object exists for the render call alone:
the modifier is worked out again at every update of the scene, and framing a
view makes several.

Measured on 2026-11-19 on the enclosure's staged project through
`render.py`, at the manual's full quality (64 samples), 1600 x 1200 and the
thumbnail 600 x 600, on a machine whose sixteen cores were busy with other
work throughout (a load of 30 to 50), so every time is an upper bound:

| View | Visible triangles | EEVEE, Guix 4.5.10: without outlines | with Line Art | Cycles, bpy 4.5.14: without outlines | with Line Art |
| --- | --- | --- | --- | --- | --- |
| the tank alone (thumbnail) | 604 | 0.8 s | 0.9 s | 27.5 s | 23.6 s |
| step 4, twelve parts added | 406 724 | 2.0 s | 4.9 s | 18.8 s | 22.6 s |
| step 8 in perspective, twenty parts added | 1 180 312 | 4.7 s | 12.7 s | 17.2 s | 27.7 s |
| the overview | 2 436 488 | 1.6 s | 13.7 s | 108.5 s | 109.4 s |

Against Freestyle, with EEVEE at the same size: one tank support frame
(343 000 triangles) 1.2 to 2.3 s with Line Art and 17 to 45 s with
Freestyle; the camera frame (472 000) 4 to 6 s and 29 to 31 s; step 5
(523 000) 9 s and 27 s. Freestyle was not run on the overview again (32
minutes on 2026-10-22). Within Freestyle's budget the two draw the same
picture but for details: Freestyle draws an edge inside a part a little
thinner than its silhouette, Line Art draws all at one width. On the whole
enclosure the framing's many edges run together into dark bands with either.
Like Freestyle, Line Art draws no edge behind a translucent part. Back faces
are left out of Line Art's reading (`use_back_face_culling`): with them the
overview took half as long again and differed in 31 pixels. With the default
outliner nothing is joined and no picture changes: the two-bases fixture
rendered by the committed code and by this one gave ten of eleven pictures
the same to the pixel, and the eleventh, the exploded view, differed in 27
pixels, as two runs of the committed code differ from each other (35).

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
the receipt lists the stale ones in `stale_reused_views`; since 2026-11-19 a
view that shows a part whose look or finish changed is stale too, the receipt
recording what every part was drawn with; other appearance
changes such as group directions or `--no-lines` still need `--views`); the enclosure's project-side `render.json` caps line art at
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

Phase-1 step renders, observed on 2026-10-23: with the instructions added to
the enclosure, `--reuse` on the front-page receipt rendered the overview (52 s)
and 18 step images (15 to 38 s each with outlines for the six frame steps up
to 600 000 visible triangles, 6 to 10 s each without above it) in 308 s and
reused the 67 other views; a changed `step_context_alpha` is an appearance
change and needs the step views named with `--views`.

A picture outside a manual (`still.py`, 2026-11-19) runs on either route:
`blender -b --python mechanical_docs/still.py -- SCENE_DIR MESHES_JSON OUT_DIR
--views iso,+z --engine BLENDER_EEVEE_NEXT` in the Guix render role, or
`pixi run -e render still SCENE_DIR MESHES_JSON OUT_DIR --views iso,+z` for
Cycles. On the two-bases fixture (six occurrences) a 720 × 540 still took 12 s
with Cycles, the denoiser and the floor, 3 s seen from below, where the floor
is dropped, and under a second with EEVEE. The studio lights a face that
looks up about seven times as brightly as its colour, with both engines: at
exposure 0 a `#808080` finish is white on top, and at the stills' default of
-2.5 stops it reads back as 140 with Cycles and 139 with EEVEE. EEVEE draws a
translucent finish by blending and shows some blotches in the shadow near
it; Cycles is the reference for such a part too.

A moving picture (`motion.py`, 2026-11-19) runs on either route as a still
does: `blender -b --python mechanical_docs/motion.py -- SCENE_DIR MESHES_JSON
OUT_DIR turntable --engine BLENDER_EEVEE_NEXT` in the Guix render role, or
`pixi run -e render motion SCENE_DIR MESHES_JSON OUT_DIR turntable` for
Cycles. The video is written by Blender's own FFmpeg, which both builds have
(libavcodec 60.31 in the Guix Blender 4.5.10, 61.19 in the bpy wheel 4.5.14):
the frames, read back from disk as an image strip over white in a scene of
its own, as H.264 in an MP4 file or, with `--webm`, VP9. No package was added
for it. `ffprobe` of Guix's `ffmpeg` was used once to look at the files and
agreed with what Blender reads back of them; it is no part of any role.
A frame costs what a still of the same size costs without the floor and
without outlines, which is how frames are drawn unless asked otherwise:
under a second on a fixture with either engine. On the enclosure's scene
with the project's draft finishes (Cycles, 16 samples with the denoiser,
960 x 720, on a machine that was rendering other things at the same time):
a turntable of one tank support frame, 72 frames, 3.6 to 6.0 s a frame and
296 s in all, a file of 1.7 MB; a turntable of the whole enclosure, 72
frames, 2.1 to 3.5 s a frame and 176 s, 0.2 MB; an exploded sequence of the
whole enclosure that comes back together, 95 frames, 2.1 to 5.7 s a frame
and 275 s, 0.3 MB. The same sequence with the shadow-catcher floor took 7 to
17 s a frame and 929 s. With EEVEE in the Guix Blender the whole enclosure
took 0.7 s a frame, 24 frames in 22 s. Outlines (`--lines`) were tried on a
fixture only: Freestyle took 44 s on one frame of the tank support frame.

Joints were drawn on a real assembly for the first time on 2026-11-19, later:
`mechanical-cad`'s mechanical example, 37 parts and 108 occurrences, 344 000
triangles in its meshes and 1.21 million drawn, with EEVEE in the Guix
Blender at 1280 x 720, on a machine busy with other work (a load of 30 on 16
cores), so the times are upper bounds. A still of the whole at a pose took
20.8 s with Freestyle's outlines and 4.6 s with Line Art's. One unit alone
(50 occurrences, 575 000 triangles), its lever through its range with the
two gears turning against each other, with Line Art's outlines: 95 frames,
1.8 to 3.8 s a frame and 238 s in all, a file of 0.2 MB. The whole assembly
seen from above, one unit turning through its arc slot, with Line Art's
outlines: 95 frames, 3.0 to 5.5 s a frame and 346 s, 0.4 MB. Line Art is what
makes outlines affordable in a video: at Freestyle's 20 s a frame the second
would have taken half an hour. The example's scene is declared Z up and
stands Y up, so every one of these pictures names its up (`--up`).

## Typst and Poppler

Typst compiles the generated `manual.typ` with its bundled fonts (no network).
Poppler reads the PDF back for the agreement checks and rasterises pages for
inspection; ImageMagick writes greyscale copies of the step images. A headless
browser is not part of any role; the HTML was checked structurally and the PDF
visually. The checks report which tools were absent as `not-run`, never as
passed.

`pixi.toml` also has a default environment (Python, pytest, and PyYAML, which
nothing imports; it leaves with the next deliberate lock update) with
`test`, `inspect`, `manual` and `check` tasks for machines without Guix; the
PDF and Poppler checks still need `typst` and Poppler on PATH there. FreeCAD is
not in Pixi; the CAD stage uses the Guix role.
