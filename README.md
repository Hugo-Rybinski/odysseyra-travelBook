# travelbook

Turn a JSON travel itinerary into a polished, print-ready PDF.

Built with [fpdf2](https://py-pdf.github.io/fpdf2/) — pure Python, no system
dependencies (no Cairo/Pango needed).

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

## Usage

```bash
# Build a PDF (the "build" sub-command is optional)
# Build first runs validation and prints any errors (errors only) before building.
travelbook build examples/pyrenees.json -o pyrenees.pdf
travelbook examples/pyrenees.json -o pyrenees.pdf

# Validate the JSON and report problems (with line numbers)
travelbook validate examples/pyrenees.json

# Output in another language (default: en). Both commands take --lang / -l.
travelbook build examples/pyrenees_fr.json --lang fr -o pyrenees_fr.pdf
travelbook validate examples/pyrenees_fr.json --lang fr

# Ink-saving mode: replace the big solid accent fills with outlines and
# thin rules (much less colored ink when printing).
travelbook build examples/pyrenees.json --ink-saver -o pyrenees.pdf

# or without installing the entry point
python -m travelbook.cli validate examples/pyrenees.json
```

### Ink-saving mode

`--ink-saver` (or `build_pdf(..., ink_saver=True)`) keeps the same layout but
drops the large solid accent areas — the cover banner, the per-page header
bands and the card backgrounds — in favor of accent-colored text, outlined
badges/pills and thin rules. Ideal for printing on a home printer.

```python
build_pdf(itinerary, "pyrenees.pdf", ink_saver=True)
```

### Languages

The PDF labels and validation messages are localized. `--lang` (`-l`) selects
the output language — `en` (default) or `fr`. It only affects generated text;
the JSON content (titles, descriptions, addresses…) is written in whatever
language you author it in. All translatable strings live in
`src/travelbook/lang/` (`translations.py` for strings, `dates.py` for
month/weekday names); add a language by adding its map to `TRANSLATIONS` — English
is the source, so any missing translation falls back to English.

```python
# As a library
from travelbook import Itinerary, build_pdf

itinerary = Itinerary.from_json_file("examples/pyrenees.json")
build_pdf(itinerary, "pyrenees.pdf")
```

### Validating

`travelbook validate <file>` checks the JSON and prints findings, each with the
line it concerns. Findings come at three levels, filtered by `--verbose`
(`-v`): `1` = errors only, `2` = errors + warnings (**default**), `3` =
everything including low-priority info.

```bash
travelbook validate examples/pyrenees.json         # errors + warnings
travelbook validate examples/pyrenees.json -v 3     # also the ℹ️ notes
```

- ❌ **errors** — a required field is missing (`title`, a day's `title`), an
  empty `days` array or a day with empty `activities`, a value is invalid (bad
  date, time, duration, timezone, color, enum…), or the data is incoherent:
  - reversed date ranges (trip / transport / accommodation),
  - two accommodations booked for the same night,
  - a night with both a hotel and an overnight transport,
  - overlapping items on a day's timeline (activities and transport),
  - a day whose schedule runs past midnight,
  - duplicate or out-of-order day dates,
  - a `start_time`/`end_time`/`duration` trio that doesn't add up,
  - a non-positive `distance_km` or `duration`.
- ⚠️ **warnings** — a softer inconsistency worth attention:
  - a night with nowhere to sleep (no accommodation, no overnight transport),
  - a date outside a manual trip range, or a manual range that doesn't cover
    the days,
  - a booking marked paid/confirmed but missing its price / reference,
  - an accommodation city that differs from the day's,
  - a hike whose `route` and `start`/`end` disagree (a loop/back-and-forth with
    a different `end`, or a one-way with no distinct `end`),
  - an activity that ends after the trip's `default.end_time`.
- ℹ️ **info** — a low-priority note (hidden unless `-v 3`): an optional field is
  missing (with the default that will be used), or a zero-minute buffer.

Each finding names the field, its description, and the expected value. The
command exits non-zero if there are any errors (warnings alone exit zero).

## JSON format

Each day needs a `title`, each day needs at least one activity, and `days` must
be non-empty; everything else is optional and falls back to a sensible default.

### Global structure

The top-level object has two config groups and three content arrays:

- **`travel_description`** *(object)* — what the trip is: cover title, summary,
  accent color, and an optional date range (inferred from the earliest/latest
  date across days, transport and accommodation when not set).
- **`default`** *(object)* — fallback settings applied across the trip: the
  day start time, inter-activity buffer, time zone, end-of-day check.
- **`days`** *(array, required, non-empty)* — the itinerary, one per day.
- **`transport`** *(array, optional)* — travel legs (also woven into the days).
- **`accommodations`** *(array, optional)* — where you sleep.

```json
{
  "travel_description": {
    "title": "Pyrenees Road Trip",
    "subtitle": "A week in the mountains",
    "cover_color": "#2f6b4f",
    "summary": "A short paragraph shown on the cover."
  },
  "default": {
    "start_time": "09:00",
    "end_time": "19:00",
    "buffer": "15 min",
    "timezone": "+02:00"
  },
  "days": [ /* day objects */ ],
  "transport": [ /* transport objects */ ],
  "accommodations": [ /* accommodation objects */ ]
}
```

Throughout, dates use `YYYY-MM-DD`, times use `HH:MM`, durations look like
`"1h30"` / `"45 min"` / `"1:30"`, and UTC offsets like `+02:00` / `UTC-3` /
`Z`. The older flat layout (all keys at the top level, with `default_start_time`
/ `default_buffer`) is still accepted.

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

### `default`

| Field | Required | Description | Type | Format | Default |
| ----- | -------- | ----------- | ---- | ------ | ------- |
| `start_time` |  | First activity's start time each day | string | `HH:MM` | `"08:00"` |
| `end_time` |  | Latest an activity should end (validation warns past it) | string | `HH:MM` | none (no check) |
| `buffer` |  | Buffer auto-inserted between consecutive activities | string | duration | `0` (no buffer) |
| `timezone` |  | Default UTC offset for all times | string | offset (`+02:00`, `UTC-3`, `Z`) | `GMT` (UTC+0) |

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
starts at `default.start_time`, each next one at the previous item's end.

| Field | Required | Description | Type | Format | Default |
| ----- | -------- | ----------- | ---- | ------ | ------- |
| `type` | ✅ | The activity kind | string | `road` \| `point_of_interest` \| `place` \| `hike` \| `buffer` | — |
| `start_time` |  | Clock time it starts | string | `HH:MM` | previous item's end, else `default.start_time` |
| `end_time` |  | Clock time it ends | string | `HH:MM` | `start_time` + `duration` |
| `duration` |  | How long it lasts | string | duration (`1h30`, `45 min`) | inferred from `end_time`, else 0 |
| `start_tz` |  | Start time zone | string | UTC offset | `default.timezone` |
| `end_tz` |  | End time zone | string | UTC offset | `default.timezone` |

A tz label is only shown in the PDF when it differs from `default.timezone`.

#### `road` — a drive/transfer

| Field | Required | Description | Type | Format | Default |
| ----- | -------- | ----------- | ---- | ------ | ------- |
| `start` | ✅ | Departure address | string | any text | — |
| `end` | ✅ | Arrival address | string | any text | — |
| `distance_km` |  | Driving distance | number | positive number | none |
| `off_road` |  | Highlight off-road sections | boolean | `true` / `false` | `false` |

#### `point_of_interest` — a specific place

| Field | Required | Description | Type | Format | Default |
| ----- | -------- | ----------- | ---- | ------ | ------- |
| `name` | ✅ | Point-of-interest name | string | any text | — |
| `category` |  | Kind of place, shown as the badge | string | `museum` \| `church` \| `building` \| `viewpoint` \| `ruins` \| `castle` \| `temple` \| `street` \| `other` | `"other"` |
| `address` |  | Address | string | any text | `""` |
| `description` |  | Description | string | any text | `""` |

#### `place` — a place (a town, say) grouping several points of interest

| Field | Required | Description | Type | Format | Default |
| ----- | -------- | ----------- | ---- | ------ | ------- |
| `name` | ✅ | Place name | string | any text | — |
| `description` |  | Description | string | any text | `""` |
| `points_of_interest` |  | Points of interest grouped here | array | `point_of_interest` objects (minus `type`) or name strings | `[]` |

#### `hike`

| Field | Required | Description | Type | Format | Default |
| ----- | -------- | ----------- | ---- | ------ | ------- |
| `name` | ✅ | Hike name | string | any text | — |
| `description` |  | Description | string | any text | `""` |
| `distance_km` |  | Distance (validation warns if missing) | number | positive number | none |
| `elevation_m` |  | Elevation gain | number | positive number | none |
| `start` |  | Trailhead address | string | any text | `""` |
| `end` |  | End address | string | any text | `""` |
| `route` |  | Route shape | string | `loop` \| `back_and_forth` \| `one_way` | `"back_and_forth"` |

For a `loop` / `back_and_forth` hike, `end` should equal `start` (or be omitted)
— validation warns otherwise; for a `one_way` hike, `end` should differ from
`start` — validation warns if it's missing or the same.

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
| `type` |  | Transport kind, shown as the badge | string | `plane` \| `train` \| `bus` \| `taxi` \| `other` | `"other"` |
| `start` | ✅ | Departure address | string | any text | — |
| `end` | ✅ | Arrival address | string | any text | — |
| `start_date` | ✅ | Departure date; slots the leg into that day (alias: `date`) | string | `YYYY-MM-DD` | — |
| `end_date` |  | Arrival date | string | `YYYY-MM-DD` | inferred (+1 day if it crosses midnight) |
| `start_time` | ✅ | Departure time | string | `HH:MM` | — |
| `end_time` |  | Arrival time | string | `HH:MM` | inferred (`start_time + duration`) |
| `start_tz` |  | Departure time zone | string | UTC offset | `default.timezone` |
| `end_tz` |  | Arrival time zone | string | UTC offset | `default.timezone` |
| `duration` |  | Travel time | string | duration | inferred from the two times |
| `booking_number` |  | Reservation reference / PNR | string | any text | `""` |
| `booking_source` |  | Where it was booked | string | any text | `""` |
| `status` |  | Reservation status, shown as a badge | string | `booked` \| `confirmed` | none (no badge) |
| `price` |  | Ticket price | string or number | text or number | `""` |
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
| `price` |  | Price | string or number | text or number | `""` |
| `paid_online` |  | Already paid? (badge **Paid online** / **To pay**) | boolean | `true` / `false` | `false` |
| `breakfast_included` |  | Show a "Breakfast included" line | boolean | `true` / `false` | `false` |

## Development

```bash
pytest
```

The code is organized into focused packages under `src/travelbook/`:

- `models/` — `parsers`, `activities`, `transport`, `accommodation`, `itinerary`
- `validate/` — `jsonpos` (line-tracking parser), `findings`, `specs`, `validator`
- `pdf/` — `base` + one mixin per section (`cover`, `days`, `transport`, `accommodation`)
- `lang/` — `dates` (localized names) and `translations` (the string maps)
- `cli.py` — the command-line entry point

Each package's `__init__.py` re-exports its public API, so imports like
`from travelbook.models import Itinerary` are unchanged.

### Example files

- `examples/pyrenees.json` — a full, valid itinerary. Build it with
  `travelbook build examples/pyrenees.json -o pyrenees.pdf` (add `--ink-saver`
  for the low-ink rendering).
- `examples/pyrenees_fr.json` — the same trip authored in French (build it with
  `--lang fr` for a fully French PDF).
- `examples/broken.json` — an intentionally broken itinerary that exercises the
  validator (missing/invalid fields and incoherences).
- `examples/broken_validator_output.txt` — the expected `validate` output for
  `broken.json`, checked by a snapshot test.

Whenever the JSON data format or the validator messages change, regenerate the
snapshot:

```bash
UPDATE_SNAPSHOTS=1 pytest tests/test_validate.py
```

The snapshot test fails if `broken_validator_output.txt` is out of date, so the
saved output always reflects the current format.

## Layout

Each PDF has a colored cover page (title, traveler, dates, summary) with a
**day-by-day overview table** (day number, date, main activities, and the town
you sleep in). Then one section per day: a colored header band, an intro
paragraph, the itinerary (each activity shown as a typed card with a badge and
type-specific details), and a bottom bar for that night's stay. Finally a
transport page and an accommodation summary page. The accent color is derived
from `cover_color`.
