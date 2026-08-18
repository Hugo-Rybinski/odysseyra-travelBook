# Travelbook Viewer (PWA)

A local-only, installable web app that opens a travelbook itinerary JSON,
**renders the travel book in the browser**, shows every validation finding, and
exports a PDF **on the side** — reusing the Python `travelbook` package in-browser
via [Pyodide](https://pyodide.org). No server, no cloud: your data stays in the
local JSON file.

See [`../docs/pwa-migration-plan.md`](../docs/pwa-migration-plan.md) for the full
plan and [`../README.md`](../README.md) → *Future iterations* for what's still
deferred (notably: in-UI JSON editing, and moving the maps fetch off the main
thread). Per-day maps now render both in the book view and in the exported PDF.

## How it works

```
React + TS  ──►  Pyodide (CPython → WASM)  ──►  travelbook package (the wheel)
   UI            loaded from a pinned CDN,        validate_text / to_dict / build_pdf
                 cached by the service worker     via src/pyodide/bridge.py
```

- The `travelbook` wheel (fonts bundled) plus its pure-Python deps (`fpdf2`,
  `defusedxml`) are built locally into `public/py/` and precached by the service
  worker — nothing is pulled from PyPI at run time.
- Pyodide's runtime + `Pillow` + `fonttools` come from a version-pinned jsDelivr
  CDN, cached by the service worker, so the app works offline after the first run.
- **Maps** run in-browser too: the `travelbook.maps` package fetches tiles
  (Carto), routes (OSRM) and geocoding (Nominatim) through an overridable seam
  (`travelbook.maps.http_get`) that the app points at a synchronous `fetch`. All
  three endpoints send `Access-Control-Allow-Origin: *`, so there's no proxy and
  data stays on-device; the service worker caches the responses for offline use.

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

## Distributing & installing on a phone

The app is a PWA: once loaded it can be **installed to a phone's home screen** and
then **runs fully offline** (Pyodide, the Python wheels and the app shell are all
cached by the service worker; your itinerary stays in the local `.json` you open).

**One hard requirement: a secure origin.** Install + offline (the service worker)
only work over **HTTPS** — a plain `http://<LAN-ip>` URL will *not* register the
service worker. The dev server also doesn't ship one; you must serve the
**production build** (`npm run build`) over HTTPS. Pick one of the routes below.

The flow is the same either way:

1. Serve the built `dist/` over HTTPS (see routes).
2. On the phone, open the HTTPS URL **while online** and let it finish booting
   (past "installing travelbook" to the "Open an itinerary" screen) — this caches
   everything. First load pulls the Pyodide runtime + packages from a CDN (a few
   MB, one time).
3. Install it: **iOS Safari** → Share → *Add to Home Screen*; **Android Chrome**
   → ⋮ menu → *Install app*.
4. Test offline: enable Airplane Mode, relaunch the installed app, open a `.json`
   — it should render and export PDFs with no network.

### Route A — Tailscale (quick, private; no deploy)

Serve locally and expose it over HTTPS on your tailnet. Good for putting it on
*your* phone without publishing anything. Requires the Tailscale app on both
machines and **HTTPS certificates enabled** for the tailnet (admin console →
DNS → *Enable HTTPS*).

```bash
npm run build
npm run preview -- --port 4173        # serve dist/ on :4173 (keep running)
tailscale serve --bg 4173             # → https://<machine>.<tailnet>.ts.net
```

Open that `https://…ts.net/` URL on the phone (also on the tailnet) and install.
The URL is reachable only while your machine keeps `preview` + `tailscale serve`
running and the phone is on the tailnet — but once installed and cached, offline
use needs neither. Stop sharing with `tailscale serve reset`.

> `vite preview` rejects unknown hosts; `vite.config.ts` already allows
> `.ts.net` via `preview.allowedHosts`.

### Route B — static host (permanent, public URL)

`dist/` is a fully static bundle — deploy it to any HTTPS static host for a
durable link installable from any device:

- **GitHub Pages / Netlify / Vercel / Cloudflare Pages** — point the build at
  `web/` (`npm ci && npm run wheel && npm run build`, publish `web/dist`). Set the
  Vite `base` if it isn't served from the domain root.
- Anything that serves the folder over HTTPS works; there's no backend.

Everything is client-side, so the only "distribution" is hosting the static
files — recipients just open the URL and install.

### Offline internals

`npm run wheel` vendors the Python wheels the app needs into `public/py/` —
`travelbook` plus `fpdf2` and `defusedxml` (Pillow and fonttools ship with
Pyodide) — and the service worker precaches them. Installs run with dependency
resolution off, so **nothing contacts PyPI at run time** and the boot completes
offline. The Pyodide runtime + Pillow/fonttools are fetched from the CDN on first
load and cached (CacheFirst) for later offline launches.

Map tiles (Carto), routes (OSRM) and geocoding (Nominatim) are fetched live the
first time a map is built and cached CacheFirst by the service worker (see the
`map-tiles` / `map-data` runtime caches in `vite.config.ts`), so a day whose map
has been rendered once online renders offline afterwards. A map that has never
been fetched simply doesn't appear offline — the build degrades gracefully.

On top of that HTTP cache, the *finished* map images are persisted in IndexedDB
(`src/maps/mapCache.ts`, database `travelbook-maps`, 30-day TTL) keyed by a hash
of the itinerary JSON + the day index. So a relaunched (or killed) app rehydrates
the exact rendered PNGs without recompositing them; expired entries are purged at
startup, and the **Redraw maps** button clears just the current file's entries
and re-renders. Editing the JSON changes its hash, so stale images miss naturally.

## Current status — v1 complete

The full v1 flow works in the browser, offline after first load:

- **Open** a local itinerary JSON (File System Access API, or an `<input>`
  fallback; "Reopen last" remembers the file) — or load the bundled **Sample**.
- **Render** the whole travel book: cover + day-by-day overview, one card per day
  with the time-ordered timeline (PDF-style type badges, nested activities, car
  events, tonight's-stay bar), plus transport and accommodation sections. Prices
  show the default currency with faded secondary conversions. When the itinerary
  opts into maps (`include_maps_in_render`), the text renders first and each day's
  Python-rendered overview map (pixel-identical to the PDF) then fills in — a
  per-day loader shows while it builds — with numbered pin discs next to activity
  titles, plus zoomed area maps. Rendered maps are cached in IndexedDB for 30
  days (keyed by a hash of the JSON), so a relaunched app hydrates them instantly
  instead of redrawing; a **Redraw maps** button discards this file's cached
  images and rebuilds them.
- **Findings** panel lists every validation ❌/⚠️/ℹ️ with line numbers and a level
  filter; **EN/FR** toggles messages, dates and labels.
- **Export PDF** runs `build_pdf` in-browser and downloads it (with ink-saver and
  maps toggles; the maps toggle defaults to the file's own `include_maps_in_render`).
- PWA polish: update-available / offline-ready / install toasts and an offline
  banner (`src/pwa/PwaStatus.tsx`). Note the service worker only registers in a
  production build, so use `npm run build && npm run preview` to exercise those.

Next up (post-v1): editing the itinerary in the UI, and moving Pyodide into a
Web Worker so the first map render doesn't block the main thread.

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
    runtime.ts             boot Pyodide, install wheel, typed validate/resolve/renderDayMap/buildPdf
    bridge.py              JSON-in/out glue over the travelbook package (+ maps)
    netbridge.ts           synchronous fetch exposed to Python for the maps seam
  maps/mapCache.ts         IndexedDB cache of rendered day maps (30-day TTL)
  types/resolved.ts        TS mirror of the resolved-model dict (to_dict)
scripts/build-wheel.sh     wheel builder used by `npm run wheel`
vite.config.ts             React + vite-plugin-pwa + static-copy of examples
```
