# Skill: `car-rentals/car-rental-<INDEX>.json`

**Target file:** `<ROOT>/car-rentals/car-rental-<INDEX>.json` — **one file per
rental** (`car-rental-01.json`, …).

One rental-car booking, with its booking window and the pick-up / drop-off
events. This is the skill for a **car-rental confirmation** (Europcar/Hertz
email, voucher, screenshot).

## What to extract

From the confirmation: the **booking window** (start/end date+time), the
**pick-up** and **drop-off** date, time and **location**, the **company** and
**booking reference**, the **car type/model**, the **price** and payment state,
the number of **additional drivers**, and a contact.

## Value formats

Write each kind of value exactly like this:

| Kind | Write it as | Examples |
|---|---|---|
| **Date** | `YYYY-MM-DD` | `2026-06-08` |
| **Time** | 24-hour `HH:MM` | `09:00`, `18:45` |
| **Timezone (UTC offset)** | `"+HH:MM"`, `"+HHMM"`, `"UTC±H"`, `"GMT±H"`, `"Z"` (=UTC), or a plain number of hours | `"+02:00"`, `"-04:00"`, `"UTC-3"`, `"Z"`, `2` |
| **Duration** | `"<h>h<mm>"`, `"<h>h"`, `"<n> min"`, `"<n>m"`, `"H:MM"`, or a plain number of minutes | `"1h30"`, `"2h"`, `"30 min"`, `90` |
| **Price** | a bare number, no currency symbol | `89`, `256.5` |
| **Currency** | a 3-letter ISO code | `"EUR"`, `"USD"`, `"GBP"` |
| **Payment flag** | `"paid"` (paid) or `"to pay"` (not yet) — omit if unknown | `"paid"`, `"to pay"` |

## Fields

| Field | Required | Format | Default | Notes |
|---|---|---|---|---|
| `booking_start_date` | **yes** | date `YYYY-MM-DD` | — | When the booking window opens. |
| `booking_start_time` | **yes** | time `HH:MM` | — | |
| `booking_end_date` | **yes** | date `YYYY-MM-DD` | — | When it closes (must be after the start). |
| `booking_end_time` | **yes** | time `HH:MM` | — | |
| `pickup_date` | **yes** | date `YYYY-MM-DD` | — | Must fall within the booking window. |
| `pickup_time` | **yes** | time `HH:MM` | — | |
| `dropoff_date` | **yes** | date `YYYY-MM-DD` | — | Within the window and **after** the pick-up. |
| `dropoff_time` | **yes** | time `HH:MM` | — | |
| `pickup_location` | **yes** | text | — | Where you collect the car. |
| `dropoff_location` | no | text | same as pick-up | Set it if you return elsewhere. |
| `booking_start_tz` / `booking_end_tz` / `pickup_tz` / `dropoff_tz` | no | UTC offset | trip default timezone | Only if different from the trip's timezone. |
| `company` | no | text | none | e.g. "Europcar". |
| `booking_number` | no | text | none | Reservation reference. |
| `website` | no | a link like `https://example.com` | none | The rental company's website — shown as a clickable link. |
| `booking_link` | no | a link like `https://example.com` | none | A direct link to this reservation — shown as a clickable link. |
| `status` | no | `booked` / `confirmed` | none (no badge) | Reservation status. |
| `price` | no | number | none | The amount only, e.g. `228` (no currency symbol). |
| `currency` | no | 3-letter ISO code | trip default currency | e.g. `"USD"`. Set only if this price differs from the trip default currency. |
| `paid` | no | `paid` / `to pay` | none | Payment state. |
| `car_type` | no | enum | `regular` | One of `regular`, `small`, `suv`, `4x4`. |
| `car_model` | no | text | none | e.g. "Dacia Duster". |
| `contact` | no | text | none | Phone/email for the rental desk. |
| `additional_drivers` | no | whole number ≥ 0 | `0` | Extra named drivers. |
| `pickup_duration` | no | duration (`"30 min"`) | none | How long collecting the car takes. |
| `dropoff_duration` | no | duration (`"20 min"`) | none | How long returning it takes. |

## Notes for extraction

- The **booking window** (`booking_*`) is the contractual period; the
  **pick-up / drop-off** are the actual events, which must fall inside it, with
  drop-off after pick-up. If the source gives only the pick-up/drop-off, reuse
  those for the booking window.
- `pickup_duration` / `dropoff_duration` place the events on the day timeline;
  set them only if the source implies a slot (otherwise leave them out).
- If `status` or `paid` is set, include `booking_number` / `price` when known
  (`validate` warns otherwise).
- **`price` is a bare number** (no symbol): write `228`, not `"€228"`. It's in
  the trip's default currency unless you add `currency` (a 3-letter ISO code
  that must be the default or a declared secondary currency).

## Example

Source: *"Europcar EC-55231, SUV (Dacia Duster), €228 paid. Pick up Pau
Airport Jun 8 18:15, drop off Montréjeau station Jun 11 19:30. Booking valid
Jun 8 18:00 – Jun 11 20:00. 1 additional driver. +33 5 59 33 20 10."*

```json
{
  "company": "Europcar",
  "car_type": "suv",
  "car_model": "Dacia Duster",
  "booking_start_date": "2026-06-08",
  "booking_start_time": "18:00",
  "booking_end_date": "2026-06-11",
  "booking_end_time": "20:00",
  "pickup_date": "2026-06-08",
  "pickup_time": "18:15",
  "pickup_location": "Pau Airport",
  "pickup_duration": "30 min",
  "dropoff_date": "2026-06-11",
  "dropoff_time": "19:30",
  "dropoff_location": "Montréjeau station",
  "dropoff_duration": "20 min",
  "booking_number": "EC-55231",
  "status": "confirmed",
  "price": 228,
  "paid": "paid",
  "additional_drivers": 1,
  "contact": "+33 5 59 33 20 10"
}
```

## Map coordinates (optional)

If the trip renders maps (`defaults.include_maps_in_render` is on), a rental has
two locations, so it takes **`pickup_coordinate`** and **`dropoff_coordinate`**:

```json
"pickup_coordinate": { "lat": 43.3800, "long": -0.4189 },
"dropoff_coordinate": { "lat": 43.0850, "long": 0.5660 }
```

- `lat` / `long` are decimal degrees (latitude −90…90, longitude −180…180).
- Each is plotted by default; add `"show_on_map": false` to one to record it
  without drawing its pin.
- Only set what you actually know — never guess.

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
