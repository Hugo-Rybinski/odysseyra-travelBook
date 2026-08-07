# Skill: `transports/transport-<INDEX>.json`

**Target file:** `<ROOT>/transports/transport-<INDEX>.json` — **one file per
leg** (`transport-01.json`, `transport-02.json`, …).

One inter-city travel leg: a flight, train, bus, or taxi. This is the skill for
a **booking confirmation** (airline/rail email, e-ticket, PDF, screenshot).

## What to extract

From the confirmation: the **mode** (`type`), **from**/**to** stations or
airports, the **departure date and time** (required), the arrival time, any
**timezones** (crucial for flights that cross zones), the **booking reference**,
who you booked with, the **price**, and whether it's **paid**.

## Fields

| Field | Required | Format | Default | Notes |
|---|---|---|---|---|
| `type` | no | enum | `other` | One of `plane`, `train`, `bus`, `taxi`, `ferry`, `other`. |
| `start` | **yes** | text | — | Departure point (station/airport/city). |
| `end` | **yes** | text | — | Arrival point. |
| `start_date` | **yes** | date `YYYY-MM-DD` | — | Departure date. |
| `start_time` | **yes** | time `HH:MM` | — | Departure time (local). |
| `end_date` | no | date `YYYY-MM-DD` | inferred (+1 day if it crosses midnight) | Set for overnight legs when known. |
| `end_time` | no | time `HH:MM` | inferred from `start_time` + `duration` | Arrival time (local). |
| `start_tz` | no | UTC offset | trip default timezone | Departure zone — **set it for flights** between zones. |
| `end_tz` | no | UTC offset | trip default timezone | Arrival zone. |
| `duration` | no | duration (`"4h20"`) | inferred from the two times (timezone-aware) | Give it if the two times aren't both known. |
| `flight_number` | no | text | none | **Planes only** — the flight number (e.g. `"AF9"`). Shown on the card. |
| `train_number` | no | text | none | **Trains only** — the train number (e.g. `"TGV 8541"`). Shown on the card. |
| `booking_number` | no | text | none | Reservation reference / PNR. |
| `booking_source` | no | text | none | Where booked (e.g. "SNCF Connect"). |
| `status` | no | `booked` or `confirmed` | none | Reservation status. |
| `price` | no | number | none | The amount only, e.g. `89` (no currency symbol). |
| `currency` | no | 3-letter ISO code | trip default currency | e.g. `"USD"`. Set only if this price is in a different currency than the trip default. |
| `paid` | no | `paid` / `to pay` | none | Payment state. |

## Notes for extraction

- **Provide any two of** `start_time` / `end_time` / `duration`; the tool
  derives the third. Departure date + time are always required.
- **Timezones matter.** For a flight `22:30 (UTC-4) → 11:45 (UTC+2)`, set both
  `start_tz` and `end_tz` so the duration comes out right (here 7h15).
- **If the source doesn't state the timezones, look them up.** For a flight,
  resolve each airport's zone from its code (e.g. `JFK` → `America/New_York`,
  `CDG` → `Europe/Paris`); for a train, resolve each station's zone from its
  name/city. Use the UTC offset in effect on the travel date (mind DST), and set
  `start_tz` / `end_tz` accordingly. Only skip this when both endpoints clearly
  share the trip's default timezone.
- **One file per leg.** If a flight or train has several legs — e.g. Paris → New
  York *via* London — create a separate JSON per leg (one Paris → London, one
  London → New York), each with its own times, timezones, and (where they
  differ) flight/train numbers. Don't collapse a multi-leg journey into a single
  entry.
- An **overnight** leg (arrival time earlier than departure, or `end_date`
  after `start_date`) is treated as *that night's accommodation* — you sleep
  aboard it, so don't also add a hotel for that night.
- If `status` or `paid` is set, include the matching `booking_number` / `price`
  when available (`validate` warns otherwise).
- **`price` is a bare number** (no symbol): write `89`, not `"€89"`. Prices are
  assumed to be in the trip's default currency; only add `currency` (a 3-letter
  ISO code) when the source states a different one, and that code must be the
  default or one of `defaults.secondary_currencies` (`validate` errors
  otherwise).
- **`flight_number` / `train_number` vs `booking_number`.** The flight/train
  number is the public service identifier (e.g. `AF9`, `TGV 8541`); the booking
  number is your reservation reference / PNR (e.g. `AF1234-XY`). They're
  different — capture both when the source gives them. Only set `flight_number`
  on a `plane` and `train_number` on a `train` (`validate` warns on a mismatch).

## Example

Source: *"Air France flight AF9, ref AF1234-XY, confirmed & paid $667. JFK
22:30 (Jun 7, EDT) → Paris CDG 11:45 (Jun 8, CEST). Booked on the AirFrance
website."*

```json
{
  "type": "plane",
  "start": "New York JFK",
  "end": "Paris CDG",
  "start_date": "2026-06-07",
  "end_date": "2026-06-08",
  "start_time": "22:30",
  "start_tz": "-04:00",
  "end_time": "11:45",
  "end_tz": "+02:00",
  "flight_number": "AF9",
  "booking_number": "AF1234-XY",
  "booking_source": "AirFrance website",
  "status": "confirmed",
  "price": 667,
  "currency": "USD",
  "paid": "paid"
}
```

(The trip's default currency here is EUR, so this leg sets `currency` to `USD`
because it was priced in dollars; a leg priced in euros would just omit it.)

## Map coordinates (optional)

A transport leg goes A→B, so it takes **`start_coordinate`** and
**`end_coordinate`** (each `{ "lat": .., "long": .. }`) when you know them. Only
set what you know; add `"show_on_map": false` on a coordinate to keep it without
plotting it.

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
