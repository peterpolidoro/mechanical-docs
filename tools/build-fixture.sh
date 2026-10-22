#!/bin/sh
# Build a fixture's manual end to end.
#
#   tools/build-fixture.sh [PROJECT_DIR] [BUILD_DIR] [--preview] [--engine ENGINE] [--renderer guix|pixi] [--groups A,B] [--appendix]
#
# Stages (each in its own managed environment, exchanging files only):
#   1. inspect   Guix base     validate manifests, report parts/occurrences/hashes
#   2. cad       Guix freecad  STEP -> per-part GLB + meshes.json (geometry checks)
#   3. render    Guix blender  thumbnails, overview, step images + render-receipt.json
#                or Pixi bpy   (--renderer pixi: the official Blender wheel with OpenImageDenoise;
#                              inside a Guix shell set CONDA_OVERRIDE_GLIBC to the host glibc, e.g. 2.41)
#   4. manual    Guix publish  manual.json, index.html, manual.typ, PDF
#   5. check     Guix publish  HTML/PDF/manual.json agreement, links, images, page rasters
# --groups adds isolated subassembly inspection views (assembly ids; render.json's
# inspection_groups are rendered anyway); --appendix prints the technical appendix.
# --engine passes CYCLES or BLENDER_EEVEE_NEXT to the render stage. Without it the
# Guix renderer uses EEVEE (no denoiser in that Blender) and the Pixi renderer the
# project's default, Cycles with OpenImageDenoise. Exit status is non-zero at the
# first failing stage. Outputs go under BUILD_DIR (ignored by Git). Nothing here
# claims a procedure is physically validated.
set -eu
here=$(cd "$(dirname "$0")/.." && pwd)
project=""; build=""; preview=""; engine=""; renderer="guix"; groups=""; appendix=""
while [ $# -gt 0 ]; do
  case "$1" in
    --preview) preview="--preview" ;;
    --engine) engine="$2"; shift ;;
    --renderer) renderer="$2"; shift ;;
    --groups) groups="--groups $2"; shift ;;
    --appendix) appendix="--appendix" ;;
    --*) echo "unknown option $1" >&2; exit 2 ;;
    *) if [ -z "$project" ]; then project="$1"; elif [ -z "$build" ]; then build="$1"; else echo "too many arguments" >&2; exit 2; fi ;;
  esac
  shift
done
project=${project:-"$here/examples/three-part-fixture"}
case "$project" in /*) ;; *) project="$here/$project" ;; esac
build=${build:-"$here/build/$(basename "$project")"}
renders="$build/renders${preview:+-preview}"
manual="$build/manual${preview:+-preview}"
# The Guix Blender has no denoiser, so without an explicit --engine the Guix path
# renders EEVEE; the Pixi bpy wheel uses the project's default (Cycles).
if [ -z "$engine" ] && [ "$renderer" = "guix" ]; then engine="BLENDER_EEVEE_NEXT"; fi
engine_arg=""; [ -n "$engine" ] && engine_arg="--engine $engine"
mkdir -p "$build"
cd "$here"
echo "== 1/5 inspect"
guix shell --pure -m manifest.scm -- python3 -B -m mechanical_docs inspect "$project" --json "$build/inspect.json"
echo "== 2/5 cad (FreeCAD)"
guix shell --pure -m .guix/manifest-cad.scm -- FreeCADCmd mechanical_docs/cad_mesh.py --pass "$project" "$build/meshes" 2>&1 | grep -E '^\[cad_mesh\]|Error|Traceback' || true
test -f "$build/meshes/meshes.json"
echo "== 3/5 render ($renderer)"
case "$renderer" in
  guix) guix shell --pure -m .guix/manifest-render.scm -- blender -b --python mechanical_docs/render.py -- "$project" "$build/meshes/meshes.json" "$renders" $preview $engine_arg $groups 2>&1 | grep -E '^\[render\]|Error|Traceback' | grep -v 'strokes set empty' || true ;;
  pixi) pixi run -e render render "$project" "$build/meshes/meshes.json" "$renders" $preview $engine_arg $groups 2>&1 | grep -E '^\[render\]|Error|Traceback' | grep -v 'strokes set empty' || true ;;
  *) echo "unknown renderer $renderer (guix|pixi)" >&2; exit 2 ;;
esac
test -f "$renders/render-receipt.json"
echo "== 4/5 manual (HTML, Typst, PDF)"
guix shell --pure -m .guix/manifest-publish.scm -- python3 -B -m mechanical_docs manual "$project" --renders "$renders" --out "$manual" --meshes "$build/meshes/meshes.json" $appendix
echo "== 5/5 check"
guix shell --pure -m .guix/manifest-publish.scm -- python3 -B -m mechanical_docs check "$manual"
echo "done: $manual"
