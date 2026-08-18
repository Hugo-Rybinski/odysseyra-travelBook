#!/usr/bin/env bash
# Build the travelbook wheel (fonts bundled) and drop it in web/public/py, plus a
# tiny wheel.json manifest the runtime reads so the versioned filename isn't
# hardcoded. Re-run after any change to the Python package.
set -euo pipefail

repo_root="$(cd "$(dirname "$0")/../.." && pwd)"
out="$repo_root/web/public/py"
pip="${PIP:-$repo_root/.venv/bin/pip}"

mkdir -p "$out"
rm -f "$out"/travelbook-*.whl

"$pip" wheel "$repo_root" --no-deps -w "$out"

wheel="$(cd "$out" && ls -t travelbook-*.whl | head -1)"
printf '{"wheel": "%s"}\n' "$wheel" > "$out/wheel.json"
echo "built $wheel -> web/public/py/wheel.json"
