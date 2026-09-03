<p align="center">
  <img src="img/logo-white-bg.png" alt="Odysseyra" width="180" />
</p>

# Odysseyra TravelBook

**Odysseyra TravelBook** turns a single JSON travel itinerary into a polished,
print-ready PDF — and comes with a browser app to view, validate and edit that
JSON along the way. It's pure Python (built on
[fpdf2](https://py-pdf.github.io/fpdf2/)) with **no system dependencies** (no
Cairo/Pango), plus a local-first PWA that runs the very same engine in the
browser via Pyodide.

> ### ▶ Try it online — <https://hugo-rybinski.github.io/odysseyra-travelBook/>
>
> No install, no sign-up. Hit **⚙️ Options → Sample** for the bundled France
> itinerary, or open a JSON file of your own. The Python engine runs *in your
> browser*, so nothing you open is ever uploaded anywhere — and once loaded it
> works offline and installs as an app.

One itinerary file gets you:

- **A print-ready PDF** — a colored cover with a day-by-day overview table, a
  whole-trip map page (with maps on), one page per day (a timeline of typed
  activity cards, nested stops, a hike's trail map + elevation profile, a
  "tonight's stay" bar), and transport + accommodation summary pages, all themed
  from a single `cover_color`.
- **Precise validation** — line-numbered, localized diagnostics at three levels
  (errors / warnings / info): missing fields, bad values, and whole-trip
  incoherences (overlaps, nowhere-to-sleep nights, reversed date ranges…).
- **Maps** — optional OpenStreetMap maps with numbered pins, drawn driving routes
  and dotted transport legs: one per day plus a whole-trip overview, in both the
  PDF and the browser (interactive pan/zoom there).
- **Hikes with a GPX** — embed a trail's `.gpx` in the hike and both renderers
  draw the **trail map** and its **elevation profile**, with the distance and
  climb measured off the recording.
- **Smart inference** — trip dates, each day's date, activity schedules and
  durations are inferred, so you only write what's interesting.
- **English & French** output, an **ink-saver** print mode, and a **stitch** mode
  that assembles the itinerary from a folder of small JSON fragments.
- **A browser viewer/editor (PWA)** — open a local file, render the book, review
  findings, edit it in a form, and export the PDF — fully offline, nothing ever
  leaves your device.

## Contents

