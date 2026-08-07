# Skill: `defaults.json`

**Target file:** `<ROOT>/defaults.json` (a **single** file, not indexed)

Trip-wide defaults that fill gaps the individual days/legs don't specify: the
day's default start time, the timezone that applies to all times, an automatic
buffer between activities, the meal-classification thresholds, and the currency
prices are given in (plus any extra currencies to convert them into).

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
| `currency` | no | 3-letter ISO code | `"EUR"` | The currency every price is in unless the price sets its own `currency`. |
| `secondary_currencies` | no | array of `{currency, change_rate}` | `[]` | Extra currencies each price is *also* shown in on the PDF (converted from the default). |
| `include_maps_in_render` | no | boolean | `false` | Draw a per-day OpenStreetMap with a pin for each located activity. |
| `infer_coordinates_from_address` | no | boolean | `false` | Geocode activities that have no explicit `coordinate`. When false, only activities with a `coordinate` appear on the map. |
| `inference_countries` | no | array of 2-letter ISO codes | `[]` (any) | Restrict geocoding to these countries, e.g. `["FR"]`. Only used when inference is on. |

### `secondary_currencies`

Each entry is `{"currency": "<ISO code>", "change_rate": <number>}`. The
`change_rate` is **units of that currency per one unit of the default currency**
— with a `EUR` default, `{"currency": "USD", "change_rate": 1.09}` means
1 € = $1.09. On the PDF every price is printed in the default currency followed
by each secondary conversion in parentheses (e.g. `€612 ($667, £520)`).

## Example

Source: *"Local time is UTC+2. Plan days from 9:00 to 19:00, leave 15 minutes
between stops, and count sit-down meals as an hour. Prices are in euros; also
show them in US dollars (1 € ≈ $1.09) and pounds (1 € ≈ £0.85)."*

```json
{
  "start_time": "09:00",
  "end_time": "19:00",
  "buffer": "15 min",
  "timezone": "+02:00",
  "meal_duration": "1h",
  "currency": "EUR",
  "secondary_currencies": [
    { "currency": "USD", "change_rate": 1.09 },
    { "currency": "GBP", "change_rate": 0.85 }
  ]
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
