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
day-by-day overview table), one **page per day** (colored header band with the
city / date / sunrise→sunset, intro,
a merged time-ordered itinerary, and a bottom "tonight's stay" bar), a
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
- **`pdf/`** — `TravelPDF(CoverMixin, DayMixin, DayMapMixin, TransportMixin,
  AccommodationMixin, CarRentalMixin, _PDFBase)`. `base.py` holds fonts/colors and
  shared drawing primitives; each section is a mixin. `build_pdf(itinerary, output,
  lang, ink_saver, maps, cache_dir)` is the entry point. The `ink_saver` flag (CLI
  `--ink-saver`) is stored on `_PDFBase` and read by the primitives that draw large
  solid accent areas — the cover banner, the `_band_header` page bands, `_card_bg`,
  `_badge`, `_pill`, `_chip` — which then render outlines + accent-colored text +
  thin rules instead of solid fills. `day_map.py`'s `DayMapMixin` embeds the per-day
  map (from `maps/`) after the intro plus a numbered legend, and each area's zoom
  map inline after it; it degrades gracefully (a map failure never breaks the build).
- **`maps/`** — per-day map rendering, imported only when maps are on. `geocode.py`
  (Nominatim + `countrycodes` + disk cache), `routing.py` (OSRM driving geometry +
  cache), `render.py` (Carto Positron `@2x` tiles → contrast boost → dotted
  transport legs → translucent theme-colored route → rotated numbered teardrop
  pins → label sandwich; pure Pillow, with `dashes()` splitting a polyline into
  dash pieces), `build.py` (`resolve_day` → points/routes/area-details,
  `day_legs` → a day's transport legs as straight endpoint pairs,
  `render_day_maps` → PIL images), `writeback.py` (`fill_coordinates` for the
  `geocode` command),
  and `Cache` (geocode/routes/tiles on disk under `~/.cache/odysseyra`, or
  `$ODYSSEYRA_CACHE`). Uses `Pillow`; everything networked goes through `urllib`.
- **`lang/`** — localization. `dates.py` (month/weekday tables + `fmt_date`),
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
  `end_time`, `buffer`, `timezone` GMT, meal thresholds `breakfast_until` 10:00 /
  `lunch_until` 16:00, `meal_duration` 0, `currency` EUR,
  `secondary_currencies`, the accommodation calendar-event times
  `accommodation_start_time` 22:00 / `accommodation_end_time` 00:00 (midnight), the maps
  switches `include_maps_in_render` false / `infer_coordinates_from_address`
  false / `inference_countries` [], `show_moon_phase` false and
  `show_sun_times` **true**) — plus
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
  day — and on the viewer's whole-trip Overview map. Leg endpoints are never
  geocoded, and legs never widen a day map's extent (a transatlantic flight would
  zoom it out to the ocean): the line is clipped at the edge, and only a day with
  nothing else locatable is framed on its legs.
  `infer_coordinates_from_address` (default off → deterministic/offline, only
  explicit coordinates are mapped) geocodes the rest, restricted to
  `inference_countries` (2-letter ISO codes). Main-map pins are numbered, the
  night's accommodation is pinned with `*`, and area detail-map pins are lettered
  A/B/C…; each pin's label is shown as a small accent disc next to that activity's
  title in the itinerary (no separate legend). That night's `*` is also pinned on
  the day's **zoom (area) maps** — as a pin only, never part of their extent,
  which is fixed by the area's own points, so the zoom/centering is identical
  with or without it (a stay outside the rendered frame simply isn't visible).
- **Inference is central.**
  - Trip `start_date`/`end_date` are inferred as the earliest/latest date across
    days, transport and accommodation — unless set manually (then they're checked).
  - A day's `date` defaults to trip-start + its index.
  - Activities chain on a timeline: first starts at `defaults.start_time`, each next
    at the previous end; give any two of `start_time`/`end_time`/`duration` and the
    third is inferred. Buffers (default, manual, or gap-inferred) fill gaps.
  - Transport requires `start_time`; the other of `end_time`/`duration` is inferred,
    tz-aware. An overnight leg (`start_date` given a `start_time`) becomes that
    night's "accommodation".
- **Enums** (case-insensitive, validated in the model): PoI `category`
  (museum/church/building/viewpoint/ruins/castle/temple/street/other, default
  `other`); hike `route` (loop/back_and_forth/one_way, default back_and_forth);
  transport `type` (plane/train/bus/taxi/ferry/other, default other); accommodation
  `type` (hotel/camping/b&b/other, default hotel). Transport, accommodation and
  car rental all share a tri-state `paid` (paid/to-pay/unset) and an optional
  `status` (booked/confirmed). Meal `meal_type` (breakfast/lunch/dinner/brunch/
  snack/picnic/meal) is optional; when omitted the resolved `category` is
  inferred from the start time, but only ever as breakfast/lunch/dinner (the
  other four are explicit-only). The
  inference thresholds and a default meal duration live in `defaults`
  (`breakfast_until` 10:00, `lunch_until` 16:00, `meal_duration` 0).
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
  `examples/pyrenees.json` (valid, English), `examples/pyrenees_pieces/` (the same
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
- When adding/renaming a field or message, update: the model `from_dict`, the
  validator `specs.py` (+ any coherence check), the PDF renderer, both example
  JSONs, the README tables, the French `translations.py`, **`skills/build-full-json.md`**
  (the field tables/examples an LLM uses to extract JSON),
  regenerate the snapshot, and re-render the example PDFs.
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
