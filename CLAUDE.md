# Odysseyra TravelBook

Turn a JSON travel itinerary into a polished, print-ready PDF — and validate the
JSON with precise, localized, line-numbered diagnostics. Pure Python, no system
dependencies (uses `fpdf2` with a bundled DejaVu font; **no** Cairo/Pango).

## Commands

```bash
# setup (or use the Makefile — see below)
python3 -m venv .venv && source .venv/bin/activate && pip install -e ".[dev]"

# build a PDF (the "build" sub-command is optional; validation runs first,
# printing errors-only to stderr, then it builds anyway)
odysseyra-travelBook build examples/pyrenees.json -o out.pdf
odysseyra-travelBook examples/pyrenees.json -o out.pdf            # implies build
odysseyra-travelBook build examples/pyrenees_fr.json --lang fr -o out_fr.pdf
odysseyra-travelBook build examples/pyrenees.json --ink-saver -o out.pdf   # outlines, not solid fills
odysseyra-travelBook build examples/pyrenees.json --maps --map-country FR -o out.pdf   # per-day maps
odysseyra-travelBook geocode examples/pyrenees.json --country FR   # fill coordinates, write back
odysseyra-travelBook ics examples/pyrenees.json -o trip.ics        # export a calendar (.ics) for Google Calendar

# validate (-v 1 errors, 2 +warnings [default], 3 +info; -l/--lang en|fr)
odysseyra-travelBook validate examples/pyrenees.json
odysseyra-travelBook validate examples/pyrenees.json -v 3 --lang fr

# scaffold an empty fragment dir (sub-folders + travel_description.json stub)
odysseyra-travelBook create-skeleton . mytrip

# stitch a directory of JSON fragments into one <title>.json (validates first)
odysseyra-travelBook stitch examples/pyrenees_pieces

pytest                                                  # all tests
UPDATE_SNAPSHOTS=1 pytest tests/test_validate.py        # regenerate the snapshot (see below)
```

Everything runs through the venv (`.venv/bin/...`); there is no `uv`. Python 3.13.

A root `Makefile` wraps all of this and installs deps on demand (venv for the
CLI, npm for the web viewer): `make cli` (install/verify the CLI), `make test`,
`make pdf FILE=… OUT=…`, `make wheel` (rebuild the in-browser wheel), `make dev`
/ `make preview` (run the PWA locally), `make clean`/`distclean`. It's a
convenience layer over the raw commands above — both still work.

## What it produces

A PDF with: a **cover** (title, inferred date range, day count, summary, and a
day-by-day overview table), a **whole-trip map** page (maps on only), one **page
per day** (colored header band with the
city / date / sunrise→sunset, a bank-holiday banner when the day is one, intro,
a merged time-ordered itinerary — including a **trail map + elevation profile**
under any hike that embeds a `gpx` — and a bottom "tonight's stay" bar), a
**transport** page, and an **accommodation** summary page. The whole palette is
derived from one `cover_color`.

## Architecture (`src/odysseyra_travelbook/`)

Four focused packages; each `__init__.py` re-exports its public API, so import
paths are stable (`from odysseyra_travelbook.models import Itinerary`, etc.).

- **`models/`** — the data model, built from JSON via `from_dict` classmethods.
  - `parsers.py` — scalar parsers (`_parse_date/_time/_duration/_tz/_paid/_route/`
    `_price/_currency`, formatters) and `ItineraryError` (raised on any invalid data).
  - `currency.py` — `SecondaryCurrency`, `to_default` (convert to the default
    currency), `format_money`, and the `CURRENCY_SYMBOLS` table.
  - `scheduling.py` — `Scheduled`, the shared base carrying the timeline fields
    (`start_/end_time`, `duration_min`, `start_/end_tz`, `duration_display`)
    inherited by `Activity`, `Transport` and `CarRentalEvent`; plus `Stamp`
    (a `date`+`time`+`tz` triple used for the car rental's four datetimes).
  - `sun.py` — `sun_times(date, lat, long, tz_minutes)` → `SunTimes`
    (`sunrise`/`sunset` + a `display` of `☀ 06:12 → 21:34`), the NOAA sunrise
    equation, pure/offline, `None` on polar day/night. Driven from
    `Itinerary.sun_for(day)` / `sun_reference(date)` / `day_timezone(day)` and
    used by both `pdf/days.py` (the header band) and `serialize.py`.
  - `geo.py` — `Coordinate` (lat/long/`show_on_map`) + `_parse_coordinate`, the
    optional map location attached to activities, transport, accommodation and
    car rentals (segments carry `start_/end_` or `pickup_/dropoff_` coordinates).
  - `gpx.py` — a hike's embedded GPX: `decode_gpx` (base64, optionally gzipped,
    `data:` prefix tolerated) → `parse_gpx` → `GpxTrack`, holding the simplified
    map line (RDP, capped at `MAP_MAX_POINTS`), the distance-resampled
    `profile` (`PROFILE_POINTS` samples), and the measured
    distance/ascent/descent/min/max. Pure stdlib, no network. Ascent is smoothed
    + accumulated with hysteresis so altimeter jitter isn't counted as climb.
  - `opening.py` — a point of interest's `opening_days` / `opening_hours` parsed
    into one `Opening` (`WEEKDAYS`, `parse_opening`, `day_runs`/`hours_display`,
    `closed_on`/`covers`). Pure data: the localized naming lives in `lang/dates.py`.
  - `activities.py` — `Activity` base + the 6 activity types (`road`,
    `point_of_interest`, `place`, `hike`, `meal`, `buffer`), `activity_from_dict`,
    `schedule_activities` (the day timeline pass) and `resolve_meal_categories`
    (fills each `Meal.category` from the trip thresholds after scheduling).
  - `transport.py` — `Transport` + `resolve_transport` (tz-aware time inference).
  - `accommodation.py` — `Accommodation`.
  - `itinerary.py` — `Day` and `Itinerary` (top-level `from_dict`, date inference).
