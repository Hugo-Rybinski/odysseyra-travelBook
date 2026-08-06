# Skill: `default.json`

**Target file:** `<ROOT>/default.json` (a **single** file, not indexed)

Trip-wide defaults that fill gaps the individual days/legs don't specify: the
day's default start time, the timezone that applies to all times, an automatic
buffer between activities, and the meal-classification thresholds.

This file is **entirely optional** — omit it and every field below takes its
default. Only create it when the source material implies a global setting (e.g.
"all times are local Paris time (UTC+2)" or "we start each day at 9am").

## Fields

| Field | Required | Format | Default | Notes |
|---|---|---|---|---|
| `start_time` | no | time `HH:MM` | `"08:00"` | When the first activity of each day begins if it gives no start. |
| `end_time` | no | time `HH:MM` | none | If set, `validate` warns about any activity that ends later. |
| `buffer` | no | duration (`"15 min"`) | `0` (none) | Free time auto-inserted between consecutive activities. |
| `timezone` | no | UTC offset (`"+02:00"`, `"UTC-3"`, `"Z"`) | `GMT` (UTC+0) | The default offset for every time in the trip that gives none. |
| `breakfast_until` | no | time `HH:MM` | `"10:00"` | A meal with no `meal_type` starting at/before this is a **breakfast**. |
| `lunch_until` | no | time `HH:MM` | `"16:00"` | A meal starting after breakfast and at/before this is **lunch**; later is **dinner**. |
| `meal_duration` | no | duration (`"1h"`) | `0` | Default length of a meal that gives neither a duration nor an end time. |

## Example

Source: *"Local time is UTC+2. Plan days from 9:00 to 19:00, leave 15 minutes
between stops, and count sit-down meals as an hour."*

```json
{
  "start_time": "09:00",
  "end_time": "19:00",
  "buffer": "15 min",
  "timezone": "+02:00",
  "meal_duration": "1h"
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
