# Skill: `accommodations/accommodation-<INDEX>.json`

**Target file:** `<ROOT>/accommodations/accommodation-<INDEX>.json` — **one file
per stay** (`accommodation-01.json`, `accommodation-02.json`, …).

One place you sleep: a hotel, campsite, B&B, or other lodging. This is the
skill for a **lodging booking** (Booking.com/hotel email, voucher, screenshot).

## What to extract

From the confirmation: the **name**, the **city/town**, the **check-in
(arrival)** and **check-out (departure)** dates (all required), the **address**
and **contact**, where it was booked, the **price**, whether it's **paid
online**, and whether **breakfast is included**.

## Fields

| Field | Required | Format | Default | Notes |
|---|---|---|---|---|
| `name` | **yes** | text | — | The property name. |
| `arrival` | **yes** | date `YYYY-MM-DD` | — | Check-in date. |
| `departure` | **yes** | date `YYYY-MM-DD` | — | Check-out date; **must be after** `arrival`. |
| `city` | **yes** | text | — | Town/city, used on the cover overview. |
| `type` | no | enum | `hotel` | One of `hotel`, `camping`, `b&b`, `other`. |
| `address` | no | text | none | Street address. |
| `contact` | no | text | none | Phone or email. |
| `booking_source` | no | text | none | e.g. "Booking.com". |
| `price` | no | number | none | The amount only for the whole stay, e.g. `256` (no currency symbol). |
| `currency` | no | 3-letter ISO code | trip default currency | e.g. `"USD"`. Set only if this price differs from the trip default currency. |
| `paid_online` | no | boolean | `false` (shows a "To pay" badge) | `true` if already paid. |
| `breakfast_included` | no | boolean | `false` | `true` if breakfast is included. |

## Notes for extraction

- **Nights = `departure` − `arrival`.** You do **not** sleep there on the
  departure night — for a 2-night stay set `arrival` to the check-in day and
  `departure` to the morning you leave (e.g. arrive Jun 08, depart Jun 10 = two
  nights, Jun 08 and Jun 09).
- One stay per file. Two consecutive stays in different towns are two files.
- Don't add an accommodation for a night spent aboard an overnight
  transport leg — that leg already covers that night.
- If `paid_online` is `true`, include `price` when known (`validate` warns
  otherwise).
- **`price` is a bare number** (no symbol): write `256`, not `"€256"`. It's in
  the trip's default currency unless you add `currency` (a 3-letter ISO code
  that must be the default or a declared secondary currency).

## Example

Source: *"Hôtel Gallia & Londres, Lourdes. Check-in Jun 8, check-out Jun 10.
26 Av. Bernadette Soubirous, 65100 Lourdes, +33 5 62 94 35 44. Booking.com,
€256, paid online, breakfast included."*

```json
{
  "name": "Hôtel Gallia & Londres",
  "arrival": "2026-06-08",
  "departure": "2026-06-10",
  "city": "Lourdes",
  "type": "hotel",
  "address": "26 Av. Bernadette Soubirous, 65100 Lourdes",
  "contact": "+33 5 62 94 35 44",
  "booking_source": "Booking.com",
  "price": 256,
  "paid_online": true,
  "breakfast_included": true
}
```

## Map coordinates (optional)

An accommodation may carry a `coordinate` (`{ "lat": .., "long": .. }`) so it can
be placed on a map. Only set it if you know it; add `"show_on_map": false` to keep
a coordinate without plotting it.

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
