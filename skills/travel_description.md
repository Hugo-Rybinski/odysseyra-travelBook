# Skill: `travel_description.json`

**Target file:** `<ROOT>/travel_description.json` (a **single** file, not indexed)

The cover of the trip: its title, an optional subtitle and summary, an accent
color, and optional manual trip dates. This is the one file `create-skeleton`
pre-fills with a `"FIXME"` title — replace it.

## What to extract

From a trip name, a heading, an email subject, or a one-line brief: the trip's
**title** (required) and, if present, a **subtitle**/tagline and a **summary**
paragraph. A color or manual dates are rarely stated — omit them unless the
source clearly gives them.

## Value formats

Write each kind of value exactly like this:

| Kind | Write it as | Examples |
|---|---|---|
| **Date** | `YYYY-MM-DD` | `2026-06-08` |
| **Hex color** | `"#RRGGBB"` or `"#RGB"` | `"#2f6b4f"` |

## Fields

| Field | Required | Format | Default | Notes |
|---|---|---|---|---|
| `title` | **yes** | text | — | Shown big on the cover. |
| `subtitle` | no | text | none | A tagline under the title. |
| `summary` | no | text | none | A short paragraph shown on the cover. |
| `cover_color` | no | hex color (`"#2f6b4f"`) | `"#1f4e5f"` (teal) | Accent color for the whole PDF. |
| `start_date` | no | date `YYYY-MM-DD` | inferred (earliest date in the trip) | Only set if the source states an explicit trip start; otherwise leave it out and let it be inferred. |
| `end_date` | no | date `YYYY-MM-DD` | inferred (latest date in the trip) | Same — omit unless explicitly given. |

> Dates are normally **inferred** from the days/transports/accommodations, so
> do not set `start_date`/`end_date` yourself unless the source explicitly
> pins the trip's span.

## Example

Source: *"Pyrenees Road Trip — a week of mountains, monasteries and long
drives. Crossing the Pyrenees from the Atlantic side toward the high peaks,
based two nights in Lourdes."*

```json
{
  "title": "Pyrenees Road Trip",
  "subtitle": "A week of mountains, monasteries and long drives",
  "cover_color": "#2f6b4f",
  "summary": "Crossing the Pyrenees from the Atlantic side toward the high peaks — mixing scenic drives, old towns, monuments and a proper mountain hike, with two nights based in Lourdes."
}
```

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
- **Trust user-supplied details.** If the user adds or corrects a value by hand,
  keep it even when it isn't in the source document — treat it as ground truth,
  not something to second-guess or overwrite.
