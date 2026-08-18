#!/usr/bin/env bash
# Assemble the Python wheels the viewer installs in-browser, into web/public/py:
#   - the travelbook wheel (fonts bundled), built from the repo, and
#   - its pure-Python deps that Pyodide does NOT bundle: fpdf2 + defusedxml.
# (Pillow and fonttools ship with Pyodide, so they're loaded from its CDN.)
# A wheel.json manifest lists them in install order so the runtime can install
# everything from local, precached files — no PyPI at run time, so it works
# fully offline. Re-run after any change to the Python package.
set -euo pipefail

repo_root="$(cd "$(dirname "$0")/../.." && pwd)"
out="$repo_root/web/public/py"
pip="${PIP:-$repo_root/.venv/bin/pip}"

mkdir -p "$out"
rm -f "$out"/*.whl "$out"/wheel.json

# travelbook itself.
"$pip" wheel "$repo_root" --no-deps -w "$out"
# Its non-Pyodide pure-Python deps (universal py3-none-any wheels).
"$pip" download --no-deps --only-binary :all: --dest "$out" fpdf2==2.8.7 defusedxml

cd "$out"
tb="$(ls travelbook-*.whl | head -1)"
deps="$(ls *.whl | grep -v '^travelbook-' | sort)"
# travelbook last (nothing depends on install order once deps resolution is off,
# but keep it tidy).
json="$(printf '"%s",' $deps "$tb")"
printf '{"wheels": [%s]}\n' "${json%,}" > wheel.json

echo "built wheels -> web/public/py/wheel.json:"
cat wheel.json
