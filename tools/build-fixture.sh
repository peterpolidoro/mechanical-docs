#!/bin/sh
# Build the synthetic fixture's manual end to end with the managed Guix roles.
#
#   tools/build-fixture.sh [PROJECT_DIR] [BUILD_DIR] [--preview]
#
# Stages (each in its own `guix shell --pure` role, exchanging files only):
#   1. inspect   base     validate manifests, report parts/occurrences/hashes
#   2. cad       freecad  STEP -> per-part GLB + meshes.json (geometry checks)
#   3. render    blender  thumbnails, overview, step images + render-receipt.json
#   4. manual    publish  manual.json, index.html, manual.typ, PDF
#   5. check     publish  HTML/PDF/manual.json agreement, links, images, page rasters
# Exit status is non-zero at the first failing stage. Outputs go under BUILD_DIR
# (ignored by Git). Nothing here claims the procedure is physically validated.
set -eu
here=$(cd "$(dirname "$0")/.." && pwd)
project=${1:-"$here/examples/three-part-fixture"}
build=${2:-"$here/build/$(basename "$project")"}
preview=""
for a in "$@"; do [ "$a" = "--preview" ] && preview="--preview"; done
renders="$build/renders${preview:+-preview}"
manual="$build/manual${preview:+-preview}"
mkdir -p "$build"
cd "$here"
echo "== 1/5 inspect"
guix shell --pure -m manifest.scm -- python3 -B -m mechanical_docs inspect "$project" --json "$build/inspect.json"
echo "== 2/5 cad (FreeCAD)"
guix shell --pure -m .guix/manifest-cad.scm -- FreeCADCmd mechanical_docs/cad_mesh.py --pass "$project" "$build/meshes" 2>&1 | grep -E '^\[cad_mesh\]|Error|Traceback' || true
test -f "$build/meshes/meshes.json"
echo "== 3/5 render (Blender)"
guix shell --pure -m .guix/manifest-render.scm -- blender -b --python mechanical_docs/render.py -- "$project" "$build/meshes/meshes.json" "$renders" $preview 2>&1 | grep -E '^\[render\]|Error|Traceback' | grep -v 'strokes set empty' || true
test -f "$renders/render-receipt.json"
echo "== 4/5 manual (HTML, Typst, PDF)"
guix shell --pure -m .guix/manifest-publish.scm -- python3 -B -m mechanical_docs manual "$project" --renders "$renders" --out "$manual" --meshes "$build/meshes/meshes.json"
echo "== 5/5 check"
guix shell --pure -m .guix/manifest-publish.scm -- python3 -B -m mechanical_docs check "$manual"
echo "done: $manual"