- [Setup](#setup)
- [Command-line tool](#command-line-tool)
- [Browser viewer (the PWA)](#browser-viewer-the-pwa)
- [JSON format](#json-format) → the full field-by-field reference lives in
  [`file_format.md`](file_format.md)
- [Development](#development)
- [Future improvements](#future-improvements)

## Setup

A root `Makefile` installs dependencies on demand and drives both halves of the
project — the command-line tool and the browser viewer. Run `make` on its own to
list every target.

### Command-line tool

```bash
make cli        # create .venv and install the `odysseyra-travelBook` CLI into it
make test       # run the test suite
```

`make cli` builds an isolated virtualenv (`.venv/`) and installs Odysseyra TravelBook, so
the CLI is available as `.venv/bin/odysseyra-travelBook` (or `source .venv/bin/activate`
first). To set it up by hand instead:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

### Browser viewer (PWA)

Nothing to set up if you just want to use it —
<https://hugo-rybinski.github.io/odysseyra-travelBook/> is the current `main`,
rebuilt and deployed on every push. To run it locally:

```bash
make dev        # run the viewer with hot reload (Vite dev server)
make preview    # build it and serve the production PWA (default port 4173)
```

Both install the web dependencies (and rebuild the in-browser Python wheel) on
first run. `make dev` is best while developing; `make preview` serves the real,
installable, offline-capable PWA — use it to exercise the service worker.
Override the bind address with `make preview HOST=0.0.0.0 PORT=4173`, or the
interpreter with `make PYTHON=python3.13 …`. `make clean` / `make distclean`
remove build artifacts / the venv + `node_modules`.

## Command-line tool

`odysseyra-travelBook <command> [options]`, with six commands: `build`, `validate`,
`ics`, `geocode`, `stitch` and `create-skeleton`. Two options recur: `-l` / `--lang`
(`en` default, or `fr`) picks the language of *generated* text and diagnostics
(never your JSON content), and `-v` / `--verbose` sets validation verbosity.
Running `odysseyra-travelBook <file.json>` with no command implies `build`. Without the
installed entry point, use `python -m odysseyra_travelbook.cli <command> …`.

### `build` — render the PDF

```bash
odysseyra-travelBook build examples/france.json -o france.pdf
odysseyra-travelBook examples/france.json                      # implies build; writes <input>.pdf
odysseyra-travelBook build examples/france.json --ink-saver -o france.pdf
odysseyra-travelBook build examples/france.json --maps -o france.pdf
```

Validation runs first (errors are printed to stderr), then it builds regardless.

| Option | Description |
| ------ | ----------- |
| `-o`, `--output PATH` | Output PDF path (default: `<input>.pdf`) |
| `--ink-saver` | Outlines + thin rules instead of solid accent fills — far less ink when printing |
| `--maps` / `--no-maps` | Force per-day maps on/off, overriding `defaults.include_maps_in_render` |
| `--map-provider google\|apple\|osm\|waze\|mapsme` | Which app the inline **(Navigate)** links open (default `google`) |
| `--cache-dir PATH` | Where to cache map tiles / geocode / route results |
| `-l`, `--lang en\|fr` | Language of the generated PDF (default `en`) |

The PDF has a colored cover (title, inferred date range, day count, summary and a
day-by-day overview table), one page per day (a colored header band carrying the
city and date, then the day's sunrise/sunset, its
intro, the merged time-ordered timeline of typed activity cards — including any
car pick-up/drop-off — and a bottom "tonight's stay" bar), then a transport page
and an accommodation summary. The whole palette is derived from `cover_color`.
With maps on, each day page also carries an OpenStreetMap with numbered pins,
drawn driving routes and a dotted straight line per transport leg — and a
full-page **whole-trip map** follows the cover, holding every day's points at
once, each pinned with its **day number** (see [Maps](file_format.md#maps--coordinates)).
`--ink-saver` keeps the layout but swaps the big solid accent
areas (cover banner, header bands, card backgrounds) for accent-colored text,
outlined badges and thin rules — ideal for a home printer.

### `validate` — check the JSON

```bash
odysseyra-travelBook validate examples/france.json             # errors + warnings (default)
odysseyra-travelBook validate examples/france.json -v 3        # also the ℹ️ info notes
odysseyra-travelBook validate examples/france_fr.json --lang fr
```

Prints findings, each with the line it concerns, at three levels selected by
`-v` / `--verbose`: `1` = errors only, `2` = errors + warnings (**default**),
`3` = everything including low-priority info. The command exits non-zero if there
are any errors (warnings alone exit zero).

- ❌ **errors** — a missing required field, an invalid value (bad date, time,
  duration, color, enum…), or incoherent data — e.g. overlapping items on a
  day's timeline, two accommodations booked for the same night, or a car rental
  picked up outside its booking window. (…and more.)
- ⚠️ **warnings** — softer inconsistencies worth a look — e.g. a night with
  nowhere to sleep, an activity ending after `defaults.end_time`, a point of
  interest visited on a day it's closed (or outside its `opening_hours`), or a
  hike whose `route` and `start`/`end` disagree. (…and more.)
- ℹ️ **info** — low-priority notes (hidden unless `-v 3`) — e.g. an optional field
  missing (stating the default that will be used), or a night with both a hotel
  and an overnight transport (the accommodation wins).

The PDF labels and validation messages are localized (`--lang en|fr`); all
translatable strings live in `src/odysseyra_travelbook/lang/` (English is the source, so a
missing translation falls back to English).

### `ics` — export to a calendar

```bash
odysseyra-travelBook ics examples/france.json                  # → examples/france.ics
odysseyra-travelBook ics examples/france.json -o trip.ics
odysseyra-travelBook ics examples/france_fr.json --lang fr
```

Writes an [iCalendar](https://en.wikipedia.org/wiki/ICalendar) (`.ics`) file you
can import into Google Calendar (or Apple/Outlook). One event is emitted per:

- **day activity** — except **buffers** (free time isn't an event);
- **transport leg** — one event per leg, so a booking that moves you twice gets
  two; timezone-aware, so a flight that departs in one zone and arrives in
  another keeps *both* wall-clock times;
- **car-rental** pick-up and drop-off;
- each **night** of an accommodation booking — from that evening at
  `defaults.accommodation_start_time` (default `22:00`) to
  `defaults.accommodation_end_time` (default `00:00`, i.e. midnight).

Every event carries as much of the object's detail as it has (address, booking
reference, price, nested activities…) in its description, localized with
`--lang`. Times are written as local wall time tagged with a self-contained
fixed-offset time zone (from each item's `start_tz`/`end_tz`, falling back to
`defaults.timezone`), so events land at the correct instant *and* display in the
local time of the place. Like `build`, it prints validation errors first but
exports anyway. The browser viewer offers the same export under **Options →
Calendar export**.

### `geocode` — bake in coordinates

```bash
odysseyra-travelBook geocode examples/france.json --country FR
```

Geocodes the objects that lack an explicit `coordinate` (from their name /
address) and writes the results **back into the JSON**, so later builds are
offline and deterministic. `-o` / `--output` writes elsewhere (default: overwrite
in place); `--country` restricts geocoding (default: the trip's
`inference_countries`).

### `stitch` & `create-skeleton` — build from fragments

Rather than one large file, you can keep each piece in its own file and let
`stitch` assemble them. The directory mirrors the itinerary shape:

```
examples/pyrenees_pieces/
  travel_description.json     # → "travel_description"  (optional; prompted if absent)
  defaults.json               # → "defaults"            (optional)
  days/*.json                 # → "days"            (one day per file)
  transports/*.json           # → "transport"       (one booking per file)
  accommodations/*.json       # → "accommodations"  (one stay per file)
  car-rentals/*.json          # → "car_rentals"     (one rental per file)
```

```bash
odysseyra-travelBook create-skeleton . mytrip     # scaffold ./mytrip/ (sub-folders + a title stub)
odysseyra-travelBook stitch mytrip                 # assemble once you've added ≥1 day
odysseyra-travelBook stitch examples/pyrenees_pieces -v 3
```

Each array folder contributes one entry per JSON file, **ordered by file name**
(a numeric prefix like `1-arrival.json` keeps days in order); a file may also
hold a JSON array, each element becoming one entry. Validation runs twice (both
respecting `-v` / `--lang`): each fragment is validated on its own first (so line
numbers point at the file you edit), then the stitched JSON is re-validated for
the cross-file coherence checks no single fragment can see. The result is written
into the directory as `<title>.json`; the command exits non-zero if either pass
found errors.

### As a library

```python
from odysseyra_travelbook import Itinerary, build_pdf

itinerary = Itinerary.from_json_file("examples/france.json")
build_pdf(itinerary, "france.pdf", ink_saver=True)
```

## Browser viewer (the PWA)

The `web/` app renders and edits the same itineraries in the browser, running the
real Odysseyra TravelBook engine locally through Pyodide — **everything stays on your
device**, it works fully offline once loaded, and it's installable as an app.
It's live at **<https://hugo-rybinski.github.io/odysseyra-travelBook/>**; run it
locally with `make dev` or `make preview` (see [Setup](#setup)).

That engine runs in a **Web Worker**, so the long jobs — building the PDF,
drawing a day's map — don't freeze the page: a small loader names whatever is in
flight while the book stays scrollable.

The header's burger menu switches between views:

- **⚙️ Options** — open a local JSON file (or reopen the last, or load the bundled
  sample); toggle the language (**EN / FR**, which localizes the whole UI, dates
  and diagnostics); toggle interactive maps and redraw them; and **export the
  PDF** (with ink-saver / include-maps toggles). Also install the app and check
  for updates.
- **📖 Travel viewer** — the rendered book (cover, day-by-day, transport,
  accommodation), prices with faded secondary-currency conversions. With maps on,
  each day's Python-rendered overview map fills in — numbered pin discs next to
  activity titles, dotted transport legs, plus zoomed area maps — and an
  **Interactive** toggle swaps them for pan/zoom MapLibre maps that keep working
  offline after one online view.
- **🗺️ Overview** — the trip at a glance: its title / date range / summary, the
  day-by-day table (clicking a row jumps into that day in the Travel view), and
  a single **whole-trip map** — every day's located points pinned with their day
  number, the real driving geometry of the days whose map has been rendered, and
  a **dotted straight line per transport leg** (flights, trains, ferries) between
  its `start_coordinate` and `end_coordinate`, dotted because the real path isn't
  known — and for a flight isn't a path on the ground at all.
  It falls back to the coordinates in the file when maps are off, so the map
  works either way; it's always the interactive (MapLibre) map, since there's no
  pre-rendered image of the whole trip to fall back to. A stray far-off cluster
  (an intercontinental departure airport, or the drive to it) doesn't get to
  squash the trip into a corner: the initial view is fitted to the trip's main
  cluster — the pins and routes are still there, one zoom out away. Two
  genuinely distant clusters both stay in view. The PDF's whole-trip map page
  (above) is built from the same logic.
- **🔎 Findings** — every validation ❌ / ⚠️ / ℹ️ finding with its line number and a
  level filter (the same engine as `odysseyra-travelBook validate`).
- **✏️ Edit** — a structured form editor over the input JSON. Every field is
  editable, with add / remove / reorder for days, activities (one level of
  nesting), transport, accommodations, car rentals and a drive's legs. It **validates
  live** as you type, anchoring each finding inline on its field; an **Apply
  changes** button pushes the draft into the viewer, findings and PDF export (the
  preview refreshes only on Apply). **Save** writes back to the opened file,
  **Save as…** / **Download JSON** write a new one; there's **undo / redo /
  revert**, an autosave that survives reloads, coordinate helpers (paste
  "lat, long", or **geocode from address**), and normalize-on-save so a
  round-tripped file stays diff-clean.

See [`web/README.md`](web/README.md) for the viewer's architecture and internals.

## JSON format

Each day needs a `title`, each day needs at least one activity, and `days` must
be non-empty; everything else is optional and falls back to a sensible default.

The format is documented in full — one table per object, each giving
**Required / Type / Format / Default** — in **[`file_format.md`](file_format.md)**:

| Section | What it covers |
| ------- | -------------- |
| [Global structure](file_format.md#global-structure) | The three config groups and three content arrays |
| [`travel_description`](file_format.md#travel_description) | Cover title, summary, accent color, optional manual date range |
| [`defaults`](file_format.md#defaults) | Trip-wide fallbacks — times, timezone, currency, meal thresholds — plus the [auto-sized buffer](file_format.md#auto-sized-buffers--spreading-a-day-out-to-end_time), [maps & coordinates](file_format.md#maps--coordinates) and [sunrise & sunset](file_format.md#sunrise--sunset) switches |
| [`misc`](file_format.md#misc) | Trip-wide reference data with no place on the timeline — the [emergency contacts](file_format.md#miscemergency_contacts) |
| [`days[]`](file_format.md#days--a-day) | One day: title, city, date, intro, bank holiday |
| [`activities[]`](file_format.md#activities--common-fields) | The timeline and its six types — [`road`](file_format.md#road--a-drivetransfer), [`point_of_interest`](file_format.md#point_of_interest--a-specific-place), [`place`](file_format.md#place--a-place-a-town-say-grouping-several-nested-activities), [`hike`](file_format.md#hike) (with a [GPX track](file_format.md#a-hikes-gpx-track)), [`meal`](file_format.md#meal--a-stop-to-eat), [`buffer`](file_format.md#buffer--free-time-between-activities) |
| [`transport[]`](file_format.md#transport) | A booking, and the [`legs[]`](file_format.md#transportlegs) that move you |
| [`accommodations[]`](file_format.md#accommodations) | Where you sleep each night |
| [`car_rentals[]`](file_format.md#car_rentals) | Pick-up / drop-off, car type, extra drivers |

[`validate`](#validate--check-the-json) checks a file against all of it and
reports line-numbered diagnostics; [`skills/build-full-json.md`](skills/build-full-json.md)
is a self-contained guide for having an LLM write one from raw notes.

## Development

```bash
make test        # or: .venv/bin/pytest
```

The Python package lives under `src/odysseyra_travelbook/`, in focused sub-packages, each
re-exporting its public API from `__init__.py` (so `from odysseyra_travelbook.models import
Itinerary` stays stable):

- `models/` — the data model + JSON parsing (`parsers`, `activities`, `transport`, `accommodation`, `car_rental`, `geo`, `itinerary`)
- `validate/` — the read-only checker (`jsonpos` line-tracking parser, `findings`, `specs`, `validator`)
- `pdf/` — `base` + one mixin per section (cover, days, day maps, trip map, transport, accommodation, car rental)
- `maps/` — map rendering, per day and for the whole trip (geocode → routing → vector tiles → `mvt` decode → `basemap` draw → image), imported only when maps are on
- `lang/` — localization (`dates`, `translations`)
- `cli.py` — the command-line entry point; `stitch.py` — fragment assembly

The browser viewer is a separate Vite/React app under `web/` (see its README).

### Example files

- `examples/france.json` — the flagship: a full, valid France tour (Paris → the Loire → the Dordogne → the Pyrenees) exercising most features, maps on. Also the in-browser **Demo**.
- `examples/france_fr.json` — the same France tour authored in French (build with `--lang fr`).
- `examples/pyrenees.json` — another full, valid itinerary, and the designated **opt-out** example: it switches off the defaults that are on (`auto_sized_buffer`, a drive's junction pins), so those code paths stay rendered somewhere.
- `examples/pyrenees_pieces/` — that trip split into per-file fragments for `stitch` (a test asserts it reassembles `pyrenees.json` exactly).
- `examples/broken.json` + `examples/broken_validator_output.txt` — an intentionally broken itinerary and the expected `validate` output (checked by a snapshot test).

Whenever the JSON format or a validator message changes, regenerate the snapshot:

```bash
UPDATE_SNAPSHOTS=1 pytest tests/test_validate.py
```

## Future improvements

Ideas that fit the existing architecture but aren't built yet. None are
committed to — this is a backlog of directions, roughly ordered by how much
they reuse of what's already here.

- **GPX / KML export** — a new CLI sub-command (sibling to `ics`) emitting the
  **whole trip** as GPX tracks/waypoints or KML, for Garmin, Komoot, OsmAnd and
  other offline-GPS apps. The geocoding and OSRM routing pipeline (`maps/`)
  already produces the points and route geometry it would serialize, and
  `models/gpx_export.py` already writes a route out — the whole-trip version is
  the same serializer over more geometry. (Two pieces of this exist in the
  viewer: a hike's own attached GPX comes back out as the file you attached, and
  a drive's leg can have one **built** from the route the map draws. Neither is
  the trip being exported in one file.)
- **PDF cover photo / per-day hero images** — let `travel_description` carry a
  cover image and each day an optional hero image, rendered behind the cover
  banner and day header. Today the layout is typography + maps only.
- **Markdown / plain-text export** — a lightweight, shareable trip summary
  (also handy as LLM round-trip input), rendered from the resolved model like
  the PDF and ICS outputs.
- **Budget / cost totals** — aggregate the per-item `price`/`currency` data the
  model already carries into trip, per-day and per-category (transport vs.
  lodging vs. activities) totals, plus a paid-vs-to-pay balance, surfaced as a
  PDF summary page and in the viewer.
- **A drive nested inside a place** — let a
  [`place`](file_format.md#place--a-place-a-town-say-grouping-several-nested-activities)
  (and a `point_of_interest`) nest a
  [`road`](file_format.md#road--a-drivetransfer), which
  `NESTED_ACTIVITY_TYPES` currently allows nowhere. Itineraries routinely group
  driving *inside* a site — a valley you drive 12 km up, walk in, and drive back
  out of, written as one 3 h block — and today that has to be flattened into
  `road → place → road` siblings (the road's
  `same_start_as_previous_activity` / `same_end_as_next_activity` pair makes
  them share one pin, so it reads well; what's lost is the driving
  sitting *within* the block's own duration). The model side is a one-line table
  entry, but a road is the one activity that isn't a *point*, and every
  nested-activity consumer assumes it is one: `maps/build.py`'s place branch
  turns each nested item into a single `_Pt`, so the drive would be pinned at its
  departure and its route never drawn; `pdf/days.py`'s nested dispatch falls
  through to `_nested_poi`, and there is no nested twin of `_road_title` /
  `_road_waypoints` in either renderer. It also needs an answer to what an
  **area zoom map**'s extent means when one member is a route rather than a
  point — the one genuinely open design question here.
- **Typed / grouped contacts** — the flat
  [`misc.emergency_contacts`](file_format.md#miscemergency_contacts) list is
  built (the book's last page, and the end of the viewer's Overview tab), but
  every entry is an untyped `{name, contact}` pair. Giving a contact a *kind*
  (embassy, insurer, host, local emergency number) would let both renderers
  group the directory and let a per-country block be filled in from the
  countries the trip actually visits.
- **More `misc` reference lists** — the [`misc`](file_format.md#misc) group was
  added precisely so trip-wide data with no place on the timeline has somewhere
  to go, and it holds one list so far. Obvious neighbours: travel documents /
  visa notes, a packing list, a phrasebook. Each is a new key in the group, a
  spec table, a page or Overview block in each renderer — no new top-level
  section.
- **More languages** — the i18n scaffold (English source strings → per-language
  tables in `lang/translations.py` and the viewer's `i18n/`) already supports
  this; adding Spanish, German, Italian, etc. is mostly translation tables.
