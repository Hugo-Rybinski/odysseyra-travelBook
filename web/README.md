# Travelbook Viewer (PWA)

A local-only, installable web app that opens a travelbook itinerary JSON,
**renders the travel book in the browser**, shows every validation finding, and
exports a PDF **on the side** — reusing the Python `travelbook` package in-browser
via [Pyodide](https://pyodide.org). No server, no cloud: your data stays in the
local JSON file.

See [`../docs/pwa-migration-plan.md`](../docs/pwa-migration-plan.md) for the full
plan and [`../README.md`](../README.md) → *Future iterations* for what v1 cuts
(notably: **maps are not embedded in the exported PDF**, and JSON editing is a
later step).

## How it works

```
React + TS  ──►  Pyodide (CPython → WASM)  ──►  travelbook package (the wheel)
   UI            loaded from a pinned CDN,        validate_text / to_dict / build_pdf
                 cached by the service worker     via src/pyodide/bridge.py
```

- The `travelbook` wheel (fonts bundled) is built locally into `public/py/` and
  precached by the service worker.
- Pyodide's runtime + `Pillow` come from a version-pinned jsDelivr CDN; `fpdf2`
  (pure Python) is pulled from PyPI by `micropip` on first load. All three are
  cached by the service worker, so the app works offline after the first run.

## Prerequisites

- **Node 18+** and npm (not required by the Python package; only for this app).
- The Python venv at the repo root (`../.venv`) — used to build the wheel.

## Setup & run

```bash
cd web
npm install
npm run wheel      # builds ../ into public/py/travelbook-*.whl (+ wheel.json)
npm run dev        # Vite dev server
```

Open the printed URL. On first load it downloads the Pyodide runtime and
packages (a one-time, several-MB download shown behind a spinner); afterwards the
service worker serves them offline.

`npm run wheel` re-runs the Python wheel build (via `../.venv/bin/pip wheel`).
Re-run it whenever the Python package changes. Set `PIP=/path/to/pip` to use a
different interpreter.

## Build / preview / typecheck

```bash
npm run build      # tsc + vite build → dist/
npm run preview    # serve the production build (verify PWA install + offline)
npm run typecheck
```

## Current status — Phase 1 (smoke)

`src/App.tsx` boots Pyodide, then validates **and** resolves a bundled sample
(`examples/pyrenees.json`, copied in as `samples/`) and renders the cover title,
day count, date range and the findings list — proving the whole toolchain works
end-to-end in the browser. The real file-open flow + findings panel come in
Phase 2, full book rendering in Phase 3, PDF export in Phase 4.

## Layout

```
public/
  icon.svg                 app / PWA icon
  py/                      built wheel + wheel.json (gitignored; `npm run wheel`)
src/
  main.tsx                 entry; registers the service worker
  App.tsx                  Phase 1 smoke UI
  index.css
  pyodide/
    runtime.ts             boot Pyodide, install wheel, typed validate/resolve/buildPdf
    bridge.py              JSON-in/out glue over the travelbook package
  types/resolved.ts        TS mirror of the resolved-model dict (to_dict)
scripts/build-wheel.sh     wheel builder used by `npm run wheel`
vite.config.ts             React + vite-plugin-pwa + static-copy of examples
```
