# PWA migration plan — travel-book viewer

A detailed, phase-by-phase plan for building a **Progressive Web App** that opens
a local travelbook itinerary JSON, **renders the travel book in the UI**, shows
every validation finding, and offers **PDF export as a secondary action** — all
**locally**, with no server and no cloud storage.

> Scope note. V1 is **read-only** and **maps are not embedded in the PDF export**.
> See the *Future iterations* section of the top-level `README.md` for the full
> list of deferred features and why each is cut.

---

## Goals & non-goals

**Goals (v1)**
- Open a single local `.json` itinerary from the user's disk.
- Render the resolved travel book in the browser: cover, per-day pages,
  transport, accommodation — the same content the PDF has.
- Display **all** validation findings (❌ errors / ⚠️ warnings / ℹ️ info) with
  line numbers, filterable, in English or French.
- Export a print-exact PDF on demand (without embedded maps in v1).
- Work fully offline after first load; installable to home screen; usable on
  desktop and mobile.
- Reuse 100% of the existing Python (`travelbook` package) — one source of truth.

**Non-goals (v1)** — see README *Future iterations*: editing the JSON in the UI,
maps embedded in the exported PDF, pixel-for-pixel PDF fidelity in the in-app
view, in-app geocoding, any cloud/shared storage.

---

## Architecture

```
┌──────────────────── PWA (installable, offline) ────────────────────┐
│  UI (React + TS)                                                    │
│   • Open local .json  → File System Access API / <input type=file>  │
│   • Book view: Cover · Day cards · Transport · Accommodation        │
│   • Findings panel: all levels, grouped, line-linked, en/fr         │
│   • [Export PDF] button                                             │
│                                                                     │
│  Pyodide (CPython → WebAssembly), loaded once, SW-cached            │
│   • installs the travelbook wheel (built from this repo)            │
│   • validate_text(json, lang)        → findings                     │
│   • Itinerary.from_dict(...).to_dict() → resolved model (NEW)       │
│   • build_pdf(..., maps=False)       → PDF bytes → Blob → download   │
│                                                                     │
│  Storage: the user's local JSON file only.                          │
│  IndexedDB holds just the last-opened file handle + UI prefs.       │
└─────────────────────────────────────────────────────────────────────┘
  Nothing is sent to any server. No backend exists.
```

**Why Pyodide.** It is the only option that satisfies *local-only + no server +
PWA + mobile* while reusing the Python resolve/validate/build logic verbatim.
`fpdf2` is pure Python (runs as-is in Pyodide); `Pillow` has a Pyodide build.
The only casualty is in-browser networking, which is why PDF-embedded maps are
deferred (the map code reaches the network via `urllib`, and Pyodide has no
sockets).

**The shared contract.** The React layer never re-implements inference. It
consumes a single **resolved-model dict** produced by a new Python `to_dict()`
that emits every inferred field (chained activity times, inferred dates, resolved
meal categories, converted prices, the day-overview rows). This dict is the
contract between Python and the UI, and it is what a future editor will write
back through.

---

## Tech stack

| Concern | Choice | Notes |
|---|---|---|
| Build tool | **Vite** | Fast dev server, first-class PWA plugin |
| UI | **React + TypeScript** | Component-per-section rendering |
| PWA | **`vite-plugin-pwa`** (Workbox) | Manifest + service worker + precache |
| Python runtime | **Pyodide** | Loads the `travelbook` wheel |
| Local file access | **File System Access API** | `<input type=file>` fallback (iOS Safari) |
| Small local state | **IndexedDB** (`idb`) | Last file handle, language, prefs |
| In-app maps (view only) | **Leaflet / MapLibre** | Optional, independent of Python maps |
| Tests | **Vitest** + **Playwright** | Unit + a smoke e2e that loads an example |

---

## Repository layout (additive — nothing existing moves)

```
travelbook/                 # existing Python package, unchanged behavior
  src/travelbook/...
  + models/serialize.py     # NEW: to_dict() resolved-model serializer
web/                        # NEW: the PWA
  index.html
  vite.config.ts            # + vite-plugin-pwa config
  public/
    manifest.webmanifest
    icons/                  # 192, 512, maskable
  src/
    main.tsx
    pyodide/
      runtime.ts            # boot Pyodide, install wheel, typed call wrappers
      bridge.py             # thin glue exposing validate/resolve/build to JS
    render/
      Cover.tsx  DayCard.tsx  TransportList.tsx  AccommodationSummary.tsx
      palette.ts            # cover_color → accent palette (display only)
    findings/
      FindingsPanel.tsx
    file/
      openFile.ts  saveExport.ts
    types/
      resolved.ts           # TS types mirroring the resolved-model dict
docs/
  pwa-migration-plan.md     # this file
```

The Python wheel is built from the existing `pyproject.toml` and copied into
`web/public/` (or fetched at boot) so Pyodide can `micropip.install` it.

---

## Phases

Estimates assume one developer. Each phase ends in something demoable and
testable; phases 0–2 de-risk the two novel pieces (the serializer and Pyodide)
before the larger rendering work in phase 3.

