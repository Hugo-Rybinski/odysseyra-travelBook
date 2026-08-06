# travelbook

Turn a JSON travel itinerary into a polished, print-ready PDF — and validate the
JSON with precise, localized, line-numbered diagnostics. Pure Python, no system
dependencies (uses `fpdf2` with a bundled DejaVu font; **no** Cairo/Pango).

## Commands

```bash
# setup
python3 -m venv .venv && source .venv/bin/activate && pip install -e ".[dev]"

# build a PDF (the "build" sub-command is optional; validation runs first,
# printing errors-only to stderr, then it builds anyway)
travelbook build examples/pyrenees.json -o out.pdf
travelbook examples/pyrenees.json -o out.pdf            # implies build
travelbook build examples/pyrenees_fr.json --lang fr -o out_fr.pdf
travelbook build examples/pyrenees.json --ink-saver -o out.pdf   # outlines, not solid fills

# validate (-v 1 errors, 2 +warnings [default], 3 +info; -l/--lang en|fr)
travelbook validate examples/pyrenees.json
travelbook validate examples/pyrenees.json -v 3 --lang fr

# scaffold an empty fragment dir (sub-folders + travel_description.json stub)
travelbook create-skeleton . mytrip

# stitch a directory of JSON fragments into one <title>.json (validates first)
travelbook stitch examples/pyrenees_pieces

pytest                                                  # all tests
UPDATE_SNAPSHOTS=1 pytest tests/test_validate.py        # regenerate the snapshot (see below)
```

Everything runs through the venv (`.venv/bin/...`); there is no `uv`. Python 3.13.

## What it produces

A PDF with: a **cover** (title, inferred date range, day count, summary, and a
day-by-day overview table), one **page per day** (colored header band, intro,
a merged time-ordered itinerary, and a bottom "tonight's stay" bar), a
**transport** page, and an **accommodation** summary page. The whole palette is
derived from one `cover_color`.

## Architecture (`src/travelbook/`)

Four focused packages; each `__init__.py` re-exports its public API, so import
paths are stable (`from travelbook.models import Itinerary`, etc.).

- **`models/`** — the data model, built from JSON via `from_dict` classmethods.
  - `parsers.py` — scalar parsers (`_parse_date/_time/_duration/_tz/_paid/_route`,
    formatters) and `ItineraryError` (raised on any invalid data).
  - `activities.py` — `Activity` base + the 6 activity types (`road`,
    `point_of_interest`, `place`, `hike`, `meal`, `buffer`), `activity_from_dict`,
    and `schedule_activities` (the day timeline pass).
  - `transport.py` — `Transport` + `resolve_transport` (tz-aware time inference).
  - `accommodation.py` — `Accommodation`.
  - `itinerary.py` — `Day` and `Itinerary` (top-level `from_dict`, date inference).
- **`validate/`** — read-only checker, never mutates.
  - `jsonpos.py` — a hand-written position-tracking JSON parser returning
    `(data, lines)` where `lines` maps a path tuple → 1-based line number.
  - `findings.py` — `Finding` (level/line/message), icons, `format_findings`.
  - `specs.py` — `Spec` field descriptors, value validators (`V_*`), spec tables.
  - `validator.py` — `_Validator` walks the data and emits findings; `validate_text`.
- **`pdf/`** — `TravelPDF(CoverMixin, DayMixin, TransportMixin, AccommodationMixin,
  _PDFBase)`. `base.py` holds fonts/colors and shared drawing primitives; each
  section is a mixin. `build_pdf(itinerary, output, lang, ink_saver)` is the entry
  point. The `ink_saver` flag (CLI `--ink-saver`) is stored on `_PDFBase` and read
  by the primitives that draw large solid accent areas — the cover banner, the
  `_band_header` page bands, `_card_bg`, `_badge`, `_pill`, `_chip` — which then
  render outlines + accent-colored text + thin rules instead of solid fills.
- **`lang/`** — localization. `dates.py` (month/weekday tables + `fmt_date`),
  `translations.py` (English→French map), `__init__` (`tr`, `LANGUAGES`).
- **`stitch.py`** — `aggregate(directory, ask=input)` assembles one itinerary
  dict from a fragment directory (`travel_description.json`, `default.json`, and
  `days/` `transports/` `accommodations/` `car-rentals/` folders — one array
  entry per JSON file, ordered by filename; alternate folder spellings accepted).
  Prompts for `travel_description` when its file is absent. `create_skeleton`
  scaffolds the reverse — an empty fragment dir (`SKELETON_DIRS` sub-folders +
  a `{"title": "FIXME"}` stub). `safe_filename` and `StitchError` round it out.
