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

One itinerary file gets you:

- **A print-ready PDF** — a colored cover with a day-by-day overview table, one
  page per day (a timeline of typed activity cards, nested stops, a "tonight's
  stay" bar), and transport + accommodation summary pages, all themed from a
  single `cover_color`.
- **Precise validation** — line-numbered, localized diagnostics at three levels
  (errors / warnings / info): missing fields, bad values, and whole-trip
  incoherences (overlaps, nowhere-to-sleep nights, reversed date ranges…).
- **Per-day maps** — optional OpenStreetMap maps with numbered pins, drawn
  driving routes and dotted transport legs, in both the PDF and the browser
  (interactive pan/zoom there), plus a whole-trip map in the viewer.
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
- [JSON format](#json-format)
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
odysseyra-travelBook build examples/france.json --maps --map-country FR -o france.pdf
```

Validation runs first (errors are printed to stderr), then it builds regardless.

| Option | Description |
| ------ | ----------- |
| `-o`, `--output PATH` | Output PDF path (default: `<input>.pdf`) |
| `--ink-saver` | Outlines + thin rules instead of solid accent fills — far less ink when printing |
| `--maps` / `--no-maps` | Force per-day maps on/off, overriding `defaults.include_maps_in_render` |
| `--map-country CODE` | ISO country code(s) to restrict geocoding to, e.g. `FR` |
| `--map-provider google\|apple\|osm\|waze\|mapsme` | Which app the inline **(Navigate)** links open (default `google`) |
| `--cache-dir PATH` | Where to cache map tiles / geocode / route results |
| `-l`, `--lang en\|fr` | Language of the generated PDF (default `en`) |

The PDF has a colored cover (title, inferred date range, day count, summary and a
day-by-day overview table), one page per day (a colored header band carrying the
city, date and the day's sunrise/sunset, the day's
intro, the merged time-ordered timeline of typed activity cards — including any
car pick-up/drop-off — and a bottom "tonight's stay" bar), then a transport page
and an accommodation summary. The whole palette is derived from `cover_color`.
With maps on, each day page also carries an OpenStreetMap with numbered pins,
drawn driving routes and a dotted straight line per transport leg.
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
  nowhere to sleep, an activity ending after `defaults.end_time`, or a hike whose
  `route` and `start`/`end` disagree. (…and more.)
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
- **transport leg** — timezone-aware, so a flight that departs in one zone and
  arrives in another keeps *both* wall-clock times;
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
  transports/*.json           # → "transport"       (one leg per file)
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
Start it with `make dev` or `make preview` (see [Setup](#setup)).

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
  cluster and a note under the map names what it left out — the pins and routes
  are still there, one zoom out away. Two genuinely distant clusters both stay
  in view.
- **🔎 Findings** — every validation ❌ / ⚠️ / ℹ️ finding with its line number and a
  level filter (the same engine as `odysseyra-travelBook validate`).
- **✏️ Edit** — a structured form editor over the input JSON. Every field is
  editable, with add / remove / reorder for days, activities (one level of
  nesting), transport, accommodations, car rentals and waypoints. It **validates
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

### Global structure

The top-level object has two config groups and three content arrays:

- **`travel_description`** *(object)* — what the trip is: cover title, summary,
  accent color, and an optional date range (inferred from the earliest/latest
  date across days, transport and accommodation when not set).
- **`defaults`** *(object)* — fallback settings applied across the trip: the
  day start time, inter-activity buffer, time zone, end-of-day check.
- **`days`** *(array, required, non-empty)* — the itinerary, one per day.
- **`transport`** *(array, optional)* — travel legs (also woven into the days).
- **`accommodations`** *(array, optional)* — where you sleep.
- **`car_rentals`** *(array, optional)* — rental-car bookings.

```json
{
  "travel_description": {
    "title": "Grand Tour of France",
    "subtitle": "Paris, the Loire, the Dordogne and the Pyrenees",
    "cover_color": "#2f5d8c",
    "summary": "A short paragraph shown on the cover."
  },
  "defaults": {
    "start_time": "08:30",
    "end_time": "21:00",
    "buffer": "15 min",
    "timezone": "+02:00"
  },
  "days": [ /* day objects */ ],
  "transport": [ /* transport objects */ ],
  "accommodations": [ /* accommodation objects */ ],
  "car_rentals": [ /* car rental objects */ ]
}
```

Throughout, dates use `YYYY-MM-DD`, times use `HH:MM`, durations look like
`"1h30"` / `"45 min"` / `"1:30"`, and UTC offsets like `+02:00` / `UTC-3` /
`Z`. The descriptive and config keys may live either in their groups
(`travel_description` / `defaults`) or at the top level, but the old renamed
aliases (`default_start_time` / `default_end_time` / `default_buffer`,
`start_timezone` / `end_timezone`, transport `date`, `transports`, `default`)
are no longer accepted — use the canonical names.

### `travel_description`

`start_date` / `end_date` are optional: if omitted they are **inferred** as the
earliest / latest date across days, transport and accommodation; if set, they
override and validation cross-checks the itinerary against them.

| Field | Required | Description | Type | Format | Default |
| ----- | -------- | ----------- | ---- | ------ | ------- |
| `title` | ✅ | Trip title shown on the cover | string | any text | — |
| `subtitle` |  | Line under the title | string | any text | `""` (hidden) |
| `start_date` |  | Trip start date (overrides inference) | string | `YYYY-MM-DD` | inferred (earliest date) |
| `end_date` |  | Trip end date (overrides inference) | string | `YYYY-MM-DD` | inferred (latest date) |
| `cover_color` |  | Accent color driving the whole palette | string | hex `#RRGGBB` | `"#1f4e5f"` |
| `summary` |  | Paragraph shown on the cover | string | any text | `""` (hidden) |

### `defaults`

| Field | Required | Description | Type | Format | Default |
| ----- | -------- | ----------- | ---- | ------ | ------- |
| `start_time` |  | First activity's start time each day | string | `HH:MM` | `"08:00"` |
| `end_time` |  | Latest an activity should end (validation warns past it) | string | `HH:MM` | none (no check) |
| `buffer` |  | Buffer auto-inserted between consecutive activities | string | duration | `0` (no buffer) |
| `timezone` |  | Default UTC offset for all times | string | offset (`+02:00`, `UTC-3`, `Z`) | `GMT` (UTC+0) |
| `breakfast_until` |  | A meal starting before this is inferred as breakfast | string | `HH:MM` | `"10:00"` |
| `lunch_until` |  | A meal starting up to this (after breakfast) is lunch; later, dinner | string | `HH:MM` | `"16:00"` |
| `meal_duration` |  | Default length of a meal with no duration/end time | string | duration | `0` (instant) |
| `accommodation_start_time` |  | Evening clock time each accommodation night starts on the calendar (`ics` export) | string | `HH:MM` | `"22:00"` |
| `accommodation_end_time` |  | Clock time each accommodation night ends on the calendar (`ics` export) | string | `HH:MM` | `"00:00"` (midnight) |
| `currency` |  | Currency every price is in unless a price sets its own | string | 3-letter ISO code | `"EUR"` |
| `secondary_currencies` |  | Extra currencies each price is also shown in on the PDF | array | `{currency, change_rate}` objects | `[]` (none) |
| `include_maps_in_render` |  | Draw a per-day OpenStreetMap with a pin for each located activity | boolean | `true`/`false` | `false` (no maps) |
| `infer_coordinates_from_address` |  | Geocode activities that lack an explicit `coordinate` (else only ones with a coordinate are mapped) | boolean | `true`/`false` | `false` |
| `inference_countries` |  | Restrict geocoding to these countries when inferring coordinates | array | 2-letter ISO codes, e.g. `["FR"]` | `[]` (any) |
| `show_moon_phase` |  | Show the night's moon phase (emoji + name) in each day's "tonight" section | boolean | `true`/`false` | `true` (shown) |
| `show_sun_times` |  | Show each day's sunrise/sunset (`☀ 06:12 → 21:34`) in its header, computed at that night's accommodation | boolean | `true`/`false` | `true` (shown) |

Each `secondary_currencies` entry is `{"currency": "<ISO code>", "change_rate":
<number>}`, where `change_rate` is **units of that currency per one unit of the
default currency** (with a `EUR` default, a `USD` rate of `1.09` means
1 € = $1.09). On the PDF every price prints in the default currency followed by
each secondary conversion in parentheses, e.g. `€612 ($667, £520)` — converted
amounts show two decimals below 25 and are rounded to whole numbers at or above
25. Major currencies (`EUR`, `USD`, `GBP`, `JPY`) print with their symbol; others
show the ISO code.

#### Maps & coordinates

When `defaults.include_maps_in_render` is `true`, each day page gets a small
OpenStreetMap with a numbered pin for every located activity and the day's drives
drawn as routes. The night's accommodation, if it has a coordinate, is pinned with
a `*`. A place (an `area`) is shown as a single pin, and — when it has two or more
located sub-activities — a second map zoomed to those points is drawn right after
it, with those pins lettered **A, B, C…** plus that night's `*`. The zoom map's
framing comes from the area's own points alone, so adding the `*` never shifts or
widens it — which does mean a hotel that falls outside the rendered frame isn't
visible there. Each pin's label (number, `*`, or area letter) also appears as a
small disc next to that activity's title in the itinerary, so there's no separate
map key.

**Every locatable object may carry a `coordinate`:**

| Field | Required | Description | Type | Format | Default |
| ----- | -------- | ----------- | ---- | ------ | ------- |
| `lat` | ✅ | Latitude | number | −90…90 | — |
| `long` | ✅ | Longitude | number | −180…180 | — |
| `show_on_map` |  | Whether to plot this point | boolean | `true`/`false` | `true` when a coordinate is set |

```json
"coordinate": { "lat": 43.0974, "long": -0.0583 }
```

Segment objects that go from A→B carry endpoint coordinates: `transport`
accepts `start_coordinate` / `end_coordinate`, and `car_rentals` accept
`pickup_coordinate` / `dropoff_coordinate`. Give a transport leg both endpoints
and it's drawn as a **dotted straight line** between them — on the per-day maps
(PDF and viewer alike) and on the viewer's whole-trip 🗺️ **Overview** map. It's
dotted because the real path isn't known, and for a flight isn't a path on the
ground at all. A leg is drawn on every day map it's *in progress* on, so an
**overnight** leg appears on both its departure and its arrival day. Legs never
widen a day map's extent — a transatlantic flight would zoom the day out to the
ocean — so the line simply runs off the edge toward where it goes; only a day
with nothing else locatable is framed on its legs. A `road` instead uses its
own `coordinate` as the departure point and its `waypoints` as the ordered stops
through to the arrival (see below).

With `infer_coordinates_from_address` off (the default) only objects with an
explicit `coordinate` appear on the map, so builds stay deterministic and offline.
Turn it on to geocode the rest from their `name`/`address` at build time
(restricted to `inference_countries` when set).

#### Sunrise & sunset

Every day carries `☀️ Sunrise: 06:12, Sunset: 21:34` (in French,
`☀️ Lever : 06:12, Coucher : 21:34`). The PDF closes the day's header band with
it; the viewer opens the day's body with it, just above the intro. It's on by
default; set `defaults.show_sun_times` to `false` to hide it.

The two ends are located **separately**, because on a day you change town they
happen in different places — the sunset where you'll sleep, the sunrise where you
woke. Each has its own chain, mirroring the other:

| | **Sunrise** (start of day) | **Sunset** (end of day) |
| --- | --- | --- |
| 1 | the stay covering the **previous** night — where you woke | **that** night's accommodation `coordinate` — where you'll watch it go down |
| 2 | the day's own **first** located activity | the day's own **last** located activity |
| 3 | the nearest dated located stay | the nearest dated located stay |

`show_on_map` is ignored throughout: it hides a pin, it doesn't move where you
are. Step 2 covers a night with no stay listed — aboard an overnight leg, or a
day you fly out — and reads a drive's `coordinate` as its departure and its final
`waypoint` as its arrival, so a day's opening and closing positions are both
real. It's why arriving from another continent doesn't print a sunrise from the
far side of it: France day 2 wakes at Roissy, where the flight lands, not in
New York. If the sunrise chain yields nothing usable it settles for the sunset's
reference rather than dropping the line.

Times are read in the day's wall clock — the `start_tz` of its first activity
when one is set explicitly, otherwise `defaults.timezone` — so set `timezone` to
the trip's actual offset (a trip in France left on the `GMT` default reads two
hours early in summer). If the reference point turns out to be more than three
hours of solar time from that clock, **nothing is shown**: a New York morning
printed on Paris time would be honest (`☀ 12:57 → 01:33`) but read as a bug, so
it's left out. Tag that day's activities with their real `start_tz` and the times
come back. That's why day 1 of `examples/france.json` — an afternoon in New York
before the night flight — carries no sun times while every later day does.

Nothing is shown either when the trip has no dates, no coordinate is reachable,
or the sun never crosses the horizon there that day (polar day / night). An
accommodation with only an `address` has no coordinate to compute from; run
[`geocode`](#geocode--bake-in-coordinates) to fill them in and the times appear.

**Navigation links.** Every locatable object gets a clickable **(Navigate)**
link (labelled *(S'y rendre)* in French) right next to its address / location
line — activities, transport, accommodation and car rentals alike. Opening it on
a phone launches the maps / navigation app with the destination pre-filled; in a
browser it opens the chosen provider's web map. The target app is Google Maps by
default, or Apple Maps / OpenStreetMap / Waze / MAPS.ME — pick it with
`--map-provider` (the web viewer has a matching **Navigate links open in** option
that also drives its PDF export). The link points at the object's `coordinate` when
it has one, otherwise it falls back to its `address` / place name, so it appears
even when maps are off and independently of `show_on_map`. A multi-leg `road`
gets one **(Navigate)** per leg in its *VIA* list, each pointing at that leg's
destination (its named waypoint).

### `days[]` — a day

Every day needs a `title` and a non-empty `activities` array.

| Field | Required | Description | Type | Format | Default |
| ----- | -------- | ----------- | ---- | ------ | ------- |
| `title` | ✅ | The day's title | string | any text | — |
| `city` |  | City/region label | string | any text | `""` |
| `date` |  | The day's date (matched to stays & transport) | string | `YYYY-MM-DD` | trip start date + the day's index |
| `description` |  | Intro paragraph for the day | string | any text | `""` |
| `activities` | ✅ | The day's items (at least one) | array | activity objects | — |

### `activities[]` — common fields

Every activity carries a `type`. All types except `buffer` share the scheduling
fields below: provide any two of `start_time` / `end_time` / `duration` and the
third is inferred (`end = start + duration`). Times chain — the first activity
starts at `defaults.start_time`, each next one at the previous item's end.

| Field | Required | Description | Type | Format | Default |
| ----- | -------- | ----------- | ---- | ------ | ------- |
| `type` | ✅ | The activity kind | string | `road` \| `point_of_interest` \| `place` \| `hike` \| `meal` \| `buffer` | — |
| `start_time` |  | Clock time it starts | string | `HH:MM` | previous item's end, else `defaults.start_time` |
| `end_time` |  | Clock time it ends | string | `HH:MM` | `start_time` + `duration` |
| `duration` |  | How long it lasts | string | duration (`1h30`, `45 min`) | inferred from `end_time`, else 0 |
| `start_tz` |  | Start time zone | string | UTC offset | `defaults.timezone` |
| `end_tz` |  | End time zone | string | UTC offset | `defaults.timezone` |

A tz label is only shown in the PDF when it differs from `defaults.timezone`.

**Guidebook pages.** The four types that carry a `description` — `road`,
`point_of_interest`, `place` and `hike` — also accept an optional
`guidebook_pages`: the page(s) of the trip's guidebook covering that activity, as
a single page (`"14"`), a range (`"15-18"`) or a comma-separated list
(`"16, 23, 25-30"`). Validation errors on anything that isn't page numbers, so
keep the `p.` out of the value. Both renderers append it to the **end of the
description text** as a light-accent pill reading `Guidebook p. 15-18` — a soft
accent fill with accent text, not bold and not uppercased, so it trails the prose
as a pointer instead of taking a row of its own. It drops to its own line only
when it wouldn't fit after the last line, or when the activity has pages but no
description. It works the same on a nested activity.

#### `road` — a drive/transfer

| Field | Required | Description | Type | Format | Default |
| ----- | -------- | ----------- | ---- | ------ | ------- |
| `start` | ✅ | Departure address | string | any text | — |
| `coordinate` |  | The departure point (for the map route) | object | `{ "lat": .., "long": .. }` | none |
| `distance_km` |  | Driving distance | number | positive number | none |
| `off_road` |  | Highlight off-road sections | boolean | `true` / `false` | `false` |
| `description` |  | Anything the other fields don't cover | string | any text | `""` |
| `guidebook_pages` |  | Guidebook page(s) covering the drive | string | page numbers (`14`, `15-18`, `16, 23, 25-30`) | `""` |
| `waypoints` | ✅ | Ordered stops the route runs through (last = arrival) | array | non-empty array of `waypoint` objects (see below) | — |
| `activities` |  | Nested meals (a stop along the drive) | array | `meal` objects, each with a `type` (see below) | `[]` |

A road departs from `start` (its `coordinate` is the departure point) and runs
through its `waypoints`, in order — the **last waypoint is the arrival**. There
is no separate `end`. The map draws `coordinate → waypoint 1 → … → last
waypoint`, with a full-opacity accent disc on the departure and every waypoint.

`description` is free prose for what the structured fields can't say — the state
of the road, a scenic stretch, a pass that closes in winter, a toll or a ferry
crossing. Both renderers print it under the drive's meta line and **above** the
`VIA` leg list; leave it out when the legs already tell the story.

| Field | Required | Description | Type | Format | Default |
| ----- | -------- | ----------- | ---- | ------ | ------- |
| `coordinate` | ✅ | The point on the route | object | `{ "lat": .., "long": .. }` | — |
| `location` |  | The waypoint's name | string | any text | `""` |
| `duration` |  | Time for the leg reaching it | string | duration (`1h30`, `45 min`) | none |
| `distance_km` |  | Distance for the leg reaching it | number | positive number | none |
| `off_road` |  | The leg reaching it runs off-road | boolean | `true` / `false` | `false` |

The waypoints are listed under the road in the PDF (in a lower accent), one row
per leg (`previous → this waypoint`) — but the list is omitted for a road with a
single leg (a plain departure→arrival), since the title already shows it. An
**unnamed** waypoint (no `location`) still gets a map disc but has no row of its
own — it merges forward into the next named waypoint, its `duration`/`distance_km`
summed into that leg and its `off_road` OR-ed into it. If the waypoint
`duration`s sum to more than the road's own `duration`, validation warns (the
segment times can't fit the drive).

**Off-road, per drive or per leg.** The road's own `off_road` says the drive as a
whole leaves the tarmac and prints the `OFF-ROAD SECTIONS` chip beside the title.
A waypoint's `off_road` marks **only the leg reaching it**, so a drive that is
paved to the village and rough for the last 5 km needs no road-level flag: that
leg's row in the `VIA` list carries a small `OFF-ROAD` chip after its
duration/distance, in the PDF and the viewer alike. The two are independent —
setting one never sets the other. The one
special case: a **single-leg** drive has no `VIA` list, so a flag on its only leg
is promoted to the road's chip rather than being lost.

#### `point_of_interest` — a specific place

| Field | Required | Description | Type | Format | Default |
| ----- | -------- | ----------- | ---- | ------ | ------- |
| `name` | ✅ | Point-of-interest name | string | any text | — |
| `category` |  | Kind of place, shown as the badge | string | `museum` \| `church` \| `building` \| `viewpoint` \| `ruins` \| `castle` \| `temple` \| `street` \| `natural park` \| `mountain` \| `lake` \| `beach` \| `waterfall` \| `other` | `"other"` |
| `address` |  | Address | string | any text | `""` |
| `description` |  | Description | string | any text | `""` |
| `guidebook_pages` |  | Guidebook page(s) covering it | string | page numbers (`14`, `15-18`, `16, 23, 25-30`) | `""` |
| `website` |  | Link to the venue's website, shown as a clickable link | string | a link like `https://example.com` | `""` |
| `activities` |  | Nested points of interest, hikes and meals | array | `point_of_interest`, `hike` or `meal` objects, each with a `type` (see below) | `[]` |

#### `place` — a place (a town, say) grouping several nested activities

| Field | Required | Description | Type | Format | Default |
| ----- | -------- | ----------- | ---- | ------ | ------- |
| `name` | ✅ | Place name | string | any text | — |
| `description` |  | Description | string | any text | `""` |
| `guidebook_pages` |  | Guidebook page(s) covering the area | string | page numbers (`14`, `15-18`, `16, 23, 25-30`) | `""` |
| `activities` |  | Nested points of interest, hikes and meals | array | `point_of_interest`, `hike` or `meal` objects, each with a `type` (see below) | `[]` |

`road`, `hike`, `place` and `point_of_interest` may each carry an `activities`
array of nested activities. Every entry must be an object with an explicit
`type`, and the allowed types depend on the container: `place` and
`point_of_interest` accept `point_of_interest`, `hike` or `meal`; `road` and
`hike` accept `meal` only. A missing or disallowed `type` is an error. Nesting is
only **one level deep** — a nested activity that carries its own `activities` is
a validation error.

#### `hike`

| Field | Required | Description | Type | Format | Default |
| ----- | -------- | ----------- | ---- | ------ | ------- |
| `name` | ✅ | Hike name | string | any text | — |
| `description` |  | Description | string | any text | `""` |
| `guidebook_pages` |  | Guidebook page(s) covering the hike | string | page numbers (`14`, `15-18`, `16, 23, 25-30`) | `""` |
| `distance_km` |  | Distance | number | positive number | none |
| `elevation_m` |  | Elevation gain | number | positive number | none |
| `start` |  | Trailhead address | string | any text | `""` |
| `end` |  | End address | string | any text | `""` |
| `route` |  | Route shape | string | `loop` \| `back_and_forth` \| `one_way` | `"back_and_forth"` |
| `activities` |  | Nested meals (a stop along the hike) | array | `meal` objects, each with a `type` (see below) | `[]` |

For a `loop` / `back_and_forth` hike, `end` should equal `start` (or be omitted)
— validation warns otherwise; for a `one_way` hike, `end` should differ from
`start` — validation warns if it's missing or the same.

#### `meal` — a stop to eat

A meal is scheduled like any other activity (the shared `start_time` /
`end_time` / `duration` fields above) but rendered compactly, like a slightly
accented buffer row rather than a full card — e.g. **Lunch at Le Magret**. A
named restaurant is also listed in the cover overview's highlights.

`meal_type` is optional. If omitted it is inferred from the start time —
**breakfast** before `defaults.breakfast_until` (10:00), **lunch** up to
`defaults.lunch_until` (16:00), **dinner** after (lunch when there's no start
time at all). Those two thresholds are configurable per trip in the `defaults`
object. `brunch`, `snack`, `picnic` and `meal` are also valid but are **never
inferred** — set them explicitly.

If a meal gives no `duration`/`end_time`, it uses `defaults.meal_duration` (0 —
instant — unless you set one).

The head shows the restaurant when named (**Lunch at Les Deux Palais**); otherwise it
falls back to `area` (**Picnic near Limoges**), or just the meal type. Setting
both `restaurant` and `area` triggers a validation warning — `area` is ignored
when a restaurant is named.

| Field | Required | Description | Type | Format | Default |
| ----- | -------- | ----------- | ---- | ------ | ------- |
| `meal_type` |  | Which meal it is | string | `breakfast` \| `lunch` \| `dinner` \| `brunch` \| `snack` \| `picnic` \| `meal` (last four explicit-only) | inferred from `start_time` |
| `restaurant` |  | Restaurant name | string | any text | `""` |
| `area` |  | Town/region to eat in (used when no `restaurant` is named) | string | any text | `""` |
| `address` |  | Address | string | any text | `""` |

#### `buffer` — free time between activities

A `0 min` buffer only suppresses the trip's default buffer at that spot (no line
drawn). A default buffer and an inferred gap that meet are merged into one.

| Field | Required | Description | Type | Format | Default |
| ----- | -------- | ----------- | ---- | ------ | ------- |
| `duration` | ✅ | Length of the free time | string | duration | — |

### `transport[]`

A travel leg, rendered on a dedicated transport page and woven into its
`start_date` day's itinerary. A leg that spans midnight is treated as that
night's accommodation (stay bar + "sleep" column, `+1` on the arrival time).
`start_time` is required; provide one of `end_time` / `duration` and the other
is inferred, across time zones when they differ.

| Field | Required | Description | Type | Format | Default |
| ----- | -------- | ----------- | ---- | ------ | ------- |
| `type` |  | Transport kind, shown as the badge | string | `plane` \| `train` \| `bus` \| `taxi` \| `ferry` \| `other` | `"other"` |
| `start` | ✅ | Departure address | string | any text | — |
| `end` | ✅ | Arrival address | string | any text | — |
| `start_date` | ✅ | Departure date; slots the leg into that day (alias: `date`) | string | `YYYY-MM-DD` | — |
| `end_date` |  | Arrival date | string | `YYYY-MM-DD` | inferred (+1 day if it crosses midnight) |
| `start_time` | ✅ | Departure time | string | `HH:MM` | — |
| `end_time` |  | Arrival time | string | `HH:MM` | inferred (`start_time + duration`) |
| `start_tz` |  | Departure time zone | string | UTC offset | `defaults.timezone` |
| `end_tz` |  | Arrival time zone | string | UTC offset | `defaults.timezone` |
| `duration` |  | Travel time | string | duration | inferred from the two times |
| `flight_number` |  | Flight number (planes only; shown on the card) | string | any text | `""` |
| `train_number` |  | Train number (trains only; shown on the card) | string | any text | `""` |
| `booking_number` |  | Reservation reference / PNR | string | any text | `""` |
| `booking_source` |  | Where it was booked | string | any text | `""` |
| `website` |  | Link to the carrier's website, shown as a clickable link | string | a link like `https://example.com` | `""` |
| `booking_link` |  | Direct link to this reservation, shown as a clickable link | string | a link like `https://example.com` | `""` |
| `status` |  | Reservation status, shown as a badge | string | `booked` \| `confirmed` | none (no badge) |
| `price` |  | Ticket price (amount only, no symbol) | number | number | none (not shown) |
| `currency` |  | Currency this price is in | string | 3-letter ISO code | `defaults.currency` |
| `paid` |  | Payment state, shown as a badge | string or boolean | `paid` \| `to pay` (or `true` / `false`) | none (no badge) |

### `accommodations[]`

Where you sleep, rendered as a summary page plus a bottom bar on each covered
day. A stay covers nights from `arrival` up to (but not including) `departure`,
so the checkout day shows no bar.

| Field | Required | Description | Type | Format | Default |
| ----- | -------- | ----------- | ---- | ------ | ------- |
| `name` | ✅ | Accommodation name | string | any text | — |
| `arrival` | ✅ | Check-in date | string | `YYYY-MM-DD` | — |
| `departure` | ✅ | Check-out date | string | `YYYY-MM-DD` | — |
| `city` | ✅ | Town shown in the cover overview | string | any text | — |
| `type` |  | Kind of accommodation | string | `hotel` \| `camping` \| `b&b` \| `other` | `"hotel"` |
| `address` |  | Street address | string | any text | `""` |
| `contact` |  | Phone or email | string | any text | `""` |
| `booking_source` |  | Where it was booked | string | any text | `""` |
| `website` |  | Link to the property's website, shown as a clickable link | string | a link like `https://example.com` | `""` |
| `booking_link` |  | Direct link to this reservation, shown as a clickable link | string | a link like `https://example.com` | `""` |
| `status` |  | Reservation status, shown as a badge | string | `booked` \| `confirmed` | none (no badge) |
| `price` |  | Price for the whole stay (amount only, no symbol) | number | number | none (not shown) |
| `currency` |  | Currency this price is in | string | 3-letter ISO code | `defaults.currency` |
| `paid` |  | Payment state, shown as a badge | string or boolean | `paid` \| `to pay` (or `true` / `false`) | none (no badge) |
| `breakfast_included` |  | Show a "Breakfast included" line | boolean | `true` / `false` | `false` |

### `car_rentals[]`

A rental-car booking, rendered under the transport page, with its **pick-up**
and **drop-off** also woven into their days' itineraries (on `pickup_date` /
`dropoff_date`, at their times). The booking runs from a start datetime to an
end datetime; the pick-up and drop-off datetimes must fall inside that window —
validation errors otherwise (and the drop-off must not precede the pick-up). A
pick-up or drop-off that overlaps an activity or transport on the same day is a
validation warning. Each of the four times takes an optional UTC offset that
falls back to `defaults.timezone`; a tz label is only shown when it differs. The
drop-off location defaults to the pick-up location.

| Field | Required | Description | Type | Format | Default |
| ----- | -------- | ----------- | ---- | ------ | ------- |
| `booking_start_date` | ✅ | Booking start date | string | `YYYY-MM-DD` | — |
| `booking_start_time` | ✅ | Booking start time | string | `HH:MM` | — |
| `booking_end_date` | ✅ | Booking end date | string | `YYYY-MM-DD` | — |
| `booking_end_time` | ✅ | Booking end time | string | `HH:MM` | — |
| `pickup_date` | ✅ | Pick-up date (must be within the booking period) | string | `YYYY-MM-DD` | — |
| `pickup_time` | ✅ | Pick-up time | string | `HH:MM` | — |
| `dropoff_date` | ✅ | Drop-off date (must be within the booking period) | string | `YYYY-MM-DD` | — |
| `dropoff_time` | ✅ | Drop-off time | string | `HH:MM` | — |
| `pickup_location` | ✅ | Where you pick up the car | string | any text | — |
| `dropoff_location` |  | Where you drop off the car | string | any text | the pick-up location |
| `booking_start_tz` |  | Booking-start time zone | string | UTC offset | `defaults.timezone` |
| `booking_end_tz` |  | Booking-end time zone | string | UTC offset | `defaults.timezone` |
| `pickup_tz` |  | Pick-up time zone | string | UTC offset | `defaults.timezone` |
| `dropoff_tz` |  | Drop-off time zone | string | UTC offset | `defaults.timezone` |
| `company` |  | Rental company | string | any text | `""` |
| `booking_number` |  | Reservation reference | string | any text | `""` |
| `website` |  | Link to the rental company's website, shown as a clickable link | string | a link like `https://example.com` | `""` |
| `booking_link` |  | Direct link to this reservation, shown as a clickable link | string | a link like `https://example.com` | `""` |
| `status` |  | Reservation status, shown as a badge | string | `booked` \| `confirmed` | none (no badge) |
| `price` |  | Rental price (amount only, no symbol) | number | number | none (not shown) |
| `currency` |  | Currency this price is in | string | 3-letter ISO code | `defaults.currency` |
| `paid` |  | Payment state, shown as a badge | string or boolean | `paid` \| `to pay` (or `true` / `false`) | none (no badge) |
| `car_type` |  | Car category, shown as the badge | string | `regular` \| `small` \| `SUV` \| `4x4` | `"regular"` |
| `car_model` |  | Car make/model | string | any text | `""` |
| `contact` |  | Phone or email for the rental company | string | any text | `""` |
| `additional_drivers` |  | Number of additional drivers | number | whole number ≥ 0 | `0` |
| `pickup_duration` |  | How long the pick-up takes | string | duration | none (not shown) |
| `dropoff_duration` |  | How long the drop-off takes | string | duration | none (not shown) |

## Development

```bash
make test        # or: .venv/bin/pytest
```

The Python package lives under `src/odysseyra_travelbook/`, in focused sub-packages, each
re-exporting its public API from `__init__.py` (so `from odysseyra_travelbook.models import
Itinerary` stays stable):

- `models/` — the data model + JSON parsing (`parsers`, `activities`, `transport`, `accommodation`, `car_rental`, `geo`, `itinerary`)
- `validate/` — the read-only checker (`jsonpos` line-tracking parser, `findings`, `specs`, `validator`)
- `pdf/` — `base` + one mixin per section (cover, days, day maps, transport, accommodation, car rental)
- `maps/` — per-day map rendering (geocode → routing → tiles → image), imported only when maps are on
- `lang/` — localization (`dates`, `translations`)
- `cli.py` — the command-line entry point; `stitch.py` — fragment assembly

The browser viewer is a separate Vite/React app under `web/` (see its README).

### Example files

- `examples/france.json` — the flagship: a full, valid France tour (Paris → the Loire → the Dordogne → the Pyrenees) exercising most features, maps on. Also the in-browser **Demo**.
- `examples/france_fr.json` — the same France tour authored in French (build with `--lang fr`).
- `examples/pyrenees.json` — another full, valid itinerary.
- `examples/pyrenees_pieces/` — that trip split into per-file fragments for `stitch` (a test asserts it reassembles `pyrenees.json` exactly).
- `examples/pyrenees_fr.json` — the Pyrenees trip authored in French (build with `--lang fr`).
- `examples/kyrgyzstan.json` — a maps-on itinerary with explicit coordinates in a region with sparser OSM coverage (a few sights deliberately have no coordinate, so aren't pinned).
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
  trip as GPX tracks/waypoints or KML, for Garmin, Komoot, OsmAnd and other
  offline-GPS apps. The geocoding and OSRM routing pipeline (`maps/`) already
  produces the points and route geometry it would serialize.
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
- **Contacts / emergency info** — an optional section for embassy, insurance,
  host and per-country emergency numbers, rendered as its own page.
- **Hike maps from a GPX track** — let a `hike` carry a GPX track and draw its
  real route on the day map, plus its own zoomed map, instead of the single pin
  it gets today. `maps/render.py` already paints polylines over tiles (the
  translucent route overlay, `dashes()`), so most of the drawing exists; the new
  parts are a JSON field pointing at the track, a small GPX parser and track
  simplification. Note that GPX is today only *source material an LLM reads*
  (`skills/build-full-json.md` takes a hike's figures from it) — nothing in the
  tool itself ingests a track.
- **Elevation profile for hikes** — an elevation chart per `hike`, built from
  the routing geometry, alongside the existing distance/duration figures. A GPX
  track (above) usually carries elevation per point, which would feed this
  directly instead of needing a new elevation service.
- **Whole-trip map in the PDF** — the viewer's 🗺️ Overview tab already draws one
  (every day's points plus the rendered drive routes, in one map); the printed
  book still only carries the per-day maps.
- **More languages** — the i18n scaffold (English source strings → per-language
  tables in `lang/translations.py` and the viewer's `i18n/`) already supports
  this; adding Spanish, German, Italian, etc. is mostly translation tables.