### Phase 0 — Resolved-model serializer (Python) · ~0.5–1 day
The only change to the Python package, and a pure addition.
- Add `to_dict()` to `Itinerary`, `Day`, each activity type, `Transport`,
  `Accommodation`, and the car-rental event — emitting **resolved** values
  (inferred times/dates, resolved meal `category`, `duration_display`, prices
  already converted to default currency with the secondary conversions, and the
  cover's day-overview rows).
- Round-trip test: `Itinerary.from_dict(load("pyrenees.json")).to_dict()` is
  stable and contains the inferred fields (e.g. day 1 activities have concrete
  `start_time`/`end_time`; trip `start_date`/`end_date` are populated).
- **Definition of done:** new unit tests pass; existing suite still green; no
  behavior change to build/validate.

### Phase 1 — PWA shell + Pyodide boot · ~1–2 days
- Scaffold `web/` with Vite + React + TS; wire `vite-plugin-pwa` with a manifest
  (name, icons incl. maskable, `display: standalone`, `theme_color`) and a
  service worker that precaches the app shell **and** the Pyodide runtime +
  `travelbook` wheel, so the app is fully offline after first load.
- `runtime.ts`: load Pyodide, `micropip.install` the local wheel, expose typed
  wrappers `validate(json, lang)`, `resolve(json)`, `buildPdf(json, opts)` that
  call `bridge.py`.
- Smoke test in-browser: `validate` on a bundled example returns findings.
- **Definition of done:** Lighthouse PVA/PWA checks pass; "Add to Home Screen"
  works; app boots offline on second visit; a console smoke call returns data.

### Phase 2 — Open a local file + findings panel · ~1–2 days
Delivers the "all warnings/errors displayed" requirement standalone.
- File open via File System Access API (persist the handle in IndexedDB), with an
  `<input type=file>` fallback for browsers without it (iOS Safari).
- Run `validate` → `FindingsPanel`: findings grouped by ❌/⚠️/ℹ️, each showing its
  line number and message, with a level filter and an en/fr language toggle.
- Handle the empty/no-file and parse-error states.
- **Definition of done:** opening `examples/broken.json` shows exactly the
  findings the CLI reports (spot-checked against `broken_validator_output.txt`);
  language toggle re-renders messages in French.

### Phase 3 — Render the resolved book (core) · ~3–5 days
- `palette.ts`: derive the accent palette from `cover_color` (port the PDF's
  derivation once, for display only).
- Components consuming the resolved-model dict:
  - `Cover` — title, traveler, inferred date range, day count, summary, and the
    day-by-day overview table.
  - `DayCard` — colored header band, intro, the merged time-ordered itinerary
    (typed activity rows with badges + type-specific details, incl. car
    pick-up/drop-off), and the "tonight's stay" bar.
  - `TransportList` — legs plus rental-car bookings.
  - `AccommodationSummary` — the stays summary.
  - Prices shown in the default currency with faded secondary-currency
    conversions.
- Responsive: single-column scroll on mobile; wider multi-column layout on
  desktop.
- **Definition of done:** `examples/pyrenees.json` renders all sections with
  correct inferred times/dates and prices; French example renders in French;
  layout is legible at 375px and at desktop widths.

### Phase 4 — PDF export on the side · ~1 day
- "Export PDF" runs `build_pdf(..., maps=False)` in Pyodide to an in-memory
  buffer → `Blob` → download with a sensible filename (`<title>.pdf`).
- Expose the `--ink-saver` toggle; show a spinner; a build failure surfaces as a
  toast without discarding the rendered view.
- A short note in the UI explains maps aren't embedded in v1 (links to README
  *Future iterations*).
- **Definition of done:** exported PDF opens and matches a CLI build of the same
  file (maps off, ink-saver honored).

### Phase 5 — Polish, offline, CI · ~1–2 days
- Update-available toast (SW `skipWaiting` + reload), install prompt handling,
  offline banner, first-run loading screen for the Pyodide download.
- Accessibility pass (headings, contrast, keyboard nav of the findings panel).
- CI: build the wheel, run Python tests (incl. the new serializer tests), build
  the PWA, run Vitest + a Playwright smoke test that loads `pyrenees.json` and
  asserts the cover + first day render, and a Lighthouse budget check.
- **Definition of done:** green CI; installable, offline-capable build artifact.

**Rough total: ~1.5–2 weeks for v1.**

---

## Key risks & mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| Pyodide + Pillow first-load payload (several MB) | Slow first open | One-time download, SW-cached; loading screen; lazy-load until first action |
| `to_dict()` drifts from the model | UI shows stale/incorrect data | Round-trip tests in Phase 0; the dict is the single contract, exercised by render tests |
| iOS Safari lacks File System Access API | No silent in-place save | v1 is read-only; open-via-picker + export-via-download cover iOS. Matters more when editing lands |
| `urllib`/sockets unavailable in Pyodide | No PDF maps, no geocoding | Explicitly deferred (README *Future iterations*); build with `maps=False` |
| Keeping Python and TS in sync over time | Divergence bugs | Only *rendering* is in TS; all resolve/validate/build stays in Python and is reused verbatim |

---

## Testing strategy

- **Python (Phase 0):** unit tests for `to_dict()` resolved-field coverage and
  stability; existing suite must stay green (no behavior change).
- **TS unit (Vitest):** `palette.ts` derivation; findings grouping/filtering;
  resolved-dict → component prop mapping.
- **E2E (Playwright):** boot the PWA, load `examples/pyrenees.json`, assert the
  cover and first day render and that the findings panel populates; run an
  "export PDF" and assert a non-empty PDF blob.
- **Parity spot-checks:** the in-browser `validate` output matches the CLI for
  `broken.json`; an in-app PDF export matches a CLI build (maps off).

---

## Dependencies on the existing project

- **New:** `models/serialize.py` (`to_dict()`), plus a build step that produces
  the `travelbook` wheel for Pyodide. No existing module changes behavior.
- The PWA consumes the package through three entry points only: `validate_text`,
  the new `to_dict()` resolve path, and `build_pdf`. Keeping the surface this
  small is what makes the Python the single source of truth.

---

## Follow-ups after v1

Tracked in README *Future iterations*: itinerary editing with write-back, maps in
the PDF export (pre-warmed cache or Web-Worker `fetch` shim), in-app geocoding,
and pixel-faithful rendering. The resolved-model contract and findings panel from
v1 are the foundation the editor builds on.
