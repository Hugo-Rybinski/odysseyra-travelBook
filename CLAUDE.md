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
odysseyra-travelBook build examples/france_fr.json --lang fr -o out_fr.pdf
odysseyra-travelBook build examples/pyrenees.json --ink-saver -o out.pdf   # outlines, not solid fills
odysseyra-travelBook build examples/pyrenees.json --maps -o out.pdf   # per-day maps
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
    inherited by `Activity`, `TransportLeg` and `CarRentalEvent`; plus `Stamp`
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
  - `misc.py` — the `misc` group: `EmergencyContact` (`name`/`contact`, both
    optional free text) + `parse_emergency_contacts`, flattened onto
    `Itinerary.emergency_contacts`.
  - `activities.py` — `Activity` base + the 6 activity types (`road`,
    `point_of_interest`, `place`, `hike`, `meal`, `buffer`), `activity_from_dict`,
    `schedule_activities` (the day timeline pass) and `resolve_meal_categories`
    (fills each `Meal.category` from the trip thresholds after scheduling). Also
    `Waypoint` + `_road_chain`, which lower a road's input `legs` onto the
    departure + waypoint chain everything downstream reads (see the road bullet
    below).
  - `transport.py` — `Transport` (a booking) + `TransportLeg` (one hop, a
    `Scheduled`) + `resolve_transport(leg, …)` (tz-aware time inference, per leg).
    A leg proxies its booking's shared fields (`type`, `booking_number`,
    `booking_source`, `website`, `booking_link`, `status`, `price`, `currency`,
    `paid`, plus `leg_index`/`leg_count`) through read-only properties, so
    everything downstream can keep treating a leg as self-contained.
    `Itinerary.legs` flattens every booking's legs; `transports_on(day)` /
    `night_transport(day)` return **legs**.
  - `accommodation.py` — `Accommodation`.
  - `itinerary.py` — `Day` and `Itinerary` (top-level `from_dict`, date inference).
- **`validate/`** — read-only checker, never mutates.
  - `jsonpos.py` — a hand-written position-tracking JSON parser returning
    `(data, lines)` where `lines` maps a path tuple → 1-based line number.
  - `findings.py` — `Finding` (level/line/message), icons, `format_findings`.
  - `specs.py` — `Spec` field descriptors, value validators (`V_*`), spec tables.
  - `validator.py` — `_Validator` walks the data and emits findings; `validate_text`.
- **`pdf/`** — `TravelPDF(CoverMixin, DayMixin, DayMapMixin, TripMapMixin,
  HikeMapMixin, TransportMixin, AccommodationMixin, CarRentalMixin, MiscMixin,
  _PDFBase)`. `base.py` holds fonts/colors and
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
  `misc.py`'s `MiscMixin.emergency_contacts()` draws the **last page** of the
  book — the `misc` group's contacts as a plain hairline-ruled directory (name
  left, number right in accent), not cards: it's a list read in a hurry, and a
  contact has two fields where a booking has a dozen.
- **`maps/`** — map rendering, imported only when maps are on. `geocode.py`
  (Nominatim + `countrycodes` + disk cache), `routing.py` (OSRM driving geometry +
  cache), `mvt.py` + `basemap.py` (Carto Positron's **vector** tiles decoded and
  drawn — see the basemap bullet under "Key design decisions"),
  `render.py` (basemap → contrast boost → dotted
  transport legs → translucent theme-colored route → rotated numbered teardrop
  pins → collision-checked place labels; pure Pillow, with `dashes()` splitting a
  polyline into dash pieces),
  `build.py` (`resolve_day` → points/routes/area-details,
  `day_legs` → a day's transport legs as straight endpoint pairs,
  `render_day_maps` → PIL images, plus `resolve_trip`/`_trip_extent`/
  `render_trip_map` for the whole-trip map and `render_hike_map(track, …)` for a
  hike's GPX — the one map with nothing to resolve, so it geocodes and routes
  nothing and needs only tiles), `writeback.py` (`fill_coordinates` for the
  `geocode` command),
  and `Cache` (geocode/routes/tiles on disk under `~/.cache/odysseyra`, or
  `$ODYSSEYRA_CACHE`; tiles are `vec_<z>_<x>_<y>.mvt` — the old raster
  `nolabels_*`/`onlylabels_*.png` files are dead and can be deleted). Uses
  `Pillow`; everything networked goes through `maps.http_get` (`urllib`
  natively, a `fetch` shim in the browser) — `basemap.tile_bytes` retries a
  transient tile failure, since one rate-limited tile otherwise silently costs
  the whole map. It also reads a **404 as an empty tile, not a failure**: a
  vector-tile server answers that for a square holding no features, which over
  empty country is the truth — and the map that most needs drawing is exactly
  the one out where the tiles run thin (Köl-Suu's trail lost its whole map to a
  single blank z13 square). It comes back as no bytes → `mvt.decode` → no
  layers → bare background, and caches as an empty file so a rebuild costs no
  request. Every **other** 4xx still raises, because those say the *request* is
  wrong (a bad URL, a moved endpoint, a key now required) and must not degrade
  into a book of blank maps. **The browser never sees that status**, which is
  why the rule can't live in `tile_bytes` alone: Carto sends
  `Access-Control-Allow-Origin: *` on a tile it *has* and **no CORS header at
  all** on the 404, so a cross-origin 404 is blocked before its status is
  readable and `netbridge.ts` reports a bare `status: 0` — indistinguishable
  from being offline (it retried it as transient and lost the map, so Köl-Suu's
  trail came back in the CLI and stayed missing in the viewer). So the decision
  is taken **per render** in `render_basemap`, which asks whether the *source*
  answered rather than what one square said: draw whatever came back (an empty
  tile counts — "nothing here" is an answer) and raise only when **every** tile
  failed, which is what a wrong URL / moved endpoint / newly-required key does.
  One policy, both renderers, and the "a broken source must not degrade into
  blank maps" half is preserved.