- **`validate/`** — read-only checker, never mutates.
  - `jsonpos.py` — a hand-written position-tracking JSON parser returning
    `(data, lines)` where `lines` maps a path tuple → 1-based line number.
  - `findings.py` — `Finding` (level/line/message), icons, `format_findings`.
  - `specs.py` — `Spec` field descriptors, value validators (`V_*`), spec tables.
  - `validator.py` — `_Validator` walks the data and emits findings; `validate_text`.
- **`pdf/`** — `TravelPDF(CoverMixin, DayMixin, DayMapMixin, TripMapMixin,
  HikeMapMixin, TransportMixin, AccommodationMixin, CarRentalMixin, _PDFBase)`. `base.py` holds fonts/colors and
  shared drawing primitives; each section is a mixin. `build_pdf(itinerary, output,
  lang, ink_saver, maps, cache_dir)` is the entry point. The `ink_saver` flag (CLI
  `--ink-saver`) is stored on `_PDFBase` and read by the primitives that draw large
  solid accent areas — the cover banner, the `_band_header` page bands, `_card_bg`,
  `_notice` (the full-width call-out strip a day's `bank_holiday` opens with),
  `_badge`, `_pill`, `_chip`, `_inline_chip` (the small pill drawn *inside* a text
  row, unlike `_chip` which owns its line — a VIA leg's `OFF-ROAD`) — which then
  render outlines + accent-colored text + thin rules instead of solid fills. `day_map.py`'s `DayMapMixin` embeds the per-day
  map (from `maps/`) after the intro plus a numbered legend, and each area's zoom
  map inline after it; it degrades gracefully (a map failure never breaks the build).
  `trip_map.py`'s `TripMapMixin.trip_map()` adds the **whole-trip map page** right
  after the cover (`build_pdf` calls it unconditionally; it's a no-op with maps
  off, with nothing located, or on a render failure — same graceful degradation).
  `hike_map.py`'s `HikeMapMixin.hike_track(hike, x, w)` is called from
  `days.py`'s `_details_hike` / `_nested_hike` and draws a hike's GPX block: the
  trail map as a **raster** (`maps.render_hike_map`) then the elevation profile as
  **native fpdf vector** (`polygon`/`polyline`) — so the profile needs no tiles,
  stays crisp, and still appears when the map can't be fetched. The profile takes
  the drawn map's box, not the column's, so the two stack as one figure.
- **`maps/`** — map rendering, imported only when maps are on. `geocode.py`
  (Nominatim + `countrycodes` + disk cache), `routing.py` (OSRM driving geometry +
  cache), `render.py` (Carto Positron `@2x` tiles → contrast boost → dotted
  transport legs → translucent theme-colored route → rotated numbered teardrop
  pins → label sandwich; pure Pillow, with `dashes()` splitting a polyline into
  dash pieces, and `_tile_bytes` retrying a transient tile failure — one
  rate-limited tile mid-stitch otherwise silently costs the whole map),
  `build.py` (`resolve_day` → points/routes/area-details,
  `day_legs` → a day's transport legs as straight endpoint pairs,
  `render_day_maps` → PIL images, plus `resolve_trip`/`_trip_extent`/
  `render_trip_map` for the whole-trip map and `render_hike_map(track, …)` for a
  hike's GPX — the one map with nothing to resolve, so it geocodes and routes
  nothing and needs only tiles), `writeback.py` (`fill_coordinates` for the
  `geocode` command),
  and `Cache` (geocode/routes/tiles on disk under `~/.cache/odysseyra`, or
  `$ODYSSEYRA_CACHE`). Uses `Pillow`; everything networked goes through `urllib`.
- **`lang/`** — localization. `dates.py` (month/weekday tables + `fmt_date`,
  plus `weekday_name` and `fmt_weekday_runs` for a POI's opening days),
  `translations.py` (English→French map), `__init__` (`tr`, `LANGUAGES`).
- **`ics.py`** — `build_ics(itinerary, output=None, lang, now=None)` exports a
  resolved itinerary to an iCalendar (`.ics`) string (CLI `ics`, and the viewer's
  **Options → Calendar export**). One `VEVENT` per day activity (buffers excluded),
  transport leg, car pick-up/drop-off and accommodation **night**. Times are emitted
  as local wall time tagged with a self-contained fixed-offset `VTIMEZONE` (from
  each item's `start_tz`/`end_tz`, falling back to `defaults.timezone`), so events
  land at the right instant and show local time; each night runs from that evening
  at `defaults.accommodation_start_time` to `accommodation_end_time` (midnight by default).
  Descriptions are packed with each object's detail, localized via `lang.tr`.
  Pure stdlib (RFC 5545 line-folding + text escaping), no dependencies.
- **`stitch.py`** — `aggregate(directory, ask=input)` assembles one itinerary
  dict from a fragment directory (`travel_description.json`, `defaults.json`, and
  `days/` `transports/` `accommodations/` `car-rentals/` folders — one array
  entry per JSON file, ordered by filename; alternate folder spellings accepted).
  Prompts for `travel_description` when its file is absent. `create_skeleton`
  scaffolds the reverse — an empty fragment dir (`SKELETON_DIRS` sub-folders +
  a `{"title": "FIXME"}` stub). `safe_filename` and `StitchError` round it out.
- `cli.py` — argparse CLI (`build` / `validate` / `ics` / `stitch` / `geocode` /
  `create-skeleton`, `--lang`, `--verbose`). `build` also takes `--maps/--no-maps`,
  `--map-country`, `--cache-dir`; `geocode` fills coordinates and writes them back.

## Key design decisions

- **JSON shape.** Two config groups — `travel_description` (title/summary/color,
  optional manual `start_date`/`end_date`) and `defaults` (`start_time` 08:00,
  `end_time` **18:00**, `auto_sized_buffer` **true** / `buffer` 0 (alternatives,
  not layers), `timezone` GMT, meal thresholds `breakfast_until` 10:00 /
  `lunch_until` 16:00, `meal_duration` 0, `currency` EUR,
  `secondary_currencies`, the accommodation calendar-event times
  `accommodation_start_time` 22:00 / `accommodation_end_time` 00:00 (midnight), the maps
  switches `include_maps_in_render` false / `include_hike_maps` **true** /
  `infer_coordinates_from_address`
  false / `inference_countries` [], and `show_moon_phase` / `show_sun_times`
  both **true**) — plus
  content arrays `days` (required, non-empty), `transport`, `accommodations`.
  Canonical keys may sit in their group or at the top level, but the old
  renamed aliases are gone (`default_start_time`/`default_end_time`/
  `default_buffer`, `start_timezone`/`end_timezone`, transport `date`,
  `transports`, `default`) — use the canonical names.
- **Maps & coordinates.** Every locatable object may carry an optional
  `coordinate` (`{lat, long, show_on_map}`, `show_on_map` defaulting true);
  segments use `start_/end_coordinate` (road, transport) or
  `pickup_/dropoff_coordinate` (car rental). `include_maps_in_render` draws a
  per-day OSM map with a pin per located activity + drives as routes; areas get a
  single pin plus a second zoomed map of their nested points. A transport leg
  with both endpoints mapped is drawn as a **dotted straight line** (its real
  path is unknown; a flight has none on the ground) on every day map it's in
  progress on — so an overnight leg appears on both its departure and arrival
  day — and on the PDF's whole-trip page + the viewer's Overview map. Leg
  endpoints are never
  geocoded, and legs never widen a **printed** map's extent (a transatlantic
  flight would zoom it out to the ocean): the line is clipped at the edge, and
  only a map with nothing else locatable is framed on its legs. The viewer's
  Overview *does* let legs widen its initial view — you can zoom out there.
  `infer_coordinates_from_address` (default off → deterministic/offline, only
  explicit coordinates are mapped) geocodes the rest, restricted to
  `inference_countries` (2-letter ISO codes). Main-map pins are numbered, the
  night's accommodation is pinned with `*`, and area detail-map pins are lettered
  A/B/C…; each pin's label is shown as a small accent disc next to that activity's
  title in the itinerary (no separate legend). That night's `*` is also pinned on
  the day's **zoom (area) maps** — as a pin only, never part of their extent,
  which is fixed by the area's own points, so the zoom/centering is identical
  with or without it (a stay outside the rendered frame simply isn't visible).
- **The whole-trip map** (`maps/build.py`'s `render_trip_map`, drawn by
  `pdf/trip_map.py` on its own page after the cover) is a **port of the viewer's
  🗺️ Overview map** (`web/src/render/tripGeo.ts`) — every day's points merged into
  one map, pinned with the **day number** (the per-day `1..N`/`★`/`A-B-C` mean
  nothing across days), the days' drives as routes, one dotted line per transport
  leg. The outlier trimming is the same: a stray far-off anchor (>6× the median
  distance from the pins' median center *and* >400 km, at most a third of the
  anchors) stops driving the framing but is still drawn. **Keep the two in step**,
  bar two deliberate print-only differences, both because paper can't be zoomed:
  legs never widen the extent (above), and points of the same day closer than
  `_TRIP_PIN_GRID` (~4 km) share one pin, since a page pin says only *which day*
  — a city day would otherwise fan into a pinwheel of identical numbers. The
  viewer's own note naming what it left out was removed (the user found it noise),
  so neither renderer discloses trimmed geometry now.
- **A hike's GPX.** A `hike` may carry `gpx`: the `.gpx` file base64-encoded
  (gzip transparently inflated, a `data:` prefix stripped, line wrapping fine).
  `models/gpx.py` reduces it to a `GpxTrack` — a simplified map line plus a
  distance-resampled elevation profile — which `serialize.py` emits as `track`,
  **with the original base64 inside it** (`track.gpx`): the viewer's
  `(Get GPX track)` link hands the file back, and a resolved hike has no index
  into the source JSON to look itself up by (buffers are woven into the
  timeline), so the blob rides along rather than being matched back. That track
  also **fills in** a missing `distance_km` / `elevation_m` (explicit values
  win).
  `defaults.include_hike_maps` (**true** by default) gates both the drawing *and*
  the serialization, so switching it off keeps kilobytes of geometry out of the
  resolved doc (and out of the browser's IndexedDB day cache). It is deliberately
  **independent of `include_maps_in_render`**: that governs the maps we *infer*
  for the trip, while attaching a GPX to a hike is itself the opt-in — a
  default-true switch gated behind a default-false one would never fire.
  Both renderers draw map-then-profile from the same `track`, with two deliberate
  differences: the PDF's map is a raster and its profile is drawn vector, while
  the viewer's map is the interactive MapLibre one (no static PNG — the geometry
  arrives with the text, not with the per-day map render) honouring the Options
  interactive-maps toggle, and its profile is inline SVG. The viewer alone offers
  `(Get GPX track)` (`GpxDownloadLink`, drawn in the hike's chips line next to
  `(Navigate)`) — a `<button>`, not an `<a href>`, because inflating the payload
  is async so there is nothing to point at until the click; paper can't download
  a file, so it has no PDF twin. Keep `pdf/hike_map.py` and
  `web/src/render/HikeTrack.tsx` in step.
- **Inference is central.**
  - Trip `start_date`/`end_date` are inferred as the earliest/latest date across
    days, transport and accommodation — unless set manually (then they're checked).
  - A day's `date` defaults to trip-start + its index.
  - Activities chain on a timeline: first starts at `defaults.start_time`, each next
    at the previous end; give any two of `start_time`/`end_time`/`duration` and the
    third is inferred. Buffers (default, manual, or gap-inferred) fill gaps.
  - A **`place`** that gives neither a `duration` nor an `end_time` lasts its
    nested activities' total (`activities.nested_duration_total`, applied in
    `Itinerary.from_dict` next to the meal-duration fill-in) — a place is what
    you do there, so zero was always wrong. Only a fallback: an explicit
    duration wins, and the validator's pre-existing `_nested_duration_fit`
    warns when one is set *below* the total. `place` alone, not
    `point_of_interest` (a visit has a length beyond what's nested in it). The
    validator swaps `SCHEDULE` for `specs.PLACE_SCHEDULE` on a place so the
    missing-`duration` info states *this* default, and the Edit tab mirrors
    that with `PLACE_SCHEDULED_FIELDS`.
  - **Auto-sized buffers** (`defaults.auto_sized_buffer`, **on** by default)
    size those gap buffers instead of fixing them, so a day spreads out and its
    last activity lands on `defaults.end_time` (itself now **18:00** when
    unset — it used to be `None`, i.e. no end-of-day check at all, so that
    validator warning is no longer opt-in). `schedule_activities` gained
    `day_end` + `auto_sized_buffer` and became a wrapper: lay the day out tight
    once (`_lay_out`) to measure the slack, `_auto_buffer_plan` decides the
    padding, then **restore the snapshotted scheduling fields** and lay it out
    again — without the restore the first pass's assigned start times would read
    as explicit ones on the second and pin everything. The plan cuts the day at
    every *stated* time (a given `start_time` ends the stretch before it; a given
    `end_time` ends the stretch it's in, so padding never shortens that
    activity), shares each stretch's slack evenly over the gaps between
    consecutive activities, skips a gap a manual `buffer` already fills, and
    rounds down to `AUTO_BUFFER_STEP` (5 min — a residual under 5 min is
    unspent, so the day may end up to 4 min early). A stretch where *no*
    activity has a length is skipped: `kyrgyzstan.json` gives almost no
    durations, and spreading would have turned it into a page of multi-hour
    buffers around instant sights. `defaults.buffer` is
    **superseded, not stacked**: the validator's `_buffer_coherence` warns when
    both are set and the auto one wins. Because a day's whole timeline moves,
    this needed a `SCHEMA_VERSION` bump (v14).
  - Transport requires `start_time`; the other of `end_time`/`duration` is inferred,
    tz-aware. An overnight leg (`start_date` given a `start_time`) becomes that
    night's "accommodation".
- **Enums** (case-insensitive, validated in the model): PoI `category`
  (museum/church/building/viewpoint/ruins/castle/temple/street/other, default
  `other`); hike `route` (loop/back_and_forth/one_way, default back_and_forth);
  transport `type` (plane/train/bus/taxi/ferry/other, default other); accommodation
  `type` (hotel/camping/b&b/other, default hotel). Transport, accommodation and
  car rental all share a tri-state `paid` (paid/to-pay/unset), an optional
  `status` (booked/confirmed) and an optional `description` (see below). Meal
  `meal_type` (breakfast/lunch/dinner/brunch/
  snack/picnic/meal) is optional; when omitted the resolved `category` is
  inferred from the start time, but only ever as breakfast/lunch/dinner (the
  other four are explicit-only). The
  inference thresholds and a default meal duration live in `defaults`
  (`breakfast_until` 10:00, `lunch_until` 16:00, `meal_duration` 0).
- **A booking's `description`.** Transport, accommodation and car rental each
  carry an optional free-text `description` — a *short note* for whatever their
  structured fields don't (a seat, a door code, a fuel policy). Plain text, no
  validation beyond "any text" (one shared `NOTE_DESC` wording across the three
  `validate/specs.py` tables). Both renderers draw it as muted prose wherever the
  object appears, which is **three places**, not one: the section card (PDF
  `pdf/transport.py` / `accommodation.py` / `car_rental.py`, viewer
  `TransportList.tsx` / `AccommodationSummary.tsx` — class `.card-note`), the
  day's row for a leg or a car pick-up/drop-off (`pdf/days.py`'s
  `_transport_row` / `_car_rental_row`, viewer `DayCard.tsx` — `.act-note`), and
  the day's **stay bar** (`.stay-note`) — except that a **sleep-aboard leg**
  fills the bar *and* sits as a row in the same day's itinerary (both
  `night_transport` and `transports_on` select on the departure date), so the
  bar suppresses a note the row above already shows. Both renderers *check*
  rather than assume the two coincide. A `CarRentalEvent` has no way back to
  its rental once resolved, so `serialize.py`'s `_car_event` copies the note onto
  both events. The stay bar is the one place with a cap: it's pinned near the
  page foot, so `_bar_note` wraps to at most `_BAR_NOTE_LINES` (2) with an
  ellipsis and grows the bar by exactly that much — the viewer's `Clamp` plays
  the same role there, and the full text is always on the accommodation page.
  Adding prose to the transport/accommodation *views* is also why `Book.tsx` now
  wraps them in `ClampProvider` (without it the notes would ignore the app's
  "show full descriptions" option). The `.ics` export packs it as a
  `Description:` detail line, the same label activities already use.
- **A day's `bank_holiday`.** An optional boolean (default false) marking a day
  that falls on a public holiday where you are. Both renderers open the day's
  body with a call-out banner — ahead of the intro *and* the day map, since it
  changes what you'll find open — drawn by `pdf/base.py`'s new shared `_notice`
  primitive (a full-width accent-tinted strip with the `_card_bg` spine,
  outline-only under `ink_saver`) and by `DayCard.tsx`'s `BankHolidayBanner`
  (`.day-holiday`). Deliberately a **flag, not a name**: the banner reads the
  same whichever holiday it is, so there is nothing to localize per country. The
  label and its one-line advice are the same two English sources in
  `translations.py` and `render/format.ts` (`bankHoliday` / `bankHolidayNote`) —
  keep the wordings in step; the ⚠️ is added by each renderer, not the key
  (U+26A0 + U+FE0F are in DejaVu, like the sun line's ☀️, so no emoji fallback is
  involved). `_notice` has room for one line only and **drops** the advice when
  the label plus sentence would overrun; the viewer wraps it under instead.
  Nothing infers it — holiday dates differ by country and year, which is why
  `skills/build-full-json.md` carves it out as the one field an LLM is told to
  look up rather than take from the source documents. No example sets it: no day
  of `france.json` (Sept 4–11, 2026) or `pyrenees.json` (June 8–11, 2026) is a
  real French holiday, and `kyrgyzstan.json` is dateless, so flagging one would
  contradict that skill guidance. `broken.json` carries an invalid value for the
  validator's `V_BOOL`, and `tests/test_bank_holiday.py` covers the rest.
- **A point of interest's opening days & hours.** Two optional strings on
  `point_of_interest` alone — `opening_days` (`tue-sun` / `mon-fri, sun`; single
  days and/or ranges, English names or 3-letter prefixes, a range may wrap the
  week) and `opening_hours` (`09:30-18:00` / `09:30-12:30, 14:00-18:00`; a close
  before its open crosses midnight). Deliberately **compact strings, not
  objects**: a guidebook line ("Tue–Sun 9.30–12.30 & 2–6pm") transcribes as it
  stands, and the Edit tab needs two text inputs. `models/opening.py` reduces
  both to one frozen `Opening` (`None` when neither is given, so *absent* means
  every day / all day rather than "unknown") carrying `day_runs` — the days
  folded back into `(first, last)` pairs, **wrapping the week** so a place shut
  on Tuesdays reads `Wed–Mon` (the printed convention) instead of splitting into
  `Mon, Wed–Sun` — and the language-neutral `hours_display` (`09:30–12:30, 14:00–18:00`,
  digits only, hence computed once). Weekday *names* do need localizing, so each
  renderer names the runs itself: `lang/dates.py`'s `fmt_weekday_runs` for the
  PDF/validator/ICS, `render/format.ts`'s `fmtWeekdayRuns` (+ the `wdMon`…`wdSun`
  keys, mirroring `_WEEKDAY_ABBR`) for the viewer — keep those two in step, and
  `WEEKDAYS` in step with `_WEEKDAY_FULL["en"]` lowercased (a test pins that).
  Both renderers draw one row under the address — `Open   Tue–Sun  ·  09:30–…`,
  `pdf/days.py`'s `_opening_line` (top-level *and* nested POI) and `DayCard.tsx`'s
  `Opening` / `.act-opening` — and the `.ics` packs an `Open:` detail line.
  Neither renderer flags a visit falling **outside** the opening: that is the
  validator's `_check_opening`, because the fix belongs in the JSON. It reads the
  *resolved* timeline (a visit's start time is normally inferred, so checking the
  raw JSON would catch almost nothing), via the new memoized `_model()` +
  `_resolved_activities()` — which `_check_end_of_day` now shares, so the model
  is built once. `covers()` requires the visit to fit inside a **single** range,
  which is the whole reason a midday closure is kept as two. A **nested** stop is
  never scheduled, so it gets the closed-day check but not the hours one.
  `skills/build-full-json.md` insists these be kept whenever the source states
  them, and — unlike `bank_holiday` — explicitly forbids looking them up.
- **Guidebook pages.** The four activity types that carry a `description` —
  `road`, `point_of_interest`, `place`, `hike` — also carry an optional
  `guidebook_pages` string: page numbers only (`14` / `15-18` /
  `16, 23, 25-30`), validated by `V_PAGES` in `validate/specs.py`, which
  **errors** on prose like `pp. 15-18`. Both renderers append it as a
  **light-accent pill at the end of the description text** (soft accent fill,
  accent text, not bold), dropping to its own line only when it won't fit or when
  there is no description: the PDF via `_para_with_pill` / `_guidebook_pill` in
  `pdf/base.py` (which derives the pill's y from the **live cursor** after the
  paragraph — computing `y + (n-1)*h` puts the box on the previous page when the
  prose auto-breaks), the viewer via `Clamp`'s `trailing` prop plus
  `.chip.guidebook` on `--accent-light` (added by `render/palette.ts`).
  The label is a template each renderer fills from the same English source —
  `"Guidebook p. {pages}"` in `translations.py` / the `guidebook` key in
  `render/format.ts` — so the two wordings must move together. The `.ics` export
  packs it as a `Guidebook:` detail line.
- **Prices & currency.** A `price` is a bare `float` (no symbol); its `currency`
  is a 3-letter ISO code that defaults to `defaults.currency` (EUR). Conversion
  lives in `models/currency.py` (`SecondaryCurrency`, `to_default`,
  `format_money`); `defaults.secondary_currencies` is a list of
  `{currency, change_rate}` with the rate in *units of that currency per one
  unit of the default*. The PDF prints each price in the default currency with
  the secondary conversions faded in parentheses (`_draw_price` in `pdf/base.py`
  — converted amounts show 2 decimals below 25, whole at/above). The validator
  errors on a price currency that is neither the default nor a declared
  secondary, and on malformed `secondary_currencies` entries.
- **Validation has three levels**, filtered by `--verbose`: ❌ errors (missing
  required, invalid value, incoherence), ⚠️ warnings (soft inconsistencies:
  nowhere-to-sleep, city mismatch, hike route/endpoints, ends-after-`end_time`…),
  ℹ️ info (optional field missing → states the default). Every finding carries a
  line number. Build surfaces errors-only but does not block.
- **i18n is gettext-style.** English is the source string; `tr(text, lang)` maps
  it (templates keep `{placeholders}` — translate *then* `.format`). Missing keys
  fall back to English. Dates are localized via name tables + per-language ordering.

## Conventions & gotchas

- Text is drawn with the bundled **DejaVu** TTF (`src/odysseyra_travelbook/fonts/`) so any
  Unicode (accents, arrows `→`, `✓`) renders. Do not switch to core fonts.
  DejaVu has **no emoji**, so the moon-phase glyphs (`show_moon_phase`) come
  from a tiny bundled Noto Emoji subset (`NotoEmojiMoon.ttf`, 8 glyphs
  U+1F311–U+1F318) registered as an fpdf2 fallback in `pdf/base.py`. Phase
  computation is in `models/moon.py` (`moon_phase(date)`), used by both the PDF
  and `serialize.py`; the phase name is localized (English source in
  `translations.py`, and the shared label key in the viewer's `render/format.ts`).
  Sunrise/sunset (`show_sun_times`, **on** by default) needs no emoji font
  either: `☀️ Sunrise: 06:12, Sunset: 21:34` uses DejaVu's own U+2600 + U+FE0F,
  so the browser shows a colour emoji and the PDF a text sun, with no
  missing-glyph box. The labels are words, so the string is language-dependent:
  `models.SunTimes` carries only the two times (+ `.hhmm`) and each renderer
  fills the **same English template** — `pdf/days.py` via `translations.py`,
  the viewer via `render/format.ts`'s `sunTimes` key. French deliberately
  shortens to `Lever`/`Coucher`: the full `Lever du soleil`/`Coucher du soleil`
  leaves ~1 mm before the band's kicker on the longest example day.
  Placement differs on purpose: the PDF closes the day's header band with it,
  the viewer opens the day's body with it (`.day-sun`, above `.day-intro`), so
  in the viewer it's hidden while the day is collapsed.
  **With both switches on, the phase closes that same line** (`☀️ Sunrise:
  07:12, Sunset: 20:27, 🌕 Full moon`) — a second template,
  `"…, {emoji} {moon}"` / `sunTimesMoon`, filled with the *already localized*
  phase name. It then **leaves the stay bar** rather than printing twice on one
  page, in both renderers: `pdf/days.py`'s `day()` decides and passes the
  leftover to `_day_stay(day, moon=…)`, and `DayCard.tsx`'s `StayBar` shows its
  emoji only when `!day.sun`. So the bar still carries the moon when the sun
  times are off *or* unavailable (no usable reference — every `kyrgyzstan.json`
  day, `france.json` day 1). The PDF has one extra wrinkle the viewer doesn't
  need: the band's kicker and meta line share a row drawn from opposite margins,
  so `_sun_moon_text` measures and degrades — named phase, then emoji alone,
  then back to the stay bar (a long city name plus `Lune gibbeuse décroissante`
  overruns; france day 5 and pyrenees day 4 land on emoji-only).
  The two ends are located separately by `sun_for` via mirrored chains, so a day
  you change town gets both right: the **sunset** at `sun_reference` (that
  night's accommodation → the day's own **last** located stop → the nearest dated
  located stay) and the **sunrise** at `wake_reference` (the **previous** night's
  stay → the day's own **first** located stop → the nearest dated located stay).
  `_first_coordinate`/`_last_coordinate` walk nested activities and a road's
  `waypoints` (its `coordinate` is the departure, its last waypoint the
  arrival). An unusable morning reference falls back to the evening's. The
  clock is `day_timezone(day)` (a day's first explicit `start_tz`, else
  `defaults.timezone`), and `_sun_at` drops a reference sitting more than
  `_MAX_CLOCK_GAP_MIN` (3 h) of solar time from it — a New York day printed on
  Paris time would read as a bug — which is why `france.json` day 1 shows none
  and day 2's sunrise comes from Paris, not the Atlantic crossing.
- The model raises `ItineraryError` on bad data; the validator instead reports it
  (it does its own parsing and never calls a mutating path except a guarded
  `Itinerary.from_dict` for the end-of-day check).
- **Examples are kept in sync and tested.** `examples/france.json` (the flagship:
  a valid, feature-rich France tour, maps on — also the web viewer's **Demo**) and
  `examples/france_fr.json` (same trip in French — build with `--lang fr`);
  `examples/pyrenees.json` (valid, English — the one example with
  `auto_sized_buffer` **off** and a fixed `buffer`, so both spacing paths stay
  rendered), `examples/pyrenees_pieces/` (the same
  trip split into per-file fragments for `stitch` — a test asserts it reassembles
  `pyrenees.json` exactly, so keep the two in sync), `examples/pyrenees_fr.json`
  (same trip in French — build with `--lang fr`), `examples/kyrgyzstan.json`
  (maps-on, explicit coordinates, sparse OSM region — some sights intentionally
  unpinned; a test asserts it validates clean), `examples/broken.json` (exercises
  every validator rule).
  `examples/broken_validator_output.txt` is a **snapshot** compared by
  `test_validate.py`; whenever the JSON format or a message changes, regenerate it
  with `UPDATE_SNAPSHOTS=1 pytest`.
- **Re-render the example PDFs after every code change.** The rendered PDFs are
  the primary way changes get reviewed, so keep them current — they are
  gitignored (`*.pdf`) and untracked, so nothing else updates them. Rebuild them
  all (`france.json` and `kyrgyzstan.json` are maps-on via `include_maps_in_render`,
  so they need network for tiles/routes unless the cache is warm, but the build
  degrades gracefully offline):
  ```bash
  .venv/bin/odysseyra-travelBook build examples/france.json -o examples/france.pdf
  .venv/bin/odysseyra-travelBook build examples/france_fr.json --lang fr -o examples/france_fr.pdf
  .venv/bin/odysseyra-travelBook build examples/pyrenees.json -o examples/pyrenees.pdf
  .venv/bin/odysseyra-travelBook build examples/pyrenees_fr.json --lang fr -o examples/pyrenees_fr.pdf
  .venv/bin/odysseyra-travelBook build examples/pyrenees.json --ink-saver -o examples/pyrenees_inksaver.pdf
  .venv/bin/odysseyra-travelBook build examples/kyrgyzstan.json -o examples/kyrgyzstan.pdf
  ```
  (macOS Preview caches an open PDF — a rebuild only shows after reopening it.)
- When adding/renaming a field or message, update **all** of:
  - the model `from_dict`;
  - the validator `specs.py` (+ any coherence check);
  - the PDF renderer;
  - `serialize.py` and its TS mirrors (`web/src/types/resolved.ts`, and
    `source.ts` for an input field) — without this the value never reaches the
    browser at all;
  - **the viewer's renderer** (`web/src/render/`, usually `DayCard.tsx` + a label
    key in `render/format.ts` for both languages). The PDF and the viewer render
    the *same* resolved field from two independent code paths, so adding it to one
    and not the other is a silent divergence — that is exactly how a `hike`'s
    `description` printed in the book for months while the viewer dropped it;
  - **the Edit tab** (`web/src/edit/schema.ts`, plus the French label/help in
    `web/src/i18n/fr.ts`, and `SAFE_DEFAULTS` in `edit/serialize.ts` for a
    `defaults` switch — a boolean that defaults *on* needs `defaultOn: true` so
    the checkbox reads and writes the right way round; a new `defaults` field
    goes inside one of `DEFAULTS_GROUPS`, whose titles are the form's section
    headings and need a French key too, and `DEFAULTS_FIELDS` flattens them);
  - both example JSONs;
  - the README tables;
  - the French `translations.py`;
  - **`skills/build-full-json.md`** (the field tables/examples an LLM uses to
    extract JSON);
  - then regenerate the snapshot and re-render the example PDFs.
- **Changing the resolved `Day` — a new field, or a new way of computing an
  existing one — must bump `SCHEMA_VERSION` in `web/src/maps/mapCache.ts`.**
  That IndexedDB cache stores the *whole* resolved
  day (pin labels included, not just the map images) keyed by the itinerary's
  hash, and `App.tsx`'s `buildDayMaps` swaps a hit in wholesale — so for an
  **unchanged** itinerary (the Demo!) a day cached by an older build silently
  masks the new value, in the browser only. The hash can't catch it: the JSON is
  byte-identical, only our code moved. The version is part of the cache key,
  so bumping it turns those entries into misses; `purgeExpired` then sweeps them.
  Symptom to recognise: the CLI/PDF and a fresh `to_dict` show the field, the
  viewer doesn't, and a hard reload doesn't help (the data is in IndexedDB, not
  the HTTP cache). This is also why Python changes need `npm run wheel` — the
  browser runs the wheel, not `src/`.
- **`skills/`** holds LLM-facing docs:
  - `build-full-json.md` — a self-contained guide (it duplicates every field
    table, value format and rule) that turns raw text/screenshots into the
    **entire** itinerary as one `<title>.json`, needing no other file, no source
    code, and no tool. **Any JSON-format change must be mirrored here** — it is
    authoritative alongside the README.
  - `fix-missing-duration-distance.md` — from a JSON + a list of validator
    warnings about missing duration/distance/elevation, builds a fill-in-the-blank
    Markdown worksheet (Google Maps links for road distances; web-inferred hike
    figures tagged `[to be checked]`). If the magnitude-warning messages change,
    update its warning-patterns table.
- `README.md` documents the JSON schema field-by-field (one table per object,
  with Required/Type/Format/Default) — keep it authoritative.
