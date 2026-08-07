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

# Per-day maps (see defaults.include_maps_in_render). Override per build with
# --maps / --no-maps; restrict geocoding with --map-country; set the tile cache.
travelbook build examples/pyrenees.json --maps --map-country FR -o pyrenees.pdf

# Geocode missing coordinates once and write them back into the JSON, so later
# builds are offline and deterministic (restrict with --country).
travelbook geocode examples/pyrenees.json --country FR

# Scaffold an empty fragment directory, then stitch it once it's filled in
travelbook create-skeleton . mytrip        # creates ./mytrip/ with sub-folders
travelbook stitch examples/pyrenees_pieces # assemble one JSON, then validate it

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
  - a non-positive `distance_km` or `duration`,
  - a car rental whose pick-up/drop-off falls outside its booking period (or a
    reversed booking window, or a drop-off before the pick-up),
  - a price whose explicit `currency` is neither the default nor a declared
    secondary currency (no rate to convert it), or a malformed
    `secondary_currencies` entry.
- ⚠️ **warnings** — a softer inconsistency worth attention:
  - a night with nowhere to sleep (no accommodation, no overnight transport),
  - a date outside a manual trip range, or a manual range that doesn't cover
    the days,
  - a booking marked paid/confirmed but missing its price / reference,
  - an accommodation city that differs from the day's,
  - a hike whose `route` and `start`/`end` disagree (a loop/back-and-forth with
    a different `end`, or a one-way with no distinct `end`),
  - an activity that ends after the trip's `defaults.end_time`,
  - a car-rental pick-up/drop-off that overlaps an activity or transport on the
    same day.
- ℹ️ **info** — a low-priority note (hidden unless `-v 3`): an optional field is
  missing (with the default that will be used), or a zero-minute buffer.

Each finding names the field, its description, and the expected value. The
command exits non-zero if there are any errors (warnings alone exit zero).

### Stitching a directory of fragments

Rather than maintaining one large JSON file, you can keep each piece in its own
file and let `travelbook stitch <directory>` assemble them. The directory
mirrors the itinerary shape:

```
examples/pyrenees_pieces/
  travel_description.json     # → "travel_description"  (optional; see below)
  defaults.json               # → "defaults"           (optional)
  days/*.json                 # → "days"            (one day per file)
  transports/*.json           # → "transport"       (one leg per file)
  accommodations/*.json       # → "accommodations"  (one stay per file)
  car-rentals/*.json          # → "car_rentals"     (one rental per file)
```

To start one from scratch, `travelbook create-skeleton <path> <name>` scaffolds
`<path>/<name>/` with the four (empty) array sub-folders and a
`travel_description.json` stub whose title is `"FIXME"` — fill in the pieces,
then `stitch` it:

```bash
travelbook create-skeleton . mytrip     # → ./mytrip/{days,transports,…}/ + stub
travelbook stitch mytrip                 # once you've added at least one day
```

Each array folder contributes one entry per JSON file, **ordered by file name**
(so a numeric prefix like `1-arrival.json` keeps days in order); a file may also
hold a JSON array, in which case each element becomes one entry. If
`travel_description.json` is absent you are prompted for its fields (only
`title` is required). The command validates the assembled JSON (respecting
`--verbose` / `--lang`), prints the findings, and writes the result into the
directory as `<title>.json` — e.g. `Pyrenees Road Trip.json`. It exits non-zero
if validation found errors.

```bash
travelbook stitch examples/pyrenees_pieces            # → "Pyrenees Road Trip.json"
travelbook stitch examples/pyrenees_pieces -v 3       # also show the ℹ️ notes
```

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
    "title": "Pyrenees Road Trip",
    "subtitle": "A week in the mountains",
    "cover_color": "#2f6b4f",
    "summary": "A short paragraph shown on the cover."
  },
  "defaults": {
    "start_time": "09:00",
    "end_time": "19:00",
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
| `currency` |  | Currency every price is in unless a price sets its own | string | 3-letter ISO code | `"EUR"` |
| `secondary_currencies` |  | Extra currencies each price is also shown in on the PDF | array | `{currency, change_rate}` objects | `[]` (none) |
| `include_maps_in_render` |  | Draw a per-day OpenStreetMap with a pin for each located activity | boolean | `true`/`false` | `false` (no maps) |
| `infer_coordinates_from_address` |  | Geocode activities that lack an explicit `coordinate` (else only ones with a coordinate are mapped) | boolean | `true`/`false` | `false` |
| `inference_countries` |  | Restrict geocoding to these countries when inferring coordinates | array | 2-letter ISO codes, e.g. `["FR"]` | `[]` (any) |

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
it, with those pins lettered **A, B, C…**. Each pin's label (number, `*`, or area
letter) also appears as a small disc next to that activity's title in the
itinerary, so there's no separate map key.

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
`pickup_coordinate` / `dropoff_coordinate`; the route is drawn between the
endpoints. A `road` instead uses its own `coordinate` as the departure point and
its `waypoints` as the ordered stops through to the arrival (see below).

