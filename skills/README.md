# travelbook — JSON extraction skills

These documents teach an LLM how to turn **raw material about a trip** — pasted
text, a booking-confirmation email, a screenshot of a reservation, a hotel
website, a hand-written plan — into the small JSON files that
`travelbook stitch` assembles into a full itinerary.

## The workflow

1. Scaffold an empty fragment directory (call its root `<ROOT>`):

   ```bash
   travelbook create-skeleton <path> <name>     # <ROOT> = <path>/<name>
   ```

   This creates `<ROOT>/` with a `travel_description.json` stub (title
   `"FIXME"`) and four empty sub-folders: `days/`, `transports/`,
   `accommodations/`, `car-rentals/`.

2. For each piece of source material, write **one JSON file** into the matching
   folder, following the relevant skill below. Then run:

   ```bash
   travelbook stitch <ROOT>          # → "<title>.json", validated
   ```

## Building the whole file at once

The skills below each cover **one fragment** written into `<ROOT>/`, for the
`travelbook stitch` workflow. If instead you want to assemble the **entire
itinerary into a single JSON file** in one pass — no fragment folders, no
`stitch` — use [build-full-json.md](build-full-json.md); it is fully
self-contained (it duplicates every field table and rule from the fragment
skills, so it needs no other file, no source code, and no tool) and produces a
single `<title>.json` for the user to build/validate afterwards.

## Which skill to use

| Source material | Skill | File(s) to write |
|---|---|---|
| Trip name / theme / summary | [travel_description.md](travel_description.md) | `<ROOT>/travel_description.json` |
| Global defaults (start time, timezone…) | [defaults.md](defaults.md) | `<ROOT>/defaults.json` |
| A day's plan (what you do, in order) | [days.md](days.md) | `<ROOT>/days/day-<INDEX>.json` |
| A flight / train / bus / taxi / ferry booking | [transports.md](transports.md) | `<ROOT>/transports/transport-<INDEX>.json` |
| A hotel / lodging booking | [accommodations.md](accommodations.md) | `<ROOT>/accommodations/accommodation-<INDEX>.json` |
| A rental-car booking | [car-rentals.md](car-rentals.md) | `<ROOT>/car-rentals/car-rental-<INDEX>.json` |

`travel_description.json` and `defaults.json` are **single files**. The four
folders hold **one entry per file**; the files are read in **filename order**,
so use a zero-padded, increasing `<INDEX>` (`day-01.json`, `day-02.json`, …).
For `days/` the file order **is** the day order — number them along the trip.

## Common value formats

Every skill uses these; they are shared across all objects.

| Kind | Write it as | Examples |
|---|---|---|
| **Date** | `YYYY-MM-DD` | `2026-06-08` |
| **Time** | 24-hour `HH:MM` | `09:00`, `18:45` |
| **Duration** | `"<h>h<mm>"`, `"<h>h"`, `"<n> min"`, `"<n>m"`, `"H:MM"`, or a plain number of minutes | `"1h30"`, `"2h"`, `"45 min"`, `"90m"`, `"1:30"`, `90` |
| **Timezone (UTC offset)** | `"+HH:MM"`, `"+HHMM"`, `"UTC±H"`, `"GMT±H"`, `"Z"` (=UTC), or a plain number of hours | `"+02:00"`, `"-04:00"`, `"UTC-3"`, `"Z"`, `2` |
| **Payment flag** | `"paid"` (paid) or `"to pay"` (not yet) — omit if unknown | `"paid"`, `"to pay"` |
| **Boolean** | `true` / `false` (also `"yes"` / `"no"`) | `true` |
| **Hex color** | `"#RRGGBB"` or `"#RGB"` | `"#2f6b4f"` |
| **Price** | a bare number, no currency symbol | `89`, `256.5` |
| **Currency** | a 3-letter ISO code | `"EUR"`, `"USD"`, `"GBP"` |

## Rules that apply to every file

- **Only include a field if the source actually states it.** Never invent
  bookings, prices, dates, or times. Omitting an optional field lets the tool
  fall back to a sensible default (each skill lists them).
- Each file is standalone JSON: a single top-level **object** (a file may also
  hold a JSON **array** of such objects, in which case each element is one
  entry).
- Write dates/times exactly as the formats above; convert "6pm" → `"18:00"`,
  "June 8, 2026" → `"2026-06-08"`.
- When a value is unknown but the field is required, leave a clear
  `"FIXME"` placeholder so `travelbook validate` (run by `stitch`) flags it.
- **After writing the JSON, report the gaps.** List the optional fields you left
  empty (with a one-line note on what each would add) so the user can fill in
  anything the source didn't cover.
- **Once you're done, report the inconsistencies.** List every conflict you found
  between the source documents (a place, date, time, price, coordinate… stated
  differently in two places) and how you arbitrated each — which source you
  trusted and why.
- **Trust user-supplied details.** If the user adds or corrects a value by hand,
  keep it even when it isn't in the source document — treat it as ground truth,
  not something to second-guess or overwrite.
- **A KML/KMZ file is the principal source of truth for coordinates.** When one
  is provided, take every `coordinate` from it. If another document states
  different coordinates for the same place, trust the KML/KMZ.