- `cli.py` — argparse CLI (`build` / `validate` / `stitch` / `create-skeleton`,
  `--lang`, `--verbose`).

## Key design decisions

- **JSON shape.** Two config groups — `travel_description` (title/summary/color,
  optional manual `start_date`/`end_date`) and `default` (`start_time` 08:00,
  `end_time`, `buffer`, `timezone` GMT, meal thresholds `breakfast_until` 10:00 /
  `lunch_until` 16:00, and `meal_duration` 0) — plus content arrays `days` (required,
  non-empty), `transport`, `accommodations`. The older flat layout still parses.
- **Inference is central.**
  - Trip `start_date`/`end_date` are inferred as the earliest/latest date across
    days, transport and accommodation — unless set manually (then they're checked).
  - A day's `date` defaults to trip-start + its index.
  - Activities chain on a timeline: first starts at `default.start_time`, each next
    at the previous end; give any two of `start_time`/`end_time`/`duration` and the
    third is inferred. Buffers (default, manual, or gap-inferred) fill gaps.
  - Transport requires `start_time`; the other of `end_time`/`duration` is inferred,
    tz-aware. An overnight leg (`start_date` given a `start_time`) becomes that
    night's "accommodation".
- **Enums** (case-insensitive, validated in the model): PoI `category`
  (museum/church/building/viewpoint/ruins/castle/temple/street/other, default
  `other`); hike `route` (loop/back_and_forth/one_way, default back_and_forth);
  transport `type` (plane/train/bus/taxi/other, default other); accommodation
  `type` (hotel/camping/b&b/other, default hotel); `status` (booked/confirmed);
  `paid`/`paid_online`. Meal `meal_type` (breakfast/lunch/dinner/brunch/snack/
  picnic/meal) is optional; when omitted it is inferred from the start time, but
  only ever as breakfast/lunch/dinner (the other four are explicit-only). The
  inference thresholds and a default meal duration live in `default`
  (`breakfast_until` 10:00, `lunch_until` 16:00, `meal_duration` 0).
- **Validation has three levels**, filtered by `--verbose`: ❌ errors (missing
  required, invalid value, incoherence), ⚠️ warnings (soft inconsistencies:
  nowhere-to-sleep, city mismatch, hike route/endpoints, ends-after-`end_time`…),
  ℹ️ info (optional field missing → states the default). Every finding carries a
  line number. Build surfaces errors-only but does not block.
- **i18n is gettext-style.** English is the source string; `tr(text, lang)` maps
  it (templates keep `{placeholders}` — translate *then* `.format`). Missing keys
  fall back to English. Dates are localized via name tables + per-language ordering.

## Conventions & gotchas

- Text is drawn with the bundled **DejaVu** TTF (`src/travelbook/fonts/`) so any
  Unicode (accents, arrows `→`, `✓`) renders. Do not switch to core fonts.
- The model raises `ItineraryError` on bad data; the validator instead reports it
  (it does its own parsing and never calls a mutating path except a guarded
  `Itinerary.from_dict` for the end-of-day check).
- **Examples are kept in sync and tested.** `examples/pyrenees.json` (valid,
  English), `examples/pyrenees_pieces/` (the same trip split into per-file
  fragments for `stitch` — a test asserts it reassembles `pyrenees.json`
  exactly, so keep the two in sync), `examples/pyrenees_fr.json` (same trip in
  French — build with `--lang fr`), `examples/broken.json` (exercises every
  validator rule).
  `examples/broken_validator_output.txt` is a **snapshot** compared by
  `test_validate.py`; whenever the JSON format or a message changes, regenerate it
  with `UPDATE_SNAPSHOTS=1 pytest`.
- **Re-render the example PDFs after every code change.** The rendered PDFs are
  the primary way changes get reviewed, so keep them current — they are
  gitignored (`*.pdf`) and untracked, so nothing else updates them. Rebuild all
  three:
  ```bash
  .venv/bin/travelbook build examples/pyrenees.json -o examples/pyrenees.pdf
  .venv/bin/travelbook build examples/pyrenees_fr.json --lang fr -o examples/pyrenees_fr.pdf
  .venv/bin/travelbook build examples/pyrenees.json --ink-saver -o examples/pyrenees_inksaver.pdf
  ```
  (macOS Preview caches an open PDF — a rebuild only shows after reopening it.)
- When adding/renaming a field or message, update: the model `from_dict`, the
  validator `specs.py` (+ any coherence check), the PDF renderer, both example
  JSONs, the README tables, the French `translations.py`, regenerate the
  snapshot, and re-render the example PDFs.
- `README.md` documents the JSON schema field-by-field (one table per object,
  with Required/Type/Format/Default) — keep it authoritative.
