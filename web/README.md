# Odysseyra TravelBook (PWA)

A local-only, installable web app that opens an Odysseyra TravelBook itinerary JSON,
**renders the travel book in the browser**, shows every validation finding, and
exports a PDF **on the side** — reusing the Python `odysseyra_travelbook` package in-browser
via [Pyodide](https://pyodide.org). No server, no cloud: your data stays in the
local JSON file.

See [`../docs/pwa-migration-plan.md`](../docs/pwa-migration-plan.md) for the full
plan and [`../README.md`](../README.md) → *Future iterations* for what's still
deferred. Per-day maps render both in the book view and in the exported PDF, and
the Python engine runs in a **Web Worker**, so building a PDF or a map no longer
freezes the page.

## How it works

```
React + TS  ──►  Web Worker  ──►  Pyodide (CPython → WASM)  ──►  odysseyra_travelbook (wheel)
   UI           postMessage      loaded from a pinned CDN,       validate_text / to_dict
              (src/pyodide/       cached by the service worker      / build_pdf, via
               runtime.ts ↔                                       src/pyodide/bridge.py
               worker.ts)
```

- **The engine lives in a Web Worker.** Every call into Python is synchronous,
  and rendering a map fetches its tiles over a *blocking* XHR (Pyodide has no
  sockets, and sync Python can't await a JS promise) — on the main thread that
  stopped the browser painting for the whole of a PDF build or a map render, so
  even a spinner sat still. Off-thread the calls take just as long and cost the
  UI nothing: the book stays scrollable while its maps stream in, and the loader
  (`src/ActivityIndicator.tsx`) names what's running. `runtime.ts` is the RPC
  client (unchanged API — `boot()` plus one async function per operation),
  `worker.ts` the host, `engine.ts` the host-agnostic implementation and
  `protocol.ts` the typed message contract. Calls never overlap (Python is
  single-threaded), so a long export simply delays the next validate.
  If a Worker can't be created at all, `runtime.ts` boots the engine on the main
  thread instead — the app works, and freezes during a call as it used to.

- The `odysseyra_travelbook` wheel (fonts bundled) plus its pure-Python deps (`fpdf2`,
  `defusedxml`) are built locally into `public/py/` and precached by the service
  worker — nothing is pulled from PyPI at run time.
- Pyodide's runtime + `Pillow` + `fonttools` come from a version-pinned jsDelivr
  CDN, cached by the service worker, so the app works offline after the first run.
- **Maps** run in-browser too: the `odysseyra_travelbook.maps` package fetches tiles
  (Carto), routes (OSRM) and geocoding (Nominatim) through an overridable seam
  (`odysseyra_travelbook.maps.http_get`) that the app points at a synchronous `fetch`. All
  three endpoints send `Access-Control-Allow-Origin: *`, so there's no proxy and
  data stays on-device; the service worker caches the responses for offline use.

## Prerequisites

- **Node 18+** and npm (not required by the Python package; only for this app).
- The Python venv at the repo root (`../.venv`) — used to build the wheel.

## Setup & run

```bash
cd web
npm install
npm run wheel      # builds ../ into public/py/odysseyra_travelbook-*.whl (+ wheel.json)
npm run dev        # Vite dev server
```

Open the printed URL. On first load it downloads the Pyodide runtime and
packages (a one-time, several-MB download shown behind a spinner); afterwards the
service worker serves them offline.

`npm run wheel` re-runs the Python wheel build (via `../.venv/bin/pip wheel`).
Re-run it whenever the Python package changes. Set `PIP=/path/to/pip` to use a
different interpreter.

> **Stale-wheel guard.** `dev` and `build` run `check-wheel` first (`npm run
> check-wheel`): the browser executes the *wheel*, not `src/odysseyra_travelbook/`, so if
> the source changed after the wheel was built the guard **fails the build** and
> tells you to `npm run wheel`. This prevents silently shipping old Python (which
> once made the maps vanish when a new constant wasn't in the wheel).

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
   (past "installing Odysseyra TravelBook" to the "Open an itinerary" screen) — this caches
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
`odysseyra_travelbook` plus `fpdf2` and `defusedxml` (Pillow and fonttools ship with
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
(`src/maps/mapCache.ts`, database `odysseyra-maps`, 30-day TTL) keyed by a hash
of the itinerary's contents + the day index. So a relaunched (or killed) app
rehydrates the exact rendered PNGs without recompositing them; expired entries
are purged at startup, and the **Redraw all maps** button clears just the current
file's entries and re-renders. Editing a *value* changes the hash, so stale
images miss naturally — but re-indenting the file, or round-tripping it through
the Edit tab without changing anything, does not: `docHash` canonicalizes the
JSON (recursively sorted object keys, no whitespace) before hashing, since the
formatting means nothing to the Python that draws the maps.

An entry is **big** — a day of the France demo is 2–4 MB of base64 PNG, the whole
trip ~20 MB — which drives most of the design:

- **Two stores.** `days` holds the payload; `meta` holds a few dozen bytes per
  entry (the file, the day, the byte count, when it was last used). Listing the
  cache and sweeping it walk `meta` alone — doing either through `days` cloned
  the whole 20 MB store into the main thread to read a timestamp.
- **One set per document, not per edit or per saved version.** The key is the
  content, so every applied edit starts a *fresh* 20 MB set and the old one
  becomes unreachable weight that only the 30-day TTL would have collected — ten
  Apply & redraw cycles left 200 MB nobody could reach.
  `dropStaleVersions(file, keep)` runs before a file's days are refilled and
  drops every other hash for the same document. "Same document" is the
  **`(vNN)`-less base name** (`file/version.ts`'s `parseVersionedName`), not the
  filename: every save route that creates a file numbers it, so the real working
  loop is `trip (v04).json` → `trip (v05).json`, and matching whole filenames
  made each save look like a brand-new document holding its own full set. A
  15-day trip leaked 16 MB per save that way. The marker *is* that document's
  version history — the whole reason it lives in the name — so two names sharing
  a base are two revisions of one trip.
- **A byte budget** (`BUDGET_BYTES`, ~8 trips) evicted least-recently-used, as
  the backstop for many *different* files. `touchDoc` refreshes last-use on
  hydration, so both the TTL and the budget spare a trip you keep reopening.
- **Persistent storage is requested at startup** (`requestPersistence`). Without
  it IndexedDB is best-effort and a browser short of room evicts the **whole
  origin** — the map cache, the last-file handle and the autosaved draft
  together. Granted silently for an installed PWA, refused just as silently
  otherwise.
- **A failed write is reported, not swallowed.** `putCachedDay` returns its
  error, because the way it fails in practice is `QuotaExceededError`, after
  which every day misses for ever and the app looks like it has no cache at all
  rather than a full disk. Options → Maps shows it.

Options → Maps lists the open trip's days with each one's cached size and a
per-day **Redraw**, so a day whose tiles came back thin can be fixed without
paying for the other ten; days from other documents are summed into one line
with a **Clear those**, since they can't be redrawn from here (their file isn't
open) and what matters about them is the room they hold.

A map figure holds its **GL context only while it is near the viewport**
(`DayMapGL`'s observer pair, `MOUNT_MARGIN` / `KEEP_MARGIN`). A browser keeps a
hard, small number of live WebGL contexts per page — Chrome's is 16 — and
**silently kills the oldest** past it, leaving a dead canvas with no error to
catch. MapLibre needs one each, and a book mounts one map per day plus one per
area and one per hike trail: a 15-day trip asks for **34**, so it lost contexts
as soon as it was scrolled and the maps simply stopped drawing. An 8-day trip
sits just under the cap, which is why it only showed on a long one. Mounting on
approach and releasing well clear keeps two or three live whatever the trip's
length; the camera the user panned to is kept in a ref and restored, and a
context lost *anyway* now calls `onFail` instead of leaving a dead canvas —
guarded on a `disposing` flag, since an intentional teardown loses the context
too and would otherwise report every scrolled-past map as broken.

The **interactive** map (`src/maps/carto.ts` + `src/render/DayMapGL.tsx`) uses
Carto's vector Positron style with its tile source pinned to a single host, so
`prefetchTiles` can warm the exact tile URLs MapLibre will request (fit-1…fit+1
over the day's bounds, capped) — that plus the runtime-cached MapLibre chunk lets
a day pan/zoom offline after one online view. If the style/tiles or the chunk
can't load, an error boundary + timeout report it (`mapUnavailable`) — the two
renderings are **alternatives, not a fallback chain**: with the toggle on, a map
slot is the interactive map or nothing, and the static PNG appears only with the
toggle off. Substituting it on a failure would hand back the rendering the user
switched away from — one that can't be panned or zoomed — which reads as the map
having silently lost its controls.

## Current status — v1 complete

The full v1 flow works in the browser, offline after first load. The header's
burger menu switches between views — **⚙️ Options**, **📖 Travel viewer**,
**🗺️ Overview** (the trip's description + day-by-day table + a whole-trip map),
**🔎 Findings** (the validation findings), and **✏️ Edit** (a structured form
editor over the input JSON) — showing one at a time. Every control lives in the
**Options** view (`src/Options.tsx`), grouped by theme — *File* (open / reopen /
sample), *Language*, *Maps* (interactive toggle + redraw), *PDF export* (ink-saver
/ include-maps / export) and *App* (install as an app / check for updates).
Options is shown on first run so a file can be opened, then switches to the viewer
once the book is on screen. Controls (and the Findings tab) are never hidden when
unavailable — they're greyed with a hover tooltip explaining why (no file open,
the itinerary opts out of maps, the browser hasn't offered an install prompt…).

The whole UI is **localized** (English / French) via the *Language* toggle — not
just the rendered travel book (which has always localized through
`render/format.ts`) but the entire chrome: the header, Options, the Edit tab
(field labels, `?` help tooltips, placeholders, enum options) and the findings
panel. It's a gettext-style layer (`src/i18n/`): English is the source string
*and* the lookup key, French is a table (`i18n/fr.ts`), a missing key falls back
to English, and templates keep `{placeholders}` (translate *then* fill) — the
same convention as the Python side. Validator findings themselves are localized
by the Python engine (`validate(text, lang)`).

- **Open** a local itinerary JSON (File System Access API, or an `<input>`
  fallback; "Reopen last" remembers the file) — or load the bundled **Sample**.
  A reload **reopens what you were reading**, so the app comes back to the book
  rather than the empty state. Two routes, in order: the stored file handle when
  its read permission is already granted (which re-reads from disk, so edits made
  outside the app are picked up), otherwise the text stashed under `lastSession`
  in `odysseyra`/`kv`. The handle can't do it alone — most browsers answer
  `queryPermission` with "prompt" after a restart and `requestPermission` needs a
  click, and there is no handle at all for the `<input>` fallback (iOS Safari),
  the Sample or a blank scaffold; so the text rides along, and the auto-reopen
  path only ever *queries* permission, never requests it (a page load carries no
  user activation). One thing outranks it: a restorable **autosaved draft**
  (`edit/autosave.ts`), whose Restore/Discard banner stays the way in — those
  edits are newer than the file they came from, and reopening the file underneath
  would bury the choice.
- **Render** the whole travel book: cover + day-by-day overview, one card per day
  with the time-ordered timeline (PDF-style type badges, nested activities, car
  events, tonight's-stay bar), plus transport and accommodation sections. Prices
  show the default currency with faded secondary conversions. When the itinerary
  opts into maps (`include_maps_in_render`), the text renders first and each day's
  Python-rendered overview map (pixel-identical to the PDF) then fills in — a
  per-day loader shows while it builds — with numbered pin discs next to activity
  titles, a dotted straight line per transport leg (both days of an overnight
  one), plus zoomed area maps. Rendered maps are cached in IndexedDB for 30
  days (keyed by a hash of the JSON's contents), so a relaunched app hydrates
  them instantly instead of redrawing; a **Redraw all maps** button discards this
  file's cached images and rebuilds them, and the listing beside it does the same
  for **one day** (see *Maps* above). An **Interactive** toggle swaps the static images
  (both the day overview and each zoomed area map) for pan/zoom MapLibre maps
  (Carto's keyless vector Positron style, drawn from the same points/routes) with
  zoom/compass, fullscreen, a distance scale and geolocate controls, and
  cooperative gestures (⌘/two-finger to zoom, so the page still scrolls);
  each day's tiles are prefetched over its area so
  it also pans/zooms **offline** after one online view. With the toggle on the
  static images are never shown — a map that can't load says so instead (see
  *Maps* above). A day that set `show_map: false` draws no overview map here
  either (and its activity titles lose their numbered discs, which were that
  map's legend), and a `place` with `show_map: false` draws no zoomed area map —
  the engine simply never emits them, so both renderings agree; `DayCard.tsx`
  checks the day's flag itself only to keep the per-day loader from waiting on a
  map that isn't coming. MapLibre is code-split into its own
  chunk (loaded on demand, only parsed when interactive is used) but precached, so
  it's served with the right MIME and works offline.
  The **attribution starts collapsed** to its ⓘ. MapLibre is already
  `compact: true` by default but opens expanded and only folds away on the first
  drag, which on a map embedded as a figure in a long page is a "MapLibre |
  Carto" strip lying across the corner of every map you scroll past.
  `DayMapGL.tsx` puts it straight into the state a drag would leave it in;
  credit is one tap away, and the static PNG prints it in full.
- **A hike's GPX** (`render/HikeTrack.tsx`) — a `hike` that embeds a `gpx` gets
  its **trail map** and **elevation profile** under it, drawn from the `track` the
  Python model derived (a simplified line + a distance-resampled profile; the
  original file inside it, for the download below). Both come with the resolved
  text, *not* with the per-day map render, so they appear immediately and work
  with `include_maps_in_render` off. The map follows the **Interactive** toggle
  like every other: on, the MapLibre one (drawing straight away, since the
  geometry arrives with the text); off, the static PNG `bridge.py`'s
  `_stamp_hike_maps` puts on `track.map` with the day's other images. A GL
  failure shows the profile alone rather than swapping in the map the user
  switched away from. The hike's own `show_map: false` drops **both** renderings
  of the trail and keeps the profile and the download — the field says *map*.
  The trail carries its own decoration, matching the print's
  (`maps/render.py`'s `Trail`): direction arrowheads along the line, a solid
  marker where it starts and a hollow one where it finishes (one marker only
  when it ends where it began), each point the GPX names with a `<wpt>`, and a
  numbered tick at every whole kilometre — the **same numbers** the elevation
  profile hairlines on its axis, so the steep stretch on the chart can be found
  on the map. Each tick also wears an arrowhead for the direction of travel
  there, and its number sits on the left of that direction, which is what tells
  an out-and-back's two nearly-coincident legs apart. Both come off
  `km_marks[].bearing`, measured by the Python model — never re-derived from the
  drawn line, whose nearest point at a mark can be on the *other* leg. The
  kilometres come from the resolved `track.km_marks` too, chosen once, so the
  two figures can't number themselves differently.
  `DayMapGL.tsx` draws the heads and the ticks as symbol layers over
  canvas-drawn `addImage` bitmaps — an accent-tinted triangle and bar, so no
  sprite and no glyph font is needed — and lets `icon-allow-overlap: false` thin
  the heads per zoom, which is what keeps an out-and-back from growing a row of
  opposed heads along the stretch it walks twice. Ticks are added first with
  `icon-allow-overlap: true` (every kilometre must draw — a scale with a gap is
  a lie) but still claim a collision box, so the heads keep off them. The
  markers and the numbers are DOM `Marker`s, like the numbered pins.
  The profile is inline SVG (it scales with the
  column and reflows on a phone) where the PDF draws vector primitives; the two
  read the same because they read the same samples, so keep `HikeTrack.tsx` in
  step with `pdf/hike_map.py`. `defaults.include_hike_maps` (default **on**)
  switches the pair off, and does it by leaving `track` out of the payload
  entirely — so the geometry never enters the IndexedDB day cache either.
  Beside the hike's other inline links sits **`(Get GPX track)`**, which
  downloads the `.gpx` itself: `track.gpx` decoded (and inflated, where the Edit
  tab gzipped it) so what you load into a watch or another app is the file that
  was attached, not a re-export of the simplified line. It's a `<button>` rather
  than an `<a href>` because the decode is async — there is no URL to point at
  until the click.
- **A URL, an email or a phone number written inside prose is tappable** —
  `render/contact.tsx` holds the two rules that answer for one, and they are
  deliberately different rules for different questions. `contactHref` asks
  whether a **whole field** is a contact (`misc.emergency_contacts[].contact`,
  an activity's `contact`) and is generous, so a bare `112` or `15` links — that
  is exactly the number you want to tap. `linkifyProse` asks whether there is
  one **inside a sentence** and is much stricter, because a loose rule let into
  prose claims `09:30-18:00`, `12 km`, a guidebook range `25-30` or a year span
  `1789-1799`, and a link that goes to the wrong place is worse than one that
  isn't there. Four things make that work:
  - **One seam, `Clamp`.** Every piece of prose the book prints goes through it —
    the cover summary, a day's intro, an activity's description, a booking's
    note, the stay bar's — so linkifying there covers all eleven call sites with
    one rule. It composes with the clamp for free: the truncation is CSS
    (`-webkit-line-clamp`), so the full text is always in the DOM and a link in
    the clipped tail comes back with *Show more*. Nothing had to be reordered.
  - **The strictness is a digit floor plus a separator rule, and a URL must name
    itself.** A leading `+` is its own evidence (nothing else in a trip file
    opens that way), so it needs only 7 digits; without one the floor is a full
    national number at **9**, which clears every date (8 digits), price,
    distance, altitude and page range a description carries. `:` and `,` are
    deliberately *not* separators — they are what a time and a page list are made
    of. A candidate with exactly **one** separator is read as a decimal, since a
    real number is either grouped (`01 42 60 30 30`) or solid (`0142603030`) —
    that is what keeps `1234.56789` from dialling. And a URL needs `https://` or
    a `www.` host, because a bare `example.com` cannot be told from `trip.json`,
    `p.m.` or a missing space after a full stop.
  - **A candidate glued to something larger is dropped**, which is how a URL in a
    note survives whole: `?id=1234567890` is not a phone number.
  - **The PDF does the same thing**, through `prose_links.py` and
    `pdf/base.py`'s `_prose_markup` (fpdf2 markdown links, so the justification
    and line breaking are untouched), and switched off under `--ink-saver` like
    every other hyperlink there. **Keep the rule in step with `contact.tsx`** —
    `tests/test_prose_links.py` is where it is pinned. The two differ only in
    look: `.prose-link` underlines in accent over the prose's own colour, the
    PDF underlines in the prose's colour outright. Neither sets the token in
    accent, because the link is about being tappable and not about mattering
    more.
- **Past days are folded away, not just collapsed** — on Options → *Days* =
  **Collapse past** (the default), `Book.tsx` renders no `DayCard` at all for a
  day dated before today, putting one `.past-days` line at the top of the list
  in their place; the other three views are untouched, since "collapse all" is
  *asking* for the bands. Three things it has to get right: the past set is the
  same rule `collapsedFor`'s `collapse-past` branch uses (keep the two in step —
  one hides what the other collapses); switching the view or loading another
  itinerary re-folds them, like the collapsed preset it sits beside; and `jump`
  reveals the run before scrolling, because the cover's day-by-day table and the
  Overview tab both jump by *day number* and neither knows what is on screen —
  without that, jumping to a past day scrolls to an element that isn't there.
- **A booking's short note** — the optional `description` on a transport leg,
  an accommodation or a car rental appears in **three** places, all as muted
  prose through `Clamp` (so the "show full descriptions" option applies): the
  section card in `TransportList.tsx` / `AccommodationSummary.tsx`
  (`.card-note`), the day's row for a leg or a car pick-up/drop-off in
  `DayCard.tsx` (`.act-note`), and the day's stay bar (`.stay-note`, where the
  clamp stands in for the PDF's two-line cap) — though a sleep-aboard leg, which
  is already a row in that day's itinerary, leaves its note to that row instead
  of repeating it in the bar. A car event carries its rental's
  note on itself — the resolved event has no way back to the rental. This is
  also why `Book.tsx` wraps the transport and accommodation views in
  `ClampProvider`: they had no prose of their own before.
- **Overview** tab (`render/TripMap.tsx` + `render/tripGeo.ts`) reuses the book's
  cover — trip title / dates / summary and the day-by-day table, always expanded,
  with each row jumping into that day in the Travel view (the app carries the day
  over as `Book`'s `jumpTo`, which expands and scrolls to it) — and adds a single
  **whole-trip map**: `tripGeo` merges every day into one `MapGeo`, labeling each
  pin with its **day number** and moving the point's own identity into the popup.
  Per day it prefers the rendered day map's `geo` (its points *and* the real OSRM
  drive geometry) and otherwise falls back to the coordinates the resolved model
  carries, so the map works with maps off — or before the per-day renders stream
  in. **Transport legs** are drawn on top of that as one dotted straight line per
  leg (`DayMapGL`'s optional `legs` prop → a dashed line layer), from the trip's
  own `transports` list so an overnight leg is drawn once rather than on both of
  its days; a leg appears only when its JSON gives both a `start_coordinate` and
  an `end_coordinate` neither of which is hidden (`hide_on_map`; nothing infers
  them, and Python's day
  maps don't map transport at all). It's interactive-only (there's no pre-rendered PNG of the whole trip to
  fall back to), so a tiles/style failure shows a note instead.
  **Outlier clusters are kept out of the initial view** so a "Manhattan → JFK"
  departure day can't squash a France tour into a corner: geometry stops driving
  the bounds once it sits both >6× the median distance from the trip's median
  center *and* >400 km out. The anchors weighed are every pin **plus every drive
  as a single unit** (a drive counts as far off only when it lies *entirely*
  beyond the cut-off) — with maps on, that departure day is a route and no pin at
  all, so a pin-only rule would let it drag the view back across the Atlantic.
  Trimming is capped at a third of the anchors (beyond that it's a real second
  cluster and both stay in view) and off entirely below four. The center/scale
  statistics come from the pins only — route vertices are hundreds per drive and
  would drag the center toward whichever day drove furthest. Trimmed geometry is
  still drawn — one zoom out away, and undisclosed (a note naming what was left
  out read as noise). The PDF's whole-trip map page ports this same trimming, so
  keep `maps/build.py`'s `_trip_extent` in step with `render/tripGeo.ts`.
- **Warnings** tab lists every validation ❌/⚠️/ℹ️ finding with line numbers and a
  level filter; **EN/FR** (in Options) toggles messages, dates and labels.
- **Export PDF** runs `build_pdf` in-browser and downloads it (with ink-saver and
  maps toggles; the maps toggle defaults to the file's own `include_maps_in_render`).
- PWA polish: **automatic updates** — `src/pwa/PwaProvider.tsx` owns the single
  service-worker registration and, when a new deploy is detected, activates it
  and reloads once (no DevTools needed). Connectivity lives in the Options
  header. `PwaProvider` also owns the deferred install prompt
  (`beforeinstallprompt`), which the Options panel's **App** group surfaces as
  **Install as an app** (shown only when the browser offers it).
  - **Check for updates**, from the burger menu's *🔄 Update app* or the Options
    button, reports its answer in the **loader's card** (`ActivityIndicator`) —
    the same floating status the day maps and the PDF export use, rather than a
    banner strip of its own. Three answers, since "couldn't ask" is not "up to
    date": *No update found — this is the latest version.*, *Update found:
    `<hash>` (`<date>`)* (dated the same way as Options' *Current version*
    line — the two are read one click apart), or *Couldn't check for updates —
    no connection.* A found update names the build **before** the reload takes
    the page, so the card stacks *Updating…* over it rather than replacing it.
  - It answers by fetching **`version.json`** — emitted at build time by
    `versionManifest()` in `vite.config.ts` and deliberately kept out of the
    precache (`globIgnores`) and fetched `no-store`. `__COMMIT_HASH__` is baked
    into the bundle, so a running page can only say which build it *is*; this is
    the only way to learn what is *deployed*. Precaching it would make every
    check answer "up to date" forever.
  - Note the SW only registers in a production build, so use
    `npm run build && npm run preview` to exercise these.

The **✏️ Edit** tab is a structured/form editor over the *input* JSON
(`src/edit/`, driven by a field registry in `src/edit/schema.ts` that mirrors the
README schema tables). It is being built in phases — see
[`../docs/edit-tab-plan.md`](../docs/edit-tab-plan.md).

- **P1:** the form surface — every object/field, grouped in collapsible sections,
  with add/remove/reorder for days, activities (incl. one level of nesting),
  transport, accommodations, car rentals, a drive's legs (and their route
  waypoints) and secondary currencies.
- **P2:** live validation. The draft is serialized (with a line→path map) and
  re-validated as you type (debounced); each finding is anchored **inline on its
  field** (the input is flagged, with the message beneath) by translating the
  validator's line number → field path. Findings that don't map to a field —
  cross-object coherence warnings, missing-required, "optional missing" info —
  collect in a filterable rail at the top so nothing is dropped.
- **P3:** an **Apply changes** button pushes the draft into the viewer (`Book`),
  the Findings tab and the PDF export — the preview refreshes only on Apply, never
  on keystroke. The button is disabled until there are unapplied edits (a dot on
  the ✏️ tab marks them). Maps aren't refetched on a plain Apply (the
  previously-rendered ones are carried over); a separate **Apply & redraw maps**
  rebuilds them.
- **P4:** save the draft. **Save** overwrites the opened file in place (File
  System Access handle, prompting for write access); **Save as…** writes a new
  file (which becomes the backing source); **Download JSON** always works (the
  only route where the FS Access API is absent, e.g. iOS Safari). An
  unsaved-changes indicator is tracked separately from unapplied edits (Apply =
  preview, Save = disk).
  The two routes that **create** a file number it — `<slug> (v01).json`,
  `(v02)`, … — so a folder of drafts sorts in the order it was written instead
  of filling with the browser's own `trip (1).json`, whose order says nothing.
  `file/version.ts` parses and formats the marker; `App.tsx`'s `nextFilename`
  takes the **base** from the trip's title (so renaming the trip renames the
  file) and the **version** from the last file opened or written, so the count
  follows the document across a rename rather than restarting. Three things are
  deliberate: the marker lives in the **name and never in the JSON** (a
  `travel_description.version` field would change the bytes on every save, and
  the day cache is keyed by the itinerary's hash — so each save would miss the
  whole cache and redraw every map for content that hadn't moved); **Save in
  place does not advance it**, because its handle points at one existing file
  and the API can't create that file's sibling without a picker; and the count
  continues from the name Save-as hands **back**, not the one it proposed, since
  the picker lets the user rename freely. The next name is shown in both
  buttons' tooltips.
  The **exports carry the marker too** — `<slug> (v05).pdf`, `.ics` — through
  `App.tsx`'s `exportFilename`, and the difference from `nextFilename` is the
  whole point of it being a second derivation: a save *creates* a revision and so
  takes `nextVersion(…)`, while an export *renders* the applied text and so takes
  the version as it stands. So exporting twice overwrites its own previous book
  (right — it is the same revision), and a folder can finally say which JSON
  produced which PDF. An **unversioned** file keeps its plain name rather than
  being given a `(v01)` it never had, which is every file the CLI, the Demo and a
  blank scaffold produce. The CLI needed no counterpart: its `-o` default is
  `Path(input).with_suffix(".pdf")`, which only swaps the extension, so it has
  carried the marker all along — the two halves already agree.
- **P5:** coordinate helpers. Every add/remove/reorder, insert scaffold and enum
  picker already exists from P1; P5 adds **paste "lat, long"** (fills both fields
  at once) and **Geocode from address** on each coordinate — a Nominatim lookup
  (through the maps seam, narrowed to `defaults.inference_countries`) gated on
  the engine being ready and the device online.
- **P6 (current):** safety & recovery. **Undo/redo** (a capped history stack),
  **Revert** to the last saved/loaded baseline, an **IndexedDB autosave** that
  survives a reload / service-worker update and is offered for restore on next
  launch, and **normalize-on-save** (prune empty values + safe defaults so a
  round-tripped file stays diff-clean).

Most fields render from their registry `kind` as a plain control (text, number,
date, time, enum…). A `bool` is a **switch** (`fields/Toggle.tsx`) drawn under
its label like every other control and sized to `--edit-input-h`, the shared
single-line control height — laid out any other way, a bool knocked its whole
grid row out of alignment. The real checkbox is still there, visually hidden
before the track it drives, so focus, the space key and screen readers keep the
platform's behaviour. Two kinds are their own components because the value
isn't a scalar: `coordinate` (`fields/CoordinateField.tsx`, with the paste and
geocode helpers above — its "hide on map" uses the same switch) and a hike's
`gpx` (`fields/GpxField.tsx`) — a **.gpx file picker** that gzips (via
`CompressionStream`, where available) and base64-encodes the file into the draft,
shows what's attached and how big it is encoded, and clears it again. Nobody
types base64.

`defaults` is the one box whose fields don't form a single subject, so the
registry splits it into `DEFAULTS_GROUPS` — *Day timing*, *Meals*, *Accommodation
nights*, *Money* (followed by the secondary currencies, which belong to it),
*Maps*, *Sun & moon* — each drawn as a hairline-ruled section under a small
uppercase title, the same one the nested arrays use. `DEFAULTS_FIELDS` is the
flattened list, which is what the finding index walks, so regrouping the form
can't change which paths it knows about.

Days and their (nested) activities start **collapsed** so a large itinerary is
scannable; a collapsed tile that hides inline findings shows count pills on its
header (`❌ 3`, `⚠️ 2`) for the errors/warnings anchored inside it. Field/button
tooltips float above neighbouring tiles and aren't clipped by a tile's edges.

The Edit tab is feature-complete for now.

## Layout

```
public/
  icon.svg                 app / PWA icon
  py/                      built wheel + wheel.json (gitignored; `npm run wheel`)
src/
  main.tsx                 entry; registers the service worker
  App.tsx                  top-level state + layout (header, book, findings)
  Options.tsx              the themed Options panel (all controls live here)
  edit/                    the ✏️ Edit tab: form editor over the input JSON
  edit/fields/GpxField.tsx a hike's .gpx picker → gzip + base64 into the draft
    schema.ts              field registry (mirrors the README schema tables)
    EditPanel.tsx          stacked collapsible sections (config + content arrays)
    serialize.ts           jsonToDraft / serializeWithPaths / serializeForSave
    findings.ts            finding index (line→path), context, collectFieldPaths
    geocodeContext.ts      geocode-from-address seam for coordinate fields (P5)
    useDraftHistory.ts     undo/redo stack for the draft (P6)
    autosave.ts            IndexedDB autosave/restore of the draft (P6)
    fields/                FieldRow/FieldList/FieldFindings, ArrayEditor, CoordinateField
    forms/                 per-object forms (day, activity, transport, …)
  types/source.ts          TS types for the INPUT JSON (what the Edit tab edits)
  i18n/                    UI-chrome localization (en source / fr table)
    index.tsx              I18nProvider + useT/useTx hooks + translate()
    fr.ts                  English→French table (keyed by the English source)
  index.css
  ActivityIndicator.tsx    the loader: names what the engine is busy with
  pyodide/
    runtime.ts             RPC client: boot() + typed validate/resolve/renderDayMap/
                           buildIcs/buildLegGpx/buildPdf
    worker.ts              module Web Worker hosting the one Python interpreter
    engine.ts              boot Pyodide, install the wheel, dispatch one call
    protocol.ts            the typed UI ↔ worker message contract
    bridge.py              JSON-in/out glue over the odysseyra_travelbook package (+ maps)
    netbridge.ts           synchronous fetch exposed to Python for the maps seam
  pwa/PwaProvider.tsx      single SW registration; auto-applies updates
  maps/mapCache.ts         IndexedDB cache of rendered day maps (30-day TTL)
  render/DayMapGL.tsx      interactive MapLibre day map (lazy-loaded, online)
  render/HikeTrack.tsx     a hike's GPX: trail map (DayMapGL) + SVG profile
  render/tripGeo.ts        merge every day into one whole-trip MapGeo
  render/TripMap.tsx       the Overview tab's whole-trip map (reuses DayMapGL)
scripts/check-wheel.mjs    prebuild guard: fail if the wheel is older than src/
  types/resolved.ts        TS mirror of the resolved-model dict (to_dict)
scripts/build-wheel.sh     wheel builder used by `npm run wheel`
vite.config.ts             React + vite-plugin-pwa + static-copy of examples
```