- **`lang/`** — localization. `dates.py` (month/weekday tables + `fmt_date`,
  plus `weekday_name` and `fmt_weekday_runs` for a POI's opening days),
  `translations.py` (English→French map), `__init__` (`tr`, `LANGUAGES`).
- **`ics.py`** — `build_ics(itinerary, output=None, lang, now=None)` exports a
  resolved itinerary to an iCalendar (`.ics`) string (CLI `ics`, and the viewer's
  **Options → Calendar export**). One `VEVENT` per day activity (buffers excluded),
  transport **leg** (so a booking that moves you twice yields two events), car
  pick-up/drop-off and accommodation **night**. Times are emitted
  as local wall time tagged with a self-contained fixed-offset `VTIMEZONE` (from
  each item's `start_tz`/`end_tz`, falling back to `defaults.timezone`), so events
  land at the right instant and show local time; each night runs from that evening
  at `defaults.accommodation_start_time` to `accommodation_end_time` (midnight by default).
  Descriptions are packed with each object's detail, localized via `lang.tr`.
  Pure stdlib (RFC 5545 line-folding + text escaping), no dependencies.
- **`stitch.py`** — `aggregate(directory, ask=input)` assembles one itinerary
  dict from a fragment directory (`travel_description.json`, `defaults.json`,
  `misc.json`, and
  `days/` `transports/` `accommodations/` `car-rentals/` folders — one array
  entry per JSON file, ordered by filename; alternate folder spellings accepted).
  Prompts for `travel_description` when its file is absent. `create_skeleton`
  scaffolds the reverse — an empty fragment dir (`SKELETON_DIRS` sub-folders +
  a `{"title": "FIXME"}` stub). `safe_filename` and `StitchError` round it out.
- `cli.py` — argparse CLI (`build` / `validate` / `ics` / `stitch` / `geocode` /
  `create-skeleton`, `--lang`, `--verbose`). `build` also takes `--maps/--no-maps`,
  `--map-provider`, `--cache-dir`; `geocode` fills coordinates and writes them back
  (its `--country` defaults to `defaults.inference_countries`).

## Key design decisions

- **JSON shape.** Three config groups — `travel_description` (title/summary/color,
  optional manual `start_date`/`end_date`) and `defaults` (`start_time` 08:00,
  `end_time` **18:00**, `auto_sized_buffer` **true** / `buffer` 0 (alternatives,
  not layers), `timezone` GMT, meal thresholds `breakfast_until` 10:00 /
  `lunch_until` 16:00, `meal_duration` 0, `currency` EUR,
  `secondary_currencies`, the accommodation calendar-event times
  `accommodation_start_time` 22:00 / `accommodation_end_time` 00:00 (midnight), the maps
  switches `include_maps_in_render` false / `include_hike_maps` **true** /
  `infer_coordinates_from_address`
  false / `inference_countries` [], and `show_moon_phase` / `show_sun_times`
  both **true**) and `misc` (`emergency_contacts`, see below) — plus
  content arrays `days` (required, non-empty), `transport` (bookings, each with
  a required non-empty `legs`), `accommodations`.
  Canonical keys may sit in their group or at the top level, but the old
  renamed aliases are gone (`default_start_time`/`default_end_time`/
  `default_buffer`, `start_timezone`/`end_timezone`, transport `date`,
  `transports`, `default`) — use the canonical names. **`misc` is the one
  exception to the top-level fallback**: it is read from its own object only,
  since it's new (no older shape to support) and a bare top-level
  `emergency_contacts` would read as a fifth content array.
- **A day's `activities` is optional and may be empty** — unlike a booking's
  `legs` or a road's, which really cannot be. A travel day carried by one
  flight, or a night whose only entry is the hotel, has no timeline of its own,
  and the page still prints its header band, that leg's row and the stay bar (as
  do the viewer's day card and the `.ics`). It used to be a required,
  non-empty-checked field, i.e. an **error** on a perfectly well-written day —
  and one the Edit tab's own save path produced, since `edit/serialize.ts`
  prunes an empty array away entirely, so emptying a day there and saving made
  the file invalid. The absent key and the empty array are therefore the *same*
  case, and neither renderer ever blocked on it (`build` reports errors without
  refusing to print; the viewer never gated on them at all). What survives is a
  **warning** from `validator.py`'s `_day` for a day with nothing on it *at
  all*: no activities **and** no transport leg, accommodation night or car
  pick-up/drop-off on the date. Judging that needs the resolved dates (a day's
  `date` is normally inferred from its index), so `_booked_on` goes through the
  memoized `_model()` — and when the file won't build, or a lone `day` fragment
  is being validated, it can't tell and the warning fires. `pdf/days.py` already
  omitted the *Itinerary* heading for an empty timeline; `DayCard.tsx` now skips
  the whole `<ol className="timeline">`, whose padding would otherwise leave a
  gap between the band and the stay bar.
- **Maps & coordinates.** Every locatable object may carry an optional
  `coordinate` (`{lat, long, show_on_map}`, `show_on_map` defaulting true);
  segments use `start_/end_coordinate` (a **road leg**, a transport **leg**) or
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
  `inference_countries` (2-letter ISO codes). Those two are **`defaults` fields
  only** — deliberately *not* overridable at build time. They used to be a
  `build --map-country` flag and two controls in the viewer's Options → PDF
  export (which mutated `itinerary.inference_countries` /
  `.infer_coordinates_from_address` in `cli.py` and `web/.../bridge.py`), so the
  same file could yield a differently-geocoded book depending on which renderer
  ran it, and the viewer's on-screen maps — which never read the overrides —
  disagreed with the PDF it exported. What gets geocoded is trip data, so it
  belongs in the file; edit it in the Edit tab's Defaults section
  (`infer_coordinates_from_address` / `inference_countries`). `--maps/--no-maps`
  and the Options *Include maps* toggle remain overridable: whether to *print*
  maps is a print choice, not data. Main-map pins are numbered, the
  night's accommodation is pinned with `*`, and area detail-map pins are lettered
  A/B/C…; each pin's label is shown as a small accent disc next to that activity's
  title in the itinerary (no separate legend). That night's `*` is also pinned on
  the day's **zoom (area) maps** — as a pin only, never part of their extent,
  which is fixed by the area's own points, so the zoom/centering is identical
  with or without it (a stay outside the rendered frame simply isn't visible).
- **One place, one pin.** A day names the same spot more than once as a matter
  of course — a drive's junction is the next drive's departure, an out-and-back
  passes its turning point twice, the village you park in is also the sight you
  walk to — and every mention used to earn its own number, so a place wore two
  or three pins stacked on each other and `N` counted mentions rather than
  places. `maps/build.py`'s **`fold_pins`** groups the day's located points
  before they are numbered: two join when their names key alike (`_pin_key` —
  accents stripped, case folded, quote/dash variants unified, whitespace
  collapsed, so a name typed by hand and one lifted out of a GPX match) **and**
  they sit within `PIN_MERGE_KM` (**1 km**). Both halves are load-bearing: the
  name alone would merge two different `Sainte-Marie`s at opposite ends of a
  driving day, and proximity alone would merge the museum with the café across
  the square, which are two stops wanting two numbers. A candidate is measured
  against the group's **first** member — the point the pin is actually drawn
  at — so a chain of near-misses can't drift a group across a valley, and a
  nameless point never merges. The whole group maps onto the one label, so the
  itinerary's discs, the map's pins and the legend agree with no extra plumbing
  (`number_for` is unchanged; this is a different mechanism from
  `pin_aliases`, which is driven by the `same_*_as_*_activity` flags rather than
  by the data, and the two compose). It applies to the numbered main map **and**
  to an area's lettered A/B/C…, and it must be computed identically in the
  static renderer (`render_day_maps`) and the interactive one
  (`web/src/pyodide/bridge.py`'s `_day_geo`) or the two disagree about what "3"
  is — both call `fold_pins`. Deliberately **not** applied to the whole-trip
  map, whose pin carries the *day* and which already collapses a day's
  neighbours on its own `_TRIP_PIN_GRID` (~4 km); nor to the night's stay `*`,
  which is a distinct marker rather than a number. No example merges anything
  today (a drive's final arrival isn't pinned by default), so the example PDFs
  are unchanged — `tests/test_pin_folding.py` is where the behaviour lives.
  Because it changes an existing resolved-`Day` field's *value*, it needed a
  `SCHEMA_VERSION` bump (**v21**).
- **The cover's HIGHLIGHTS cell** (`pdf/cover.py`'s `_day_highlights` /
  `Cover.tsx`'s `highlightsOf` — keep the two in step) lists a day's points of
  interest, places and hikes, its long drives (>60 min) and its transport legs,
  in time order. A **detour** is never one (see that bullet), and a **drive is
  dropped once the day has two other stops**: the drive is how you got to them
  rather than what the day is for, and this is a few words on a table row, so
  `Road Amboise → Sarlat-la-Canéda` was crowding out the château it delivered
  you to. Below two it stays, so a day of one visit plus a long transfer still
  reads as both, and a day with *nothing* else still falls back to its drives —
  short ones included, which is the case that fallback exists for. Only
  *activities* count toward the two: a transport leg is not one, and a flight
  day is exactly when the drive to the airport is worth naming. Four rows of
  the examples changed (`france.json` days 4 and 7, `pyrenees.json` days 3 and
  4); `tests/test_cover_highlights.py` is where the rule lives.
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
  so neither renderer discloses trimmed geometry now. Two kinds of point are
  left out of both, for the same reason — at this zoom they say nothing the day
  number doesn't: an **area's nested points** (they collapse into its one main
  pin) and a **drive's own points** (its departure, junctions and arrival — see
  the `display_*_on_maps` bullet; the drive is drawn as a route already).
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
  Both renderers draw map-then-profile from the same `track`, with one deliberate
  difference: the PDF's profile is drawn vector, the viewer's is inline SVG. The
  **map** obeys the Options interactive-maps toggle like every other viewer map
  — the MapLibre one when it's on (drawing straight away, since the geometry
  arrives with the text), the static PNG when it's off. That PNG is
  `track.map`, rendered per day by `bridge.py`'s `_stamp_hike_maps` and
  therefore arriving with the day's other images rather than with the text; it
  used not to exist at all, which left a hike showing its profile and no trail
  whenever the toggle was off while the PDF printed both. Because the render is
  per-day, `App.tsx`'s `wantsDayRender` runs the day loop for a trip that draws
  **no** day maps but has a track — otherwise the one switch that is
  deliberately independent of `include_maps_in_render` would depend on it after
  all. Since the resolved `Day` gains a field, this needed a `SCHEMA_VERSION`
  bump (**v24**) — which also covers the tile-404 fix changing every *rendered
  image* inside a cached day. The viewer alone offers
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
    activity has a length is skipped: a day written with no durations at all
    (some trips are) would otherwise spread into a page of multi-hour buffers
    around instant sights. `defaults.buffer` is
    **superseded, not stacked**: the validator's `_buffer_coherence` warns when
    both are set and the auto one wins. Because a day's whole timeline moves,
    this needed a `SCHEMA_VERSION` bump (v14).
  - A transport **leg** requires `start_time`; the other of `end_time`/`duration`
    is inferred, tz-aware. An overnight leg (`start_date` given a `start_time`)
    becomes that night's "accommodation". A **booking** infers nothing of its
    own: its `title`/`start_date`/`end_date` are derived from its legs (first
    departure → last arrival).
- **A drive is its `legs`.** A `road` is written as an ordered array of `legs` —
  one per hop, each with `start_/end_location`, `start_/end_coordinate`, its own
  `duration` / `distance_km` / `off_road`, and `waypoints`: a bare coordinate
  list that bends *that hop's* drawn route. `legs` is **required and non-empty**,
  so a plain A → B drive is a one-leg road and there is exactly one shape to
  consume — the move `transport` already made. The road itself therefore has
  **no** `start`, `coordinate`, `waypoints` or `off_road` of its own any more
  (`validator.py`'s `ROAD_MOVED_KEYS` names each retired key and where its value
  went, since nothing reports an unknown key and it would otherwise be dropped in
  silence); the drive counts as off-road when **all** of its legs are.
  - **A junction is written once.** `models/activities.py`'s `_road_chain`
    resolves an omitted endpoint from the neighbouring leg (`start_*` ← the
    previous leg's `end_*`, `end_*` ← the next leg's `start_*`), so the first leg
    must name its own departure and the last its own arrival; a junction no leg
    names raises. Where both sides state it the **earlier** leg's `end_*` wins,
    and `_road_leg_junction` warns when the two disagree (a different name, or
    coordinates over 0.01° apart) — the losing value would otherwise vanish
    without a word. The departure *coordinate* alone stays optional: it is
    geocoded from the name, exactly as the road's own `coordinate` always was.
    Every other point of the route is plotted from its coordinate, which is what
    a hand-written waypoint always demanded anyway.
  - **It lowers onto the old chain, which is why nothing rendered differently.**
    `_road_chain` returns `(start, coordinate, waypoints, off_road)` — each leg
    contributing its shaping points as unnamed `Waypoint`s, then its arrival as a
    named one carrying that leg's figures — so `Road`, `serialize.py`, the
    resolved `Day`, both renderers, the maps and the `.ics` are all untouched.
    The *input* moved; the rendering contract didn't, so `france.json`'s resolved
    document is byte-identical and **`SCHEMA_VERSION` needs no bump**. The
    display legs the renderers compute (`pdf/days.py`'s `road_display_legs`,
    `render/nav.ts`'s `roadLegs`) now line up one-to-one with the written legs,
    since every leg's arrival is named — the merge-forward rule survives for the
    shaping points, which is where it always mattered.
  - The validator has its own table (`ROAD_LEG_SPECS`) and `_road_leg_specs`
    tailors it per leg: an endpoint the neighbour supplies is optional (its
    `default` naming *which* neighbour), one nobody supplies is `required` — so a
    broken junction is a single error on the earlier leg's `end_*`, and the later
    leg's `start_*` is dropped from its table rather than reported a second time.
    Per-leg `duration`/`distance_km` still warn when missing, with the wording
    unchanged (`skills/fix-missing-duration-distance.md` matches on it), and a
    one-leg drive may state either on the road instead — the drive *is* that hop.
  - The Edit tab mirrors the shape: `ROAD_LEG_FIELDS` plus a **Legs** sub-array
    with two `CoordinateField`s per leg and a nested **Route waypoints** array of
    bare coordinates; the road itself no longer draws a coordinate box. `geocode`
    now fills **every** leg endpoint (`maps/writeback.py`) — something the old
    shape couldn't do for a waypoint, since its coordinate was required up front.
  - **A drive can pin its own points** — `display_start_on_maps`,
    `display_end_on_maps`, `display_intermediate_point_on_maps`. A
    road is a *route*; these give its departure, its final arrival and its
    junctions a **numbered pin** as well, joining the day's `1..N` sequence in
    timeline order (`resolve_day` appends them where the road sits, so the
    numbers still read down the page and everything after a pinned drive shifts).
    All three on = every named point pinned, which is the whole rule. **The
    junction switch defaults on, the two ends off**: splitting a drive at a place
    is what says the place matters, and a junction has nothing else on the page
    to identify it, while the two ends are usually the activity before and after
    — already numbered, so pinning them by default would put two numbers on one
    place (that is what the `same_*_as_*_activity` pair below is for). Because
    every multi-leg drive that never mentioned the switch now pins its junctions
    and renumbers the rest of its day, that default needed a `SCHEMA_VERSION`
    bump (**v20**) — same shape, same JSON, different `map_pin`. The pin is
    keyed by object identity like every other (`DayMaps.numbers[id(obj)]`): the
    **road** object carries the departure's label — so `pin_label(road)` /
    `act.map_pin` needed no new plumbing — and each pinned waypoint carries its
    own, which is why `serialize.py`'s `_waypoint` gained `map_pin` and
    `bridge.py`'s `_stamp_pins` now walks the waypoints too. A disc sits **beside
    the name it labels**, which for a drive means *inside* the line rather than
    leading it — a road is the one activity that is two places, so with all three
    switches on a day reads

    ```
    (1) Amboise → (4) Sarlat-la-Canéda
    4h · 345 km
    VIA
    •  (1) Amboise → (2) Poitiers
    •  (2) Poitiers → (3) Limoges
    •  (3) Limoges → (4) Sarlat-la-Canéda
    ```

    A junction is one place written twice — it ends one leg and starts the next —
    so its disc appears on **both** rows and the numbers chain down the list; a
    row's departure pin is the previous row's arrival pin, the first one's being
    the road's own (`pin_label(road)` / `act.map_pin`). Bunching the discs at the
    front of a line was the old shape and read as several labels on one place.
    Drawing a disc mid-line is what `pdf/day_map.py`'s `_route_with_pins` (+
    `_route_width`, which has to measure the whole line *before* the first disc
    goes down) and `days.py`'s `_road_title` exist for: the title falls back to
    the plain one-disc `multi_cell` for anything that isn't a drive with a pinned
    named arrival, and for a route too long for one line — a disc can't be drawn
    mid-wrap. The viewer's twins are `ActivityTitle` and `RoadVia` plus the
    `pin-disc-mid` class (`.act-title` is a flex row, so the space at the end of
    `"Amboise → "` is collapsed and the margin is all that's left). This is also
    what lets a **one-leg** drive print **no VIA row at all** (`_road_waypoints`
    / `RoadVia` both switch on `len(legs) > 1`, full stop): the drive *is* that
    hop, so the title carries the route, the figures, the Navigate link *and*
    the arrival's disc against its own name. A pinned arrival used to earn a row
    — the title bunched its discs at the front then, so the number sat against
    the wrong town — and the row was pure duplication once the discs moved
    mid-line. `show_on_map: false` still suppresses a pin.
    **None of these three pins reach the whole-trip map**, in either renderer.
    A pin there carries the **day**, not the stop, and the drive is drawn as a
    route — so its departure, its junctions and its arrival would only stack
    more copies of that same day number along the line it is already drawn as,
    and `display_intermediate_point_on_maps` being on by default meant every
    multi-leg drive contributed several. The two paths that had to learn it are
    `maps/build.py`'s `resolve_trip` (which filters `_Pt.from_road`, a flag
    `resolve_day` sets on exactly the points this bullet is about) and
    `tripGeo.ts`, both of whose sources drew them: its `modelPoints` fallback
    walked a road's named waypoints explicitly, and its `day.map.geo` branch
    took the day map's points wholesale, which is why `bridge.py`'s `_day_geo`
    now marks a point `from_road` for it to skip — a folded pin group counts as
    a drive's only when **every** member is, since a junction that keys alike to
    a real stop within a kilometre *is* that stop. The *day* map is unchanged:
    there a numbered junction is what identifies it. Since `map.geo.points`
    gains a field, this needed a `SCHEMA_VERSION` bump (**v26**).
  - **A drive can share an end with the activity beside it** —
    `same_start_as_previous_activity` / `same_end_as_next_activity`, both
    **off**. Most drives on a day leave where the last activity left you and
    arrive where the next one starts; these say so, and do **two independent
    things**:
    - **They fill the endpoint in.** The one endpoint the leg chain can't
      deduce — the first leg's `start_*`, the last leg's `end_*` — may be left
      blank and is taken from that activity's place name and `coordinate`. Only a
      *fallback*: an endpoint you write yourself wins, so the drive can end at
      "Amboise — car park" while the visit is "Château d'Amboise".
    - **They share the map pin.** That end never takes a number of its own,
      whatever `display_start_on_maps` / `display_end_on_maps` say — it wears the
      neighbour's, on the map and in the day's itinerary alike. One place, one
      number. This is the half worth having even with the endpoint spelled out,
      and it is what the user asked for in those words; the validator turns the
      now-redundant `display_*` switch into an **info** rather than dropping it.

    Only `Day.from_dict` can settle this — `Road.from_dict` sees one activity —
    so `models/activities.py`'s `resolve_shared_road_endpoints(activities)` runs
    there, **before** `schedule_activities`, so "the next activity" is still the
    one the JSON wrote next rather than an inserted buffer. `_road_chain` gained
    `borrow_start`/`borrow_end` purely to stop raising on the blank endpoint, and
    `Waypoint.coordinate` is typed optional for that one transient state (the
    pending arrival, filled in before the day is observable). Buffers are
    **skipped** when looking for the neighbour: free time is a length, not a
    place, so `[museum, 45 min buffer, drive]` departs from the museum. Roads are
    settled left to right, so one drive can hand its arrival to the next drive's
    departure; two pointing at each other resolve to nothing and raise, which is
    the honest answer. Three things raise, all of them reported by the validator
    too (`_road_shared_endpoints` → `_shared_start`/`_shared_end`): no
    neighbouring activity at all (the drive is first or last in the day), one
    that names no place, and — for an arrival — one with no `coordinate`, since a
    drive's arrival is a point on the drawn route.
    - **No renderer changed, in either language.** The pin is aliased at
      *lookup* time: `maps/build.py`'s `pin_aliases(day)` maps `id(road)` →
      the previous activity and `id(waypoints[-1])` → the next one, `DayMaps`
      carries it, and `number_for` falls through to it (the target is numbered
      later in the same pass, so a copied value would be empty). Those are the
      **same two objects** the pins always hung off — the road carries its
      departure's label, the last waypoint its arrival's — so `pin_label` /
      `_stamp_pins` → `map_pin` → `ActivityTitle` / `RoadVia` all work
      untouched. `resolve_day` and `Road.pinned_waypoints` just stop emitting a
      pin of their own there.
    - **No `SCHEMA_VERSION` bump.** The resolved doc gains no field (the flags
      are *input*, consumed by the model; the Edit tab reads them from
      `source.ts`) and a road without them resolves byte-identically, so a
      cached day can't be masking anything.
    - The validator needs raw-JSON twins of the model's accessors —
      `_raw_place_name` / `_raw_place_coord` beside `_place_name` /
      `_place_coord`, **keep the pairs in step**. Two traps they exist for: a
      *road* neighbour is two places (its start side is its first leg's
      departure, its end side its last leg's arrival), and a road carries no
      `coordinate` of its own any more, so reading that key for every type would
      report every drive as unlocated.
    - `examples/france.json` exercises both halves: *Renaissance châteaux* drops
      the last leg's `end_location`/`end_coordinate` entirely (the next activity
      *is* Château de Chambord — the duplication the flag exists to remove), and
      *Castles & caves* keeps `Beynac-et-Cazenac` written out and takes only the
      pin. `broken.json`'s last day carries every error and both infos.
  - **A leg may carry a `gpx`** — stored exactly like a hike's (base64, gzip
    tolerated, `models/gpx.py`) but used for one thing only: `maps/build.py`'s
    `_road_route` draws **that leg** from the recording instead of routing it, so
    a road with no GPX draws precisely the line it always did while one with a
    track follows the road actually taken. Deliberately **not** a hike: no trail
    map, no elevation profile, so an elevation-less file loses nothing and
    `defaults.include_hike_maps` (hikes only) doesn't gate it — attaching the
    file is the opt-in, and with maps off it draws nothing (an info says so). The
    resolved waypoint therefore carries a bare `gpx` string rather than a hike's
    `track` object: there is no geometry to ship, because the *map render* is
    where the line lives. The viewer alone offers it back — `GpxDownload` (the
    hike's button, generalized to a base64 + a filename) on the leg's row — the
    same paper-can't-download divergence.
    - **A one-leg drive draws no VIA row, so its GPX links are promoted to the
      road's own chips line** — beside `(Navigate)`, exactly where a hike's
      `(Get GPX track)` sits. Without that they were simply absent for the
      commonest road there is: the links hang off the leg, and a plain A → B
      drive has no leg row to hang them on (the same reasoning that promotes a
      single leg's `off_road` to the road's chip). `ActivityDetails` promotes on
      `legs.length === 1` — the same condition `RoadVia` returns null on, so the
      two can't both draw the link or both drop it. No PDF twin, as above.
  - **A leg with no recording can have one built on demand.** The other link on
    that row, `(Build GPX file)` (`GpxBuildLink`) — deliberately worded apart
    from `(Get GPX track)`, since this file didn't exist until the click — asks
    the engine for the leg's drawn geometry and downloads it. The chain is
    `RouteGpxContext` (provided by `App.tsx`, bound to the text the preview was
    resolved from, mirroring the Edit tab's geocode context) → `buildLegGpx` →
    the `legGpx` op → `bridge.leg_gpx` → `maps/build.py`'s `road_leg_geometry` +
    `models/gpx_export.py`'s `route_gpx`. Both GPX buttons are styled as the
    inline links they sit among (`.link .gpx-link`, weight 600), so the VIA row's
    Navigate uses the shared `NavLink` (`.link .nav-inline`, and the `(Navigate)`
    parentheses the rest of the book prints) rather than a bare `.link` of its
    own — otherwise the row's three links came out in two different weights and
    only two of the three were parenthesized. Three things are load-bearing:
    - **A `<rte>`, not a `<trk>`.** The geometry was computed, so writing it as a
      track would hand a GPS a recording that never happened —
      `models/gpx_export.py` exists to keep that distinction (and is where the
      README's whole-trip GPX/KML export should grow from, rather than a second
      writer).
    - **No straight-line fallback.** `route(..., fallback=False)` and
      `road_leg_geometry(..., fallback=False)` return `None` where the drawing
      path would draw `[a, b]`: a crow-flight line is fine to *draw* and wrong to
      *export*, so the link reports "no route" instead. Nothing is stored either
      way, which is why the file's own `gpx` stays "user-provided only".
    - **The leg is addressed as "the Nth road of day D, hop M"**, not by an index
      into the resolved timeline — that has buffers woven through it, so its
      activity numbers don't match the input's, while a day's roads do (hence
      `roadOrdinals` in `DayCard`).
  - Both of those change the resolved `Day`, hence the `SCHEMA_VERSION` bump to
    **18**.
- **Transport is a booking plus its `legs`.** What is reserved once — `type`,
  `name`, `booking_number`, `booking_source`, `website`, `booking_link`,
  `status`, `description`, `price`/`currency`/`paid` — sits on the `Transport`;
  what moves once — the places, dates, times, `flight_number`/`train_number`,
  `distance_km`, its
  own `description`, the endpoint coordinates — sits on each `TransportLeg`. `legs` is **required and
  non-empty**, so a single-hop booking is a one-leg booking and there is exactly
  one shape to consume. A round trip, or a flight with a connection, is finally
  the one thing it is: one PNR, one price, one cancellation link, several
  movements (`examples/france.json` is the multi-leg example — one 3-leg
  `AF77-QWLM`; `pyrenees.json` keeps three one-leg bookings, so both paths stay
  rendered).
  - **A leg answers for its booking.** `TransportLeg` proxies the shared fields
    to its parent (`models/transport.py`), and `serialize.py`'s `_transport_leg`
    *copies* them into the resolved leg (plus `leg_index`/`leg_count`), so a day's
    row, the stay bar, a map line and a calendar event each get a self-contained
    object — the same trick as `_car_event` copying its rental's note. That is
    why `Day.transports` is a list of **legs** while the top-level `transports`
    is a list of **bookings** holding theirs (`web/src/types/resolved.ts` mirrors
    both as `TransportLeg` / `Transport`), and why the resolved-`Day` change
    needed a `SCHEMA_VERSION` bump (v17).
  - **The booking's `name` and `description` are the two fields that are *not*
    copied onto the legs.** `name` is the card's heading, defaulting to
    `route_chain` — every place the booking touches in travel order, a connection
    named once but a break kept (`Transport.title` resolves the two). The
    `description` is about the reservation (a baggage allowance, a fare
    condition) while a leg's is about that hop (a seat, a terminal): both levels
    have one, they answer different questions, and each renderer draws each where
    its object is drawn — so `validate/validator.py` must exclude `description`
    from **both** `BOOKING_ONLY_KEYS` and `LEG_ONLY_KEYS` (it derives the sets by
    subtracting their intersection; a field on both levels can't be "misplaced").
    The `.ics` packs the booking's onto every one of its leg events as
    `Booking note`, kept apart from the leg's own `Description`.
  - **`price` stays the booking's.** It is copied onto the leg for completeness
    but covers *every* leg, so nothing may draw it per leg: only the transport
    page (once, on the booking) and the `.ics` do — and the ICS labels it
    `Price (whole booking)` as soon as `leg_count > 1`.
  - **Both renderers draw the card in one of two shapes**, and the pair must
    stay in step (`pdf/transport.py` / `TransportList.tsx`):
    - **several legs** — everything the reservation covers (name, type badge,
      status/payment pills, `Ref …  ·  Booked via …`, the booking note, the
      price, the links), then a **rule**, then one **inset** block per leg,
      hairline separated, each carrying a `Leg N` badge beside its route
      (`_multi_leg_transport_card` + `_leg_block` + `LEG_INDENT` + `_leg_label` /
      `LegBlock` + `.card-legs`/`.card-leg`/`.card-leg-badge`). Every rule here
      is **grey**, not accent: the accent marks emphasis (badges, times, links),
      so using it for structure made the boundary shout. The badge's label is one
      template in two places — `"Leg {n}"` in `translations.py` and the `leg` key
      in `render/format.ts` — so keep the wordings in step. The identity line is
      split to match — the flight/train number under each route (`_leg_number`),
      the reference once above (`_booking_ref`) — so `Ref …` isn't repeated.
    - **one leg** — flat: no rule, no inset, no badge, and the leg's route line
      is **dropped when it equals the heading** (`_flat_transport_card` /
      `FlatBooking`), so an unnamed one-leg booking prints its route once and the
      heading carries the Navigate link. The two halves of the identity line are
      joined again here (there's only one leg to attribute them to).
    A **day row** has no booking around it either, so `_transport_booking` there
    joins both halves too.
  - **The validator has two tables** (`TRANSPORT_SPECS` / `TRANSPORT_LEG_SPECS`)
    and walks `transport.i.legs.j`. Since nothing reports an unknown key, a field
    written on the wrong side would be silently dropped — so
    `_misplaced_transport_fields` compares the two key sets (derived from the
    tables themselves) and names the level it belongs on. The coherence checks
    all work on legs, via the `_all_legs` generator.
- **Enums** (case-insensitive, validated in the model — the tuples in `models/`
  are the source of truth, so check them rather than this list): PoI `category`
  (museum/church/building/viewpoint/ruins/castle/temple/street/natural park/
  mountain/mountain pass/lake/beach/waterfall/canyon/spring/market/other,
  default `other` — the last four were added for trips where they are the
  point, and `mountain pass` is the longest label that still fits the badge's
  14-character clip whole, which `tests/test_activity_extras.py` pins); hike `route`
  (loop/back_and_forth/one_way, default back_and_forth);
  transport `type` (plane/train/bus/taxi/ferry/other, default other); accommodation
  `type` (hotel/camping/b&b/other, default hotel); car rental `car_type`
  (regular/small/suv/4x4, default regular). Transport, accommodation and
  car rental all share a tri-state `paid` (paid/to-pay/unset), an optional
  `status` (booked/confirmed) and an optional `description` (see below). Meal
  `meal_type` (breakfast/lunch/dinner/brunch/
  snack/picnic/meal) is optional; when omitted the resolved `category` is
  inferred from the start time, but only ever as breakfast/lunch/dinner (the
  other four are explicit-only). The
  inference thresholds and a default meal duration live in `defaults`
  (`breakfast_until` 10:00, `lunch_until` 16:00, `meal_duration` 0).
- **A booking's `description`.** A transport **leg**, an accommodation and a car
  rental each carry an optional free-text `description` — a *short note* for
  whatever their structured fields don't (a seat, a door code, a fuel policy).
  On transport it sits on the leg, not the booking: an outbound and a return
  rarely share a seat. Plain text, no
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
- **An activity's `detour`.** An optional boolean (default false) on every
  activity but a `buffer` (a buffer *is* time), marking a stop you probably
  **won't** make but want the book to carry anyway. Parsed in
  `models/activities.py`'s `_sched`, so it lands on the `Activity` base and every
  type gets it, nested ones included.
  - **It is kept beside the day rather than on it.** `resolve_detours` (run from
    `Day.from_dict`, *before* the timeline pass, because it also reaches nested
    activities — which are never scheduled) folds a stated `start_time`/
    `end_time` pair into the `duration` and then **clears both times**;
    `schedule_activities` pulls the detours out of the list, lays the rest out
    untouched, and `_splice_detours` puts each one back after the activity it
    followed (ahead of any buffer there, which belongs to the two scheduled stops
    it separates). So a detour costs **0 minutes and no buffer**, and nothing
    after it moves. Clearing the times in the model rather than hiding them per
    renderer is what makes "a detour has no clock time" true in one place for all
    five consumers (both books, the `.ics`, the validator's opening-hours check,
    the forecast planner) — the last three already skip a timeless item, so they
    needed **no code change at all**.
  - **A detour still sorts where it was written.** Both merges key an activity
    with no start time to the *last one seen* rather than to `None`
    (`pdf/days.py`'s `_day_items`, `DayCard.tsx`'s `mergeTimeline`) — sorting on
    its own missing time would sweep every detour to the head of the day. Keep
    the two in step.
  - **Marked, and a step down in emphasis** — the two things asked for. Both
    renderers put the mark **under the row's type badge, in the badge's own
    column** — which for a top-level row is the gutter, *where the absent start
    time would be*: the one slot that is empty precisely because it's a detour.
    It is deliberately not ahead of the title, which is where the PDF used to
    put it — a heading that opens with a pill buries the name of the place. The
    PDF draws it with `pdf/base.py`'s `_detour_tag`, an outline pill filling the
    column and returning its height, and greys the
    title plus the gutter/nested type badge (`_badge(muted=…)` /
    `_nested_badge(muted=…)`). The viewer's twin is `.t-detour` in the gutter
    plus `.act.detour` dimming the row.
    - **The label is one word — `DETOUR` / `DÉTOUR`** (`Detour` / `Détour` in
      the viewer, which uppercases in CSS). It was `OPTIONAL DETOUR`, which
      wanted 27.6 mm at 6.5 pt (French `DÉTOUR OPTIONNEL` 29.3) against the
      gutter's 23 mm, so it had to set over two lines. "Optional" was also
      saying what the row already says: it's dimmed, and it has no clock time.
      `_detour_tag` still **wraps** greedily on spaces rather than drawing one
      `cell`, because a badge column is narrow and this is the kind of label
      that grows in translation — hence the returned height.
    - **A nested row marks itself the same way**, under its own compact badge.
      Two things make that work. `_render_nested` widens the group's shared
      `badge_w` to `_detour_min_width()` (~16 mm) when *any* of the
      group is a detour — the group's width, not the detour's, because the
      badges have to keep lining up and a pill narrower than the badge above it
      wouldn't read as one block. And `_detour_floor` holds the cursor at the
      pill's bottom edge: a row can be shorter than its own badge column (a
      nested title plus one meta line is 9.5 mm, a meal row not much more) and
      the pill would overhang what follows. Guarded on `page_no()`, like
      `_activity`'s floor, and passed the *measured* bottom so a wrapped label
      is accounted for.

    Grey, never accent: the accent is what this book uses for
    emphasis, and this is the opposite. The **title and the description share
    that one grey**, so the row reads as a single de-emphasized block rather
    than a grey heading over black prose — free in the PDF (every description is
    already `MUTED`), an explicit `.act.detour … .desc` rule in the viewer,
    where `.desc` inherits `--fg`. The wordings are the usual pair
    (`"DETOUR"` in `translations.py`, the `detour` key in
    `render/format.ts` — uppercased by CSS there, so both read alike).
  - **It keeps its map pin** (still a place you may end up at, so it stays on the
    day map, numbered like any other located stop) but is **never a cover
    highlight** (`_day_highlights` / `highlightsOf` skip it — the cover
    advertises the day, and this isn't part of what it promises) and never a
    calendar event.
  - The validator adds `detour` to `SCHEDULE` (so `PLACE_SCHEDULE` inherits it)
    plus `_detour_coherence`, which reports a clock time written on a detour
    where the ignored value sits — nothing else would say it went. Its two other
    halves are `_nested_duration` / `_nested_duration_fit`, which had to start
    skipping nested detours to stay in step with `nested_duration_total`: a
    detour isn't competing for its container's minutes.
  - Because a day's whole timeline moves (and gains a flag), this needed a
    `SCHEMA_VERSION` bump (**v22**). `examples/france.json` /`france_fr.json`
    carry one of each — a top-level `La Roque Saint-Christophe` on day 6 and a
    nested `Musée de Cluny` in the Latin Quarter — `broken.json` carries the
    invalid value and both coherence wordings, and `tests/test_detour.py` covers
    the rest.
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
  real French holiday, so flagging one would contradict that skill guidance. `broken.json` carries an invalid value for the
  validator's `V_BOOL`, and `tests/test_bank_holiday.py` covers the rest.
- **The `misc` group and its `emergency_contacts`.** A third top-level config
  group for trip-wide reference data that belongs to no point on the timeline —
  so it has nowhere to live among the days, bookings or stays. It holds one list
  so far: `emergency_contacts`, each `{name, contact}`. Deliberately a **group,
  not a bare top-level array**, so the next such list has an obvious home
  instead of becoming a fifth content array beside `days`; and read from its own
  object only (see the JSON-shape bullet). **Everything in it is optional,
  including both halves of a contact** — `contact` is free text, *never parsed*
  (emergency numbering is local: `112`, `15`, `999`, `+996 312 …`, and an entry
  may hold an email or an address instead), and a half-filled entry renders as
  the half it has. That is the point rather than laxness: the whole feature
  hangs on *leaving an unknown number out being better than inventing one*, so
  failing the build over a missing half would push the user to fabricate. The
  validator carries the burden instead — `warn_if_missing` on both fields, plus
  a warning on an entry with neither (the model drops those, so it would
  otherwise vanish silently). Both renderers draw the same list and must stay in
  step (`pdf/misc.py` / `web/src/render/EmergencyContacts.tsx`): the PDF gives it
  the **book's last page** with a *Jump to → Emergency* shortcut on the cover
  (`cover.py`'s `_cover_section_links`), the viewer closes the **🗺️ Overview**
  tab with it (`Book.tsx`'s `show === "overview"` branch, `.emergency` in
  `index.css`). One deliberate divergence, of the same kind as the hike's
  `(Get GPX track)`: the viewer sniffs a dialable/mailable `contact` and wraps it
  in a `tel:`/`mailto:` link, which paper has no twin for. **Not in the `.ics`** —
  a phone number is not an event. `stitch` reads it from a `misc.json` fragment
  (`_OBJECT_SECTIONS`, shared with `defaults.json`, plus a `misc` fragment kind
  in `validate/validator.py`), the Edit tab from a **Misc** section
  (`MiscForm` in `edit/forms/ConfigForms.tsx`). The resolved doc carries it
  flattened at the top level (`emergency_contacts`), *not* on a `Day` — so this
  needed **no `SCHEMA_VERSION` bump**: the IndexedDB cache stores days only.
  `skills/build-full-json.md` makes this the second field an LLM may look up
  online (after `bank_holiday`) — and the first that must be **cited**: every
  value taken from the web is listed in the inconsistency report with its source
  URL.
- **A point of interest's opening days & hours.** Two optional strings on
  `point_of_interest` alone — `opening_days` (`tue-sun` / `mon-fri, sun`; single
  days and/or ranges, English names or 3-letter prefixes, a range may wrap the
  week) and `opening_hours` (`09:30-18:00` / `09:30-12:30, 14:00-18:00`; a close
  before its open crosses midnight). Deliberately **compact strings, not
  objects**: a guidebook line ("Tue–Sun 9.30–12.30 & 2–6pm") transcribes as it
  stands, and the Edit tab needs two text inputs.
  - **The hours may differ by weekday**, as `;`-separated groups each optionally
    prefixed with its days — `mon-sat 09:00-17:00; sun 10:00-17:00`, which is
    the shape a museum with different Sunday hours actually has and the one
    thing the single pair could not express. Staying inside the *same string*
    is what keeps the compact-string decision above intact; no separator is
    needed between the days and the times because a day spec never holds a
    digit and a time range always opens with one (`_FIRST_DIGIT` is the seam).
    A group naming **no** days is the default for every day the others don't,
    so `09:00-17:00; fri 09:00-21:45` is the Louvre. Two groups naming the same
    day, or two day-less groups, **raise**: either leaves a day ambiguous, and
    there is no honest way to pick. When `opening_days` is absent but the hours
    name weekdays, those *become* the open days — writing `mon-fri 09:00-17:00`
    alone means shut at the weekend — while a default group leaves the set
    empty, since it claims no day in particular.
  - So `Opening` carries `days` + a tuple of `OpeningRule`s rather than one
    `hours`, plus `per_day` (any rule names days) which is what picks between
    the renderers' **two line shapes**: without it `Open  Tue–Sun · 09:30–18:00`,
    with it one part per rule, `Open  Mon–Sat 09:00–17:00 · Sun 10:00–17:00` —
    the overall day run says nothing about which hours belong to which day.
    `hours`/`hours_display` survive as the union, so `if opening.hours` still
    reads as "some hours are stated"; `hours_on(day)` / `hours_display_on(day)`
    pick the day's rule, and **`covers()` gained an `on=` date** so a Sunday
    visit is checked against the Sunday hours and the validator's warning quotes
    those rather than the union. `on=None` falls back to every range on purpose:
    a caller with no date must not report a Sunday visit as outside the weekday
    hours. A plain single-group value parses to exactly one day-less rule, which
    is what makes every file written before this render identically.
  `models/opening.py` reduces
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
- **An activity's `price`/`currency` and `contact`.** What the stop costs and
  who to call, parsed in `_sched` so they land on the `Activity` base and
  **every type but a `buffer`** has them — a fee is a fee whether it buys a
  museum, a guided walk or a dinner, and a restaurant's phone number is as
  worth having as a monument's. Same shape as a booking's price (a bare amount
  plus an optional ISO code defaulting to `defaults.currency`, validated
  against the declared set by the *same* `_check_price_currency`, now called
  from `_activity` and `_nested_activities` too).
  - **`0` is meaningful and prints as `Free`.** A guidebook that says entry
    costs nothing is telling you something an omitted price is not, so zero
    survives everywhere: `price_inline` / `priceInline` render it as the word,
    the `.ics` packs `Price: Free`, and `edit/serialize.ts`'s `SAFE_DEFAULTS`
    deliberately **omits** `price` so save-time pruning can't turn "we checked,
    it's free" back into "nobody knows" (there is a comment there saying so).
  - **There is no `paid`**, unlike the three booked objects: a fee at the gate
    has nothing to settle in advance, and a pre-paid ticket with a reference is
    a booking. That also keeps this to "a figure and a phone number" rather
    than dragging in the status/payment pill machinery.
  - **`contact` is free text, never parsed** — the same call as
    `misc.emergency_contacts`, and for the same reason: numbering is local and
    half of these are instructions rather than numbers ("call the guardian to
    open the museum" is the case the field exists for). Both renderers give it
    its own labelled row under the details — `_contact_line` / `_label_row`,
    which `_opening_line` now shares, and `.act-contact` — with the usual
    paper-can't-do-it divergence: the viewer wraps a dialable/mailable value in
    a `tel:`/`mailto:` link, reusing `EmergencyContacts.tsx`'s `DIALABLE` /
    `MAILABLE` rules (keep the two in step).
  - The price sits **inline at the end of the meta line** rather than in a bold
    row of its own: `2h30 · Rue de Rivoli · €22 ($23.76, £18.70)`. A booking's
    price is a headline; a stop's is one figure among the duration and the
    address.
  - `examples/france.json` already carried seven `price` values that the model
    was silently dropping — the Louvre's 22, the Eiffel Tower's 29.4, and so on
    — so this activated data the flagship example had been asking for. Notre-Dame
    now states `price: 0` (it really is free) and day 6's two paying sights carry
    a contact each, one email and one number, so both viewer link paths are
    visible in the demo.
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
- **Distances and climbs are rounded for *display* only.** Both are estimates —
  a distance is routed or copied off a guidebook, an ascent is accumulated from
  a GPS altimeter — and the precision a reader can use falls off with the
  magnitude, so the step coarsens as the number grows: a **distance** to 0.1 km
  below 10 km, to 0.5 km up to and including 20 km, to whole km above; a
  **climb** to 5 m below 100 m and to 10 m from there up. `models/parsers.py`
  holds `round_km`/`round_elevation` plus the `format_km`/`format_elevation`
  that add the unit (and return `""` for `None`, since every caller drops them
  into a `·`-joined parts list); the viewer mirrors all four in
  `render/format.ts` as `roundKm`/`roundElevation`/`fmtKm`/`fmtElevation` —
  **keep the two in step**, there is no JS test runner, so
  `tests/test_figure_rounding.py` is the contract both sides implement. It is
  **display-only**: the JSON, the model and the resolved doc keep the value as
  written, so nothing round-trips through a rounded figure and the Edit tab
  shows what the file says. Applied everywhere a figure is *printed* — a road's
  and a hike's summary line, a VIA leg's row, a hike GPX profile's `↑`/`↓` and
  total length, and the `.ics` `Distance:`/`Elevation:` details. Deliberately
  **not** applied to the profile chart's high/low marks: those are altitudes
  (axis scale), not a climb.
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
  shortens to `Lever`/`Coucher`.
  **Both renderers now open the day's *body* with it**, above the intro and
  below the bank-holiday banner (`pdf/days.py`'s `_sun_moon_line`, drawn in
  `day()`; the viewer's `.day-sun` above `.day-intro`, so there it's hidden
  while the day is collapsed). It used to close the PDF's header band, sharing
  one row with the kicker — which is why `_sun_moon_text` measured and degraded
  the phase (named → emoji → back to the stay bar). Owning a full-width row
  retired all of that: the phase is always named, in both languages.
  **With both switches on, the phase closes that same line** (`☀️ Sunrise:
  07:12, Sunset: 20:27, 🌕 Full moon`) — a second template,
  `"…, {emoji} {moon}"` / `sunTimesMoon`, filled with the *already localized*
  phase name. It then **leaves the stay bar** rather than printing twice on one
  page, in both renderers: `pdf/days.py`'s `day()` decides and passes the
  leftover to `_day_stay(day, moon=…)`, and `DayCard.tsx`'s `StayBar` shows its
  emoji only when `!day.sun`. So the bar still carries the moon when the sun
  times are off *or* unavailable (no usable reference — `france.json` day 1,
  or any undated trip).
  The two ends are located separately by `sun_for` via mirrored chains, so a day
  you change town gets both right: the **sunset** at `sun_reference` (that
  night's accommodation → the day's own **last** located stop → the nearest dated
  located stay) and the **sunrise** at `wake_reference` (the **previous** night's
  stay → the day's own **first** located stop → the nearest dated located stay).
  `_first_coordinate`/`_last_coordinate` walk nested activities and a road's
  lowered `waypoints` (its `coordinate` is the first leg's departure, its last
  waypoint the last leg's arrival). An unusable morning reference falls back to the evening's. The
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
  `examples/pyrenees.json` (valid, English — the designated **opt-out** example,
  so the paths a default-on switch would otherwise hide stay rendered:
  `auto_sized_buffer` **off** with a fixed `buffer`, and its 3-leg drive sets
  `display_intermediate_point_on_maps` **false**), `examples/pyrenees_pieces/` (the same
  trip split into per-file fragments for `stitch` — a test asserts it reassembles
  `pyrenees.json` exactly, so keep the two in sync), and `examples/broken.json`
  (exercises every validator rule). There is **one French example**
  (`france_fr.json`) and **one maps-on trip** (`france.json`) — `pyrenees_fr.json`
  and `kyrgyzstan.json` were dropped as a second copy of coverage that
  `france_fr.json` and `france.json` already give, so a format change no longer
  has to be mirrored into five valid files. Anything that needs a *dateless* or
  a *duration-less* trip therefore builds its own fixture (see
  `test_sun.py`'s `test_undated_trip_has_no_sun_times`) rather than reaching for
  an example.
  `examples/broken_validator_output.txt` is a **snapshot** compared by
  `test_validate.py`; whenever the JSON format or a message changes, regenerate it
  with `UPDATE_SNAPSHOTS=1 pytest`.
- **Re-render the example PDFs after every code change.** The rendered PDFs are
  the primary way changes get reviewed, so keep them current — they are
  gitignored (`*.pdf`) and untracked, so nothing else updates them. Rebuild them
  all (`france.json` / `france_fr.json` are maps-on via `include_maps_in_render`,
  so they need network for tiles/routes unless the cache is warm, but the build
  degrades gracefully offline):
  ```bash
  .venv/bin/odysseyra-travelBook build examples/france.json -o examples/france.pdf
  .venv/bin/odysseyra-travelBook build examples/france_fr.json --lang fr -o examples/france_fr.pdf
  .venv/bin/odysseyra-travelBook build examples/pyrenees.json -o examples/pyrenees.pdf
  .venv/bin/odysseyra-travelBook build examples/pyrenees.json --ink-saver -o examples/pyrenees_inksaver.pdf
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
  - the `file_format.md` tables (**not** the README — it only links there now);
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
- **The viewer's Python engine runs in a Web Worker**
  (`web/src/pyodide/worker.ts`), not on the main thread. Every bridge call is
  synchronous Python and a map render fetches its tiles over a *blocking* XHR
  (`netbridge.ts` — Pyodide has no sockets and sync Python can't await a JS
  promise), so in-thread a PDF build or a day's map froze the page outright,
  spinner included. The split is: `runtime.ts` the RPC client (same public API as
  before — `boot()` + one async function per op), `worker.ts` the host,
  `engine.ts` the host-agnostic Pyodide boot + `dispatch`, `protocol.ts` the typed
  message contract. **A new bridge function therefore needs an entry in
  `protocol.ts`'s `OpMap`, a `case` in `engine.ts`'s `dispatch` and a wrapper in
  `runtime.ts`** — the wrapper alone no longer reaches Python. Keep `engine.ts`
  DOM-free (`document`/`window` don't exist in a worker); it is also the
  main-thread fallback used when a Worker can't be created, which is why it is
  imported dynamically (a chunk nobody normally downloads). Long calls are now
  surfaced by the loader, `web/src/ActivityIndicator.tsx` — non-blocking by
  design (no backdrop, `pointer-events: none`), since the page stays usable.
- **The basemap is Carto's *vector* tiles, rasterized by us.** Both renderers
  now read the **same** source — `web/src/maps/carto.ts`'s
  `tiles-a.basemaps.cartocdn.com/vectortiles/carto.streets/v1/{z}/{x}/{y}.mvt`,
  the URL template MapLibre draws in the viewer — because Carto's *pre-rendered
  raster* tiles (`light_nolabels`/`light_only_labels@2x`, what `render.py` used
  to stitch) now answer keyless requests with an `API KEY REQUIRED` watermark.
  They answer with **HTTP 200 and a valid PNG**, so nothing downstream could
  detect it: `tile_bytes`'s retry/backoff was useless and the stamp simply
  appeared in the book. Two new modules do the work `render.py` used to get for
  free from the server:
  - `mvt.py` — bytes → features. A hand-rolled Mapbox-Vector-Tile reader (pure
    stdlib; `protobuf` is compiled and would have to work in Pyodide too),
    gzip-tolerant like `models/gpx.py`. The caller names the layers it wants and
    every other layer is **skipped by its length prefix without decoding a
    feature** — on a city tile the `poi`/`housenumber`/`building` layers we never
    draw are 13 of every 16 features. `ring_is_exterior` reads a polygon ring's
    winding to tell a lake from the island in it; tile coordinates run
    y-downwards, which flips the shoelace sign (get it backwards and every lake
    renders as a hole).
  - `basemap.py` — features → image, plus the labels as **data**. Colours and
    per-zoom widths are lifted from `positron-gl-style/style.json`, so it reads
    as the same basemap, but it is a **deliberate subset**: ~15 rules against
    Positron's 93 layers, no bridge/tunnel distinction, no POIs, and no road
    names (clutter at a few centimetres wide). Building footprints *are* drawn,
    but only from `BUILDING_MIN_ZOOM` (14) — an **area** zoom map is a few city
    blocks, where a footprint is what you navigate by, while on a day map it
    would be a grey smear. `width_at`'s first stop
    doubles as the layer's minzoom, which is what keeps a z6 country map to
    motorways. `render_basemap` returns `(image, labels)` and draws no text
    itself.
  Three things got **better**, not merely restored: a map costs **one** tile
  fetch instead of two (the old base + labels-only sandwich); labels are drawn
  last by `render.py`'s `_draw_labels`, so a place name is **dropped where a pin
  or the attribution already sits** (the raster label tile was composited over
  our pins regardless, so a numbered pin could sit on the town it marked) and
  where it would be clipped at the edge; and because the label is data, places
  are named in the **book's** language (`name:{lang}` → `name:latin` → `name`,
  plumbed as `lang` through `render_map`/`render_day_maps`/`render_trip_map`/
  `render_hike_map` from the PDF mixins' `self.lang`). `state`/`province` labels
  are deliberately dropped: OSM's `name:en` for a French region is often a
  literal gloss (Bourgogne-Franche-Comté → "BURGUNDY-FREE COUNTY"). The
  viewer's `render_day` bridge call passes **no** lang on purpose — its static
  PNG then names places the way its own MapLibre map does, and the PDF it
  exports still goes through `build(lang=…)`. The source publishes to **z14**, so
  anything closer overzooms those tiles — exactly what MapLibre does, which is
  why the two stay consistent past z14. Strokes are aliased in Pillow, so the
  basemap is supersampled ×2 and reduced, dropping to ×1 past
  `MAX_SS_PIXELS` (the whole-trip page would otherwise want a 56 MB canvas).
  This changed the *rendered images* inside a cached day without changing any
  field, so it needed a `SCHEMA_VERSION` bump (**v19**) — the one case the
  itinerary hash provably cannot catch.
- **Interactive and static maps are alternatives, not a fallback chain.** With
  Options → interactive maps **on**, a viewer map slot is the MapLibre map or a
  short "couldn't be loaded" note; the pre-rendered PNG is drawn *only* with the
  toggle off (`DayCard.tsx`'s `MapView`). Substituting the PNG on a GL failure
  silently returns the rendering the user switched away from — one with no pan or
  zoom — so it reads as the map having lost its controls. A slot with nothing
  locatable stays empty either way rather than claiming a failure.
  `HikeTrack.tsx` follows the same rule now that a hike's trail has a PNG twin
  (`track.map`, above): MapLibre on, PNG off, and a GL failure shows the profile
  alone rather than the map the user turned off. `TripMap.tsx` is the one that
  stays interactive-only — the 🗺️ Overview is a whole-trip view you pan and
  zoom, and its paper twin is the PDF's trip-map page.
  The **figure** the PNG is drawn in is shared: `Parts.tsx`'s `MapFigure`, used
  by both `MapView` and `HikeTrackFigure`, so a caption/markup change can't
  drift between the two.
- **A one-line row in the PDF neither wraps nor clips.** fpdf's `cell` draws
  straight past its own width, so any single-line row carrying a value a user
  can make arbitrarily long runs off the paper — and nothing reports it, because
  the text is *there*, just past the margin. Three tools, and a rule for
  choosing between them:
  - **`_fit_text(text, w)`** (`pdf/base.py`) ellipsizes. Right only where the
    full value is readable elsewhere in the book — the stay bar's name (also on
    the accommodation page) and its address line (also its Navigate link), the
    accommodation card's name (cut to the width its right-aligned badges leave).
    A row that would *lose* information must wrap or drop a whole part instead;
    the stay bar's sub line does both, dropping `·`-separated parts first and
    only ellipsizing what's left when one part is itself too long.
  - **`_route_with_pins(…, max_w=, indent=)`** (`pdf/day_map.py`) breaks a route
    **between its ends**, after the arrow, so each name keeps its own pin disc —
    which wrapping it as prose would lose (that is why `_road_title` declines
    the job and falls back to a plain one-disc `multi_cell` instead). This is
    what lets a VIA row take two lines: `_road_waypoints` measures the route and
    its tail (figures + `OFF-ROAD` pill + Navigate) **before drawing anything**,
    since the row's height decides whether it starts on this page, and lays them
    out by the same greedy per-end rule the drawing uses so the two agree.
  - **Measure each piece under the font it is drawn in.** `_inline_chip_width`
    (and `_pin_disc`, and `_route_width`) *set* the font, so chaining
    measurements in one expression silently measures later pieces in an earlier
    piece's font — a Navigate link measured in the chip's 6 pt bold reads ~30 %
    narrow, i.e. a row that overflows while claiming to fit.
  The viewer needs none of this: CSS reflows, so its twins (`RoadVia`,
  `.stay-note`, `Clamp`) wrap or clamp on their own.
- **A label the PDF passes through `self.t()` needs a viewer twin.** The gutter
  type badge is the case that got away: `pdf/days.py`'s `_badge_label`
  localizes `ROAD`/`HIKE`/`MEAL`/`PLACE`/`POINT` and a POI's `category` through
  `translations.py`, while `DayCard.tsx`'s `badgeLabel` returned hardcoded
  English — so a French book printed `RANDO` and the viewer showed `HIKE`. Both
  sides now read label keys (`badge*` / `cat*` in `render/format.ts`, plus
  `catLabel` mirroring `POI_CATEGORIES`); the viewer uppercases in CSS
  (`text-transform` on `.type-badge`) where the PDF does it in code, which is
  why the keys are written in sentence case. Keep the two sets and the
  14-character category clip in step.
- **The PDF's page box is 10 mm, not the 18 mm the code reads as.**
  `_PDFBase.__init__`'s `set_margins`/`set_auto_page_break`/`set_title` sat
  **after the `return`** in `d()` for the file's whole life, so every book ever
  printed used fpdf's defaults (10 mm sides and top, a 20 mm bottom break) and
  the whole layout — the gutter, the card widths, the map height caps — was
  measured against those. The three lines now live in `__init__` at the values
  actually in force, so `set_title` finally fills the PDF's metadata title;
  moving the margins to 18 mm is a **one-line, deliberate** change that narrows
  the column by 16 mm, reflows every page and changes the page count, so it is a
  design decision rather than a bug fix and hasn't been taken.
- **`skills/`** holds LLM-facing docs:
  - `build-full-json.md` — a self-contained guide (it duplicates every field
    table, value format and rule) that turns raw text/screenshots into the
    **entire** itinerary as one `<title>.json`, needing no other file, no source
    code, and no tool. **Any JSON-format change must be mirrored here** — it is
    authoritative alongside `file_format.md`. It runs in **two modes**: from
    nothing, or — when an itinerary JSON is among the sources — **updating that
    file**, which is then the base and the source of truth (every existing key
    survives, including ones the guide doesn't document; the base's values
    outrank the model's own re-derivation; its `title` and prose language are
    kept), and the run ends with a **"Changes to the JSON"** recap listing every
    field added, changed (`old → new`), newly-created object and migrated stale
    key. That last part is why the retired aliases matter here: a base written
    against the old shape (a `road` with its own `start`/`waypoints`, a
    `transport` with a `date` and no `legs`, `default_*`…) has to be migrated to
    build at all, and that is the one change the guide makes without a source
    asking for it.
  - `fix-missing-duration-distance.md` — from a JSON + a list of validator
    warnings about missing duration/distance/elevation, builds a fill-in-the-blank
    Markdown worksheet (Google Maps links for road distances; web-inferred hike
    figures tagged `[to be checked]`). If the magnitude-warning messages change,
    update its warning-patterns table.
- **`file_format.md`** (repo root) documents the JSON schema field-by-field (one
  table per object, with Required/Type/Format/Default) — keep it authoritative.
  It used to be the README's `## JSON format` section, which grew to two thirds
  of the file; the README now keeps a short pointer section linking each object's
  table, so add new fields to `file_format.md` and only touch the README when a
  whole *object* or top-level section appears. Anchors are unchanged by the move
  (GitHub slugs on heading text, not level), so old `#field` links still work —
  but they now need a `file_format.md` prefix from any other file.