With `infer_coordinates_from_address` off (the default) only objects with an
explicit `coordinate` appear on the map, so builds stay deterministic and offline.
Turn it on to geocode the rest from their `name`/`address` at build time
(restricted to `inference_countries` when set).

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

#### `road` — a drive/transfer

| Field | Required | Description | Type | Format | Default |
| ----- | -------- | ----------- | ---- | ------ | ------- |
| `start` | ✅ | Departure address | string | any text | — |
| `coordinate` |  | The departure point (for the map route) | object | `{ "lat": .., "long": .. }` | none |
| `distance_km` |  | Driving distance | number | positive number | none |
| `off_road` |  | Highlight off-road sections | boolean | `true` / `false` | `false` |
| `waypoints` | ✅ | Ordered stops the route runs through (last = arrival) | array | non-empty array of `waypoint` objects (see below) | — |
| `activities` |  | Nested meals (a stop along the drive) | array | `meal` objects, each with a `type` (see below) | `[]` |

A road departs from `start` (its `coordinate` is the departure point) and runs
through its `waypoints`, in order — the **last waypoint is the arrival**. There
is no separate `end`. The map draws `coordinate → waypoint 1 → … → last
waypoint`, with a full-opacity accent disc on the departure and every waypoint.

| Field | Required | Description | Type | Format | Default |
| ----- | -------- | ----------- | ---- | ------ | ------- |
| `coordinate` | ✅ | The point on the route | object | `{ "lat": .., "long": .. }` | — |
| `location` |  | The waypoint's name | string | any text | `""` |
| `duration` |  | Time for the leg reaching it | string | duration (`1h30`, `45 min`) | none |
| `distance_km` |  | Distance for the leg reaching it | number | positive number | none |

The waypoints are listed under the road in the PDF (in a lower accent), one row
per leg (`previous → this waypoint`) — but the list is omitted for a road with a
single leg (a plain departure→arrival), since the title already shows it. An
**unnamed** waypoint (no `location`) still gets a map disc but has no row of its
own — it merges forward into the next named waypoint, its `duration`/`distance_km`
summed into that leg. If the waypoint `duration`s sum to more than the road's own
`duration`, validation warns (the segment times can't fit the drive).

#### `point_of_interest` — a specific place

| Field | Required | Description | Type | Format | Default |
| ----- | -------- | ----------- | ---- | ------ | ------- |
| `name` | ✅ | Point-of-interest name | string | any text | — |
| `category` |  | Kind of place, shown as the badge | string | `museum` \| `church` \| `building` \| `viewpoint` \| `ruins` \| `castle` \| `temple` \| `street` \| `natural park` \| `mountain` \| `lake` \| `beach` \| `waterfall` \| `other` | `"other"` |
| `address` |  | Address | string | any text | `""` |
| `description` |  | Description | string | any text | `""` |
| `website` |  | Link to the venue's website, shown as a clickable link | string | a link like `https://example.com` | `""` |
| `activities` |  | Nested points of interest, hikes and meals | array | `point_of_interest`, `hike` or `meal` objects, each with a `type` (see below) | `[]` |

#### `place` — a place (a town, say) grouping several nested activities

| Field | Required | Description | Type | Format | Default |
| ----- | -------- | ----------- | ---- | ------ | ------- |
| `name` | ✅ | Place name | string | any text | — |
| `description` |  | Description | string | any text | `""` |
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
| `distance_km` |  | Distance (validation warns if missing) | number | positive number | none |
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

The head shows the restaurant when named (**Lunch at Le Magret**); otherwise it
falls back to `area` (**Lunch near Lourdes**), or just the meal type. Setting
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
pytest
```

The code is organized into focused packages under `src/travelbook/`:

- `models/` — `parsers`, `activities`, `transport`, `accommodation`, `car_rental`, `itinerary`
- `validate/` — `jsonpos` (line-tracking parser), `findings`, `specs`, `validator`
- `pdf/` — `base` + one mixin per section (`cover`, `days`, `transport`, `accommodation`, `car_rental`)
- `lang/` — `dates` (localized names) and `translations` (the string maps)
- `cli.py` — the command-line entry point

Each package's `__init__.py` re-exports its public API, so imports like
`from travelbook.models import Itinerary` are unchanged.

### Example files

- `examples/pyrenees.json` — a full, valid itinerary. Build it with
  `travelbook build examples/pyrenees.json -o pyrenees.pdf` (add `--ink-saver`
  for the low-ink rendering).
- `examples/pyrenees_pieces/` — the same trip split into per-file fragments,
  for `travelbook stitch`. `stitch`ing it reproduces `pyrenees.json` exactly
  (guarded by a test).
- `examples/pyrenees_fr.json` — the same trip authored in French (build it with
  `--lang fr` for a fully French PDF).
- `examples/kyrgyzstan.json` — a maps-on itinerary with explicit coordinates in a
  region with sparser OSM coverage; a few sights deliberately have no coordinate
  and so aren't pinned. Build with maps: `travelbook build examples/kyrgyzstan.json`.
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
type-specific details, including any car pick-up/drop-off), and a bottom bar for
that night's stay. Finally a transport page (transport legs plus rental-car
bookings) and an accommodation summary page. The accent color is derived from
`cover_color`.
