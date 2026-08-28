# Skill: build the full itinerary JSON

**Output:** a single `<title>.json` — the **complete** itinerary in one file.
The user will later turn it into a PDF with the `odysseyra-travelBook` tool; your job is
only to produce correct JSON. You do **not** run any commands.

Use this skill when you want to turn a pile of source material (a trip brief,
booking-confirmation emails, hotel/rental vouchers, screenshots, a day-by-day
plan, a guidebook PDF, links to blog posts, a KML/KMZ track — e.g. one exported
from a custom Google Map, a GPX track for a hike or off-road drive, or an MBOX
export — e.g. a Gmail label exported via Google Takeout) **directly into one
finished JSON file**.

**This document is self-contained.** Everything you need — the top-level shape,
every object's fields, the value formats, and all the rules — is here; you do
not need any other file, the source code, or any tool. Follow the field tables
and rules exactly, because you cannot run the validator to catch mistakes: the
JSON you emit must be correct on the first pass.

**Start from a blank slate.** Work only from this skill and the documents
provided in this conversation — do not draw on past memory, earlier
conversations, or prior assumptions. If a fact is not in this skill or the
supplied sources, it does not exist for this task.

---

## The workflow

1. Read **all** the source material first. Note which document each fact comes
   from — you will report conflicts between them at the end.
2. Build one JSON object with the top-level shape below. Fill only what the
   sources actually state; leave everything else out so the tool applies its
   defaults.
3. **Self-check** the JSON against the "Global rules" and the "Before you emit
   it" checklist at the end — you have no validator, so this manual pass is your
   only safety net.
4. Output the finished JSON, then report the gaps and the inconsistencies (see
   the end of this document).

**Mining an MBOX for booking links.** When the source includes an MBOX export
(e.g. a Gmail label saved via Google Takeout), treat each confirmation email as
a rich source for the reservation fields — especially the **direct booking
link**. Scan every message's body (and, where present, the HTML part) for the
"manage / view / modify your booking" URL and put it in the matching entry's
`booking_link` (transport or accommodation); do the same for the carrier's or
property's `website`, and pull the `booking_number`/PNR, `booking_source`,
`price`, dates and times from the same email. Prefer the stable manage-booking
URL over one-time tracking links, and never invent a link — only use one that
actually appears in the email.

---

## Top-level shape

The itinerary is one JSON **object** with these keys:

```json
{
  "travel_description": { ... },   // object — cover info (title required)
  "defaults":           { ... },   // object — trip-wide defaults (all optional)
  "days":               [ ... ],   // array  — REQUIRED, non-empty; one entry per day, in order
  "transport":          [ ... ],   // array  — inter-city legs (flights/trains/buses/…)
  "accommodations":     [ ... ],   // array  — places you sleep
  "car_rentals":        [ ... ]    // array  — rental-car bookings
}
```

- Only `days` is required (non-empty). Every other key may be omitted.
- Note the exact key names: **`transport`** is singular, **`car_rentals`** uses
  an underscore, **`accommodations`** is plural.
- `title` (and the other `travel_description` fields) may also sit at the top
  level instead of inside `travel_description`, but the grouped form is cleaner —
  prefer it.
- Trip `start_date` / `end_date` are normally **inferred** as the earliest /
  latest date across days, transport, accommodation and car rentals. A day with
  no `date` is inferred as trip-start + its index. So you rarely set dates
  except the concrete ones your sources give.

---

## Shared value formats

Every object uses these. Write each kind of value **exactly** like this:

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
| **Coordinate** | `{ "lat": .., "long": .. }`, decimal degrees (lat −90…90, long −180…180) | `{ "lat": 43.0974, "long": -0.0583 }` |

`inference_countries` (in `defaults`) takes **2-letter** ISO *country* codes
(`"FR"`, `"ES"`), not the 3-letter currency codes.

Convert freely into these formats: "6pm" → `"18:00"`, "June 8, 2026" →
`"2026-06-08"`.

---

## `travel_description` (object)

The cover: title, optional subtitle/summary, accent color, optional manual
dates.

| Field | Required | Format | Default | Notes |
|---|---|---|---|---|
| `title` | **yes** | text | — | Shown big on the cover. |
| `subtitle` | no | text | none | A tagline under the title. |
| `summary` | no | text | none | A short paragraph shown on the cover. |
| `cover_color` | no | hex color (`"#2f6b4f"`) | `"#1f4e5f"` (teal) | Accent color for the whole PDF. |
| `start_date` | no | date `YYYY-MM-DD` | inferred (earliest date in the trip) | Only set if the source states an explicit trip start; otherwise omit and let it be inferred. |
| `end_date` | no | date `YYYY-MM-DD` | inferred (latest date in the trip) | Same — omit unless explicitly given. |

---

## `defaults` (object)

Trip-wide defaults that fill gaps. **Entirely optional** — omit it and every
field takes its default. Only set a field when the source implies a global
setting (e.g. "all times are local Paris time (UTC+2)" or "we start at 9am").

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
| `show_moon_phase` | no | boolean | `false` | Show the night's moon phase (emoji + name) in each day's "tonight" section. |

**`secondary_currencies`.** Each entry is `{"currency": "<ISO code>",
"change_rate": <number>}`. The `change_rate` is **units of that currency per one
unit of the default currency** — with a `EUR` default, `{"currency": "USD",
"change_rate": 1.09}` means 1 € = $1.09. On the PDF every price is printed in the
default currency followed by each secondary conversion in parentheses (e.g.
`€612 ($667, £520)`).

---

## `days` (array — REQUIRED, one entry per day, in order)

Each entry is one **day**: a title, optional date/city/intro, and an ordered
list of **activities**.

| Field | Required | Format | Default | Notes |
|---|---|---|---|---|
| `title` | **yes** | text | — | The day's headline (e.g. "Renaissance châteaux"). |
| `date` | no | date `YYYY-MM-DD` | trip start + this day's index | Set it if the source states the date; otherwise it's inferred from position. |
| `city` | no | text | none | City/region label (e.g. "Paris", or "Amboise → Sarlat-la-Canéda"). |
| `description` | no | text | none | An intro paragraph for the day. |
| `activities` | **yes** | array (non-empty) | — | The ordered timeline — see below. |

### Activities

`activities` is an ordered array of objects, each with a `type`. There are six
types. **Timing is usually inferred** — you rarely give every time:

- Provide **any two** of `start_time` / `end_time` / `duration` and the third is
  computed. Give one, or none, and the chain fills in.
- The first activity starts at the day's default start (`defaults.start_time`,
  else 08:00). Each next activity starts when the previous one ends.
- Gaps (and the trip's default buffer) become **buffer** activities
  automatically — you seldom add those by hand.

Capture the **order** and whatever concrete times/durations the source gives;
leave the rest out.

**Guidebook page references.** If the source cites guidebook pages for a place,
activity, or zone (e.g. "Lonely Planet p. 142" or "see pp. 88–91"), keep that
reference verbatim in that activity's `description` (append it if a description
already exists). It carries over to any `point_of_interest`, `place`, or `hike`
that has a `description` field.

**Lift a shared page reference up to the area.** When several stops nested under
one container (a `place`, or a `point_of_interest` with sub-activities) all cite
the *same* guidebook pages, drop that reference from each nested `description`
and put it once in the container's `description` instead. Keep a page reference
on a nested stop only when it is *specific to that stop* and differs from the
area's.

**Scheduling fields (any non-`buffer` activity may include these):**

| Field | Format | Notes |
|---|---|---|
| `start_time` | time `HH:MM` | Clock start. |
| `end_time` | time `HH:MM` | Clock end. |
| `duration` | duration (`"1h30"`, `"45 min"`) | How long it lasts. |
| `start_tz` / `end_tz` | UTC offset | Only if this activity is in a different timezone than the trip default. |

**Map coordinates (any located activity may include these):** if the trip
renders maps (`defaults.include_maps_in_render` on), an activity can carry a
`coordinate` (applies to `point_of_interest`, `place`, `hike`, `meal`, `road` —
on a `road` it's the **departure** point). A coordinate is plotted by default;
add `"show_on_map": false` to record one without drawing its pin. With
`infer_coordinates_from_address` on, activities with no coordinate are geocoded
from their `name`/`address`; otherwise only explicit coordinates appear.

#### Type `road` — a drive or transfer

A road departs from `start` and runs through its `waypoints`, in order — the
**last waypoint is the arrival**. There is no `end` field.

| Field | Required | Format | Notes |
|---|---|---|---|
| `start` | **yes** | text | Where the drive begins. |
| `coordinate` | no | `{ "lat": .., "long": .. }` | The departure point, for the map route. |
| `distance_km` | recommended | positive number | Driving distance. A road should carry a duration (its own/inferred times, or waypoint durations) **and** a `distance_km`; `validate` warns naming either that's missing. |
| `off_road` | no | boolean | `true` if part is off-road. |
| `waypoints` | **yes** | non-empty array of **waypoint** objects | Ordered stops through to the arrival. |
| `activities` | no | array of **meal** objects | Meal stops along the drive (see nesting). |

Each **waypoint** is an object:

| Field | Required | Format | Notes |
|---|---|---|---|
| `coordinate` | **yes** | `{ "lat": .., "long": .. }` | The point on the route. Only set coordinates you actually know. |
| `location` | no | text | The waypoint's name. |
| `duration` | no | duration (`"45 min"`) | Time for the leg reaching this waypoint. |
| `distance_km` | no | positive number | Distance for the leg reaching this waypoint. |

- A road needs **at least one** waypoint — the arrival. For a plain A→B drive,
  that's a single waypoint at the destination (name it in `location`).
- Give a waypoint a `location` when it's a real named stop shown to the reader.
  Leave `location` off for a point that only **shapes the route** on the map (a
  bend, a pass): it still gets a map disc, but in the PDF it merges into the next
  named waypoint and its `duration`/`distance_km` are summed into that leg.
- On a **multi-stop** drive each named waypoint is its own displayed leg, so give
  each one a `duration` **and** a `distance_km` (folding in any preceding unnamed
  shaping points); `validate` warns for a named leg missing either.
- Keep the waypoint `duration`s adding up to no more than the road's own
  `duration`; `validate` warns if the segments don't fit the drive.

**Build the waypoints from a KML/KMZ directions track when one is provided.** If
a KML/KMZ holds a *directions* geometry matching this drive, use it to generate
the `waypoints` array instead of listing stops by hand. Keep every **named**
point of the directions that falls on the drive's relevant segment as a named
waypoint (its `location` = that name). Then, between each consecutive pair of
named waypoints, insert **25 intermediate unnamed waypoints** (`location`
omitted) by taking evenly spaced points along the directions geometry for that
segment — so the map route follows the real road rather than a straight line.

**Link separate places with a `road`.** Between two consecutive activities that
happen in different places (a different town, area, or trailhead), insert a
`road` whose `start` is the first place and whose final waypoint is the second.
Skip it only when the two stops share the same area (nested under one `place`,
or clearly in one town) — there's no leg to draw within a single place.

#### Type `point_of_interest` — a specific sight

| Field | Required | Format | Notes |
|---|---|---|---|
| `name` | **yes** | text | The place's name. |
| `category` | no | enum (default `other`) | One of: `museum`, `church`, `building`, `viewpoint`, `ruins`, `castle`, `temple`, `street`, `natural park`, `mountain`, `lake`, `beach`, `waterfall`, `other`. |
| `address` | no | text | |
| `description` | no | text | |
| `website` | no | a link like `https://example.com` | The venue's website — shown as a clickable link. |
| `activities` | no | array of `point_of_interest` / `hike` / `meal` | Nested sights/hikes/meals (see nesting). |

#### Type `place` — a town/area grouping several stops

| Field | Required | Format | Notes |
|---|---|---|---|
| `name` | **yes** | text | The place name. |
| `description` | no | text | |
| `activities` | no | array of `point_of_interest` / `hike` / `meal` | The things you do there. |

**Group co-located stops under a `place`.** When several activities happen in the
same city, town, or national park, don't list them flat in the day — create a
`place` named for that shared zone (e.g. `"The Latin Quarter"`,
`"Sarlat old town"`) and nest the individual sights, hikes and meals inside
its `activities`. Reserve the top-level list for the day's distinct legs (a
drive, a different town). When maps are on, the area gets a single pin plus a
second map zoomed to its nested points. You don't need to give the area its own
`coordinate` — if omitted, its pin is placed at the average position of its
located sub-activities.

#### Type `hike`

| Field | Required | Format | Notes |
|---|---|---|---|
| `name` | **yes** | text | Trail/hike name. |
| `distance_km` | recommended | number | Length. A hike (top-level **or nested** under a place/point of interest) should carry a duration, a `distance_km` **and** an `elevation_m`; `validate` warns naming any of the three that's missing. |
| `elevation_m` | recommended | number | Elevation gain in metres (see `distance_km`). |
| `start` | no | text | Trailhead. |
| `end` | no | text | End point. |
| `route` | no | enum (default `back_and_forth`) | One of `loop`, `back_and_forth`, `one_way`. For `loop`/`back_and_forth`, `end` should match `start` (or be omitted); for `one_way`, `end` should differ. |
| `activities` | no | array of **meal** objects | Meal stops along the hike. |

#### Type `meal` — a stop to eat

| Field | Required | Format | Notes |
|---|---|---|---|
| `meal_type` | no | enum | One of `breakfast`, `lunch`, `dinner`, `brunch`, `snack`, `picnic`, `meal`. **If omitted it is inferred** from the start time as breakfast/lunch/dinner (using `defaults.breakfast_until`/`lunch_until`). Set it explicitly for brunch/snack/picnic/meal. |
| `restaurant` | no | text | The restaurant's name. |
| `area` | no | text | Where to eat, if no named restaurant. Ignored when `restaurant` is set. |
| `address` | no | text | |

#### Type `buffer` — explicit free time

| Field | Required | Format | Notes |
|---|---|---|---|
| `duration` | **yes** | duration (`"30 min"`) | Length of free time. A `0`-minute buffer *suppresses* the default buffer at that point. |

Only add `buffer` when the source explicitly calls for a fixed break; gaps are
otherwise generated for you.

### Nesting rules

A container activity can hold a nested `activities` array, **one level deep
only** (a nested activity may not itself nest). Allowed nesting:

| Container | May nest |
|---|---|
| `road` | `meal` |
| `hike` | `meal` |
| `place` | `point_of_interest`, `hike`, `meal` |
| `point_of_interest` | `point_of_interest`, `hike`, `meal` |

Nested activities happen *inside* the container, so their durations should fit
within it: if the container gives a `duration` (or start/end span) and the
nested durations add up to more, `validate` warns. Leave the container's
duration out if unsure — the warning only fires when both sides are known.

---

## `transport` (array — one entry per leg)

One inter-city leg: a flight, train, bus, taxi, or ferry.

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
| `flight_number` | no | text | none | **Planes only** — e.g. `"AF9"`. |
| `train_number` | no | text | none | **Trains only** — e.g. `"TGV 8541"`. |
| `booking_number` | no | text | none | Reservation reference / PNR. |
| `booking_source` | no | text | none | Where booked (e.g. "SNCF Connect"). |
| `website` | no | link | none | The carrier's website — clickable. |
| `booking_link` | no | link | none | Direct link to this reservation — clickable. |
| `status` | no | `booked` / `confirmed` | none | Reservation status. |
| `price` | no | number | none | Amount only, e.g. `89` (no symbol). |
| `currency` | no | 3-letter ISO code | trip default currency | Set only if this price is in a different currency. |
| `paid` | no | `paid` / `to pay` | none | Payment state. |
| `start_coordinate` / `end_coordinate` | no | `{ "lat": .., "long": .. }` | none | For maps; the route is drawn between them. |

**Notes:**

- **Provide any two of** `start_time` / `end_time` / `duration`; the tool
  derives the third. Departure date + time are always required.
- **Timezones matter.** For a flight `22:30 (UTC-4) → 11:45 (UTC+2)`, set both
  `start_tz` and `end_tz` so the duration comes out right (here 7h15). If the
  source doesn't state them, look them up from the airport codes / station
  cities (use the offset in effect on the travel date — mind DST). Only skip
  this when both endpoints clearly share the trip's default timezone.
- **One file/entry per leg.** A journey Paris → New York *via* London is two
  entries (Paris → London, London → New York), each with its own times, zones
  and (where they differ) flight/train numbers. Don't collapse them.
- An **overnight** leg (arrival earlier than departure, or `end_date` after
  `start_date`) is treated as *that night's accommodation* — don't also add a
  hotel for that night.
- **`flight_number` / `train_number` vs `booking_number`** are different: the
  first is the public service identifier (`AF9`, `TGV 8541`), the second your
  reservation reference / PNR (`AF1234-XY`). Capture both when given. Only set
  `flight_number` on a `plane`, `train_number` on a `train`.
- If `status` or `paid` is set, include the matching `booking_number` / `price`
  when available (`validate` warns otherwise).

---

## `accommodations` (array — one entry per stay)

One place you sleep: hotel, campsite, B&B, or other.

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
| `website` | no | link | none | The property's website — clickable. |
| `booking_link` | no | link | none | Direct link to this reservation — clickable. |
| `status` | no | `booked` / `confirmed` | none | Reservation status. |
| `price` | no | number | none | Amount for the whole stay, e.g. `256` (no symbol). |
| `currency` | no | 3-letter ISO code | trip default currency | Set only if it differs from the trip default. |
| `paid` | no | `paid` / `to pay` (or `true` / `false`) | none | Payment state. |
| `breakfast_included` | no | boolean | `false` | `true` if breakfast is included. |
| `coordinate` | no | `{ "lat": .., "long": .. }` | none | For maps; the property's pin. |

**Notes:**

- **Nights = `departure` − `arrival`.** You do **not** sleep there on the
  departure night — arrive Jun 08, depart Jun 10 = two nights (Jun 08 and 09).
- One stay per entry. Two consecutive stays in different towns are two entries.
- A night spent aboard an overnight transport leg is already covered — you don't
  need a separate accommodation for it. If both are recorded for the same night,
  the tool uses the **accommodation** and just notes the overlap (info, not an
  error).
- If `status` or `paid` is set, include `booking_source` / `price` when known.

---

## `car_rentals` (array — one entry per rental)

One rental-car booking, with its booking window and pick-up / drop-off events.

| Field | Required | Format | Default | Notes |
|---|---|---|---|---|
| `booking_start_date` | **yes** | date `YYYY-MM-DD` | — | When the booking window opens. |
| `booking_start_time` | **yes** | time `HH:MM` | — | |
| `booking_end_date` | **yes** | date `YYYY-MM-DD` | — | When it closes (after the start). |
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
| `website` | no | link | none | The company's website — clickable. |
| `booking_link` | no | link | none | Direct link to this reservation — clickable. |
| `status` | no | `booked` / `confirmed` | none | Reservation status. |
| `price` | no | number | none | Amount only, e.g. `228` (no symbol). |
| `currency` | no | 3-letter ISO code | trip default currency | Set only if it differs from the trip default. |
| `paid` | no | `paid` / `to pay` | none | Payment state. |
| `car_type` | no | enum | `regular` | One of `regular`, `small`, `suv`, `4x4`. |
| `car_model` | no | text | none | e.g. "Dacia Duster". |
| `contact` | no | text | none | Phone/email for the rental desk. |
| `additional_drivers` | no | whole number ≥ 0 | `0` | Extra named drivers. |
| `pickup_duration` | no | duration (`"30 min"`) | none | How long collecting the car takes. |
| `dropoff_duration` | no | duration (`"20 min"`) | none | How long returning it takes. |
| `pickup_coordinate` / `dropoff_coordinate` | no | `{ "lat": .., "long": .. }` | none | For maps; the two location pins. |

**Notes:**

- The **booking window** (`booking_*`) is the contractual period; the **pick-up
  / drop-off** are the actual events, which must fall inside it, drop-off after
  pick-up. If the source gives only the pick-up/drop-off, reuse those for the
  window.
- `pickup_duration` / `dropoff_duration` place the events on the day timeline;
  set them only if the source implies a slot.
- If `status` or `paid` is set, include `booking_number` / `price` when known.

---

## Prices & currency

A `price` is a bare number (write `89`, not `"€89"`). It's in the trip's default
currency (`defaults.currency`, EUR by default) unless the object sets its own
`currency` — a 3-letter ISO code. On the PDF each price prints in the default
currency with the secondary conversions faded in parentheses.

**Using a currency with no rate yet is fine.** If a booking is priced in a
currency you have no exchange rate for (say a hotel in `GBP` on a EUR trip),
still record the price in its real `currency` — do **not** convert it yourself,
force it into EUR, or drop it. Without a matching `defaults.secondary_currencies`
entry the PDF simply prints that amount as-is (no conversion), and `validate`
flags the currency as one to resolve — neither blocks the build. Add a
`{currency, change_rate}` entry later, once the rate is known, to turn
conversion on.

**Tiny price differences aren't a conflict.** If two sources give prices for the
same booking that differ by **1 unit or less** in the same currency (e.g. 256 vs
256.50, or 256 vs 257 — rounding, fees), treat them as equal: use either value
and do **not** list it in the inconsistency report. Only report a price conflict
when the gap exceeds 1 (or the currencies differ).

**Ignore a source's own conversion — keep only the charged amount.** When a
source states a price with a parenthetical/approximate conversion into another
currency (e.g. `$100 (≈ €98.54)` or `100 USD, about 98.54 EUR`), record **only
the original charged amount and its currency** as the `price`/`currency`
(`price: 100`, `currency: "USD"`) and drop the converted figure. The two are not
a conflict.

---

## Full worked example

A short slice of a France trip: one flight in, a hire car picked up off the
train, a nested `place`, a multi-stop drive, one hotel and a car rental. (Shows
the shape — real values come from your sources. The full version lives at
`examples/france.json`.)

```json
{
  "travel_description": {
    "title": "Grand Tour of France",
    "subtitle": "Paris, the Loire châteaux, the Dordogne and the high Pyrenees",
    "cover_color": "#2f5d8c",
    "summary": "A week across France: Paris, the Loire châteaux, the medieval Dordogne, and a hike in the high Pyrenees."
  },
  "defaults": {
    "start_time": "08:30",
    "timezone": "+02:00",
    "meal_duration": "1h",
    "currency": "EUR",
    "secondary_currencies": [
      { "currency": "USD", "change_rate": 1.08 }
    ]
  },
  "days": [
    {
      "date": "2026-09-05",
      "city": "Paris",
      "title": "Landing in Paris",
      "description": "Off the overnight flight at CDG, drop the bags, then the Louvre.",
      "activities": [
        {
          "type": "road",
          "start": "Paris-Charles de Gaulle Airport",
          "distance_km": 32,
          "start_time": "12:30",
          "duration": "50 min",
          "waypoints": [
            { "location": "Hôtel des Grands Boulevards", "coordinate": { "lat": 48.8713, "long": 2.3436 } }
          ]
        },
        {
          "type": "point_of_interest",
          "name": "Musée du Louvre",
          "category": "museum",
          "address": "Rue de Rivoli, 75001 Paris",
          "start_time": "15:30",
          "duration": "2h30",
          "website": "https://www.louvre.fr"
        }
      ]
    },
    {
      "date": "2026-09-06",
      "city": "Paris",
      "title": "Île de la Cité to the Latin Quarter",
      "activities": [
        {
          "type": "point_of_interest",
          "name": "Cathédrale Notre-Dame de Paris",
          "category": "church",
          "address": "6 Parvis Notre-Dame, 75004 Paris",
          "end_time": "12:30"
        },
        {
          "type": "meal",
          "restaurant": "Les Deux Palais",
          "address": "3 Bd du Palais, 75004 Paris",
          "start_time": "12:30"
        },
        {
          "type": "place",
          "name": "The Latin Quarter",
          "start_time": "14:00",
          "duration": "3h",
          "activities": [
            {
              "type": "point_of_interest",
              "name": "Panthéon",
              "category": "building",
              "duration": "45 min"
            }
          ]
        }
      ]
    },
    {
      "date": "2026-09-08",
      "city": "Amboise → Sarlat-la-Canéda",
      "title": "South to the Dordogne",
      "activities": [
        {
          "type": "road",
          "start": "Amboise",
          "waypoints": [
            { "location": "Poitiers", "coordinate": { "lat": 46.5802, "long": 0.3404 }, "duration": "1h20" },
            { "location": "Limoges", "coordinate": { "lat": 45.8336, "long": 1.2611 }, "duration": "1h15" },
            { "location": "Sarlat-la-Canéda", "coordinate": { "lat": 44.8890, "long": 1.2160 }, "duration": "1h25" }
          ]
        }
      ]
    }
  ],
  "transport": [
    {
      "type": "plane",
      "start": "New York JFK",
      "end": "Paris CDG",
      "start_date": "2026-09-04",
      "end_date": "2026-09-05",
      "start_time": "22:10",
      "start_tz": "-04:00",
      "end_time": "11:45",
      "end_tz": "+02:00",
      "flight_number": "AF23",
      "booking_number": "AF77-QWLM",
      "status": "confirmed",
      "price": 720,
      "currency": "USD",
      "paid": "paid"
    }
  ],
  "accommodations": [
    {
      "name": "Hôtel des Grands Boulevards",
      "arrival": "2026-09-05",
      "departure": "2026-09-07",
      "city": "Paris",
      "type": "hotel",
      "address": "17 Bd Poissonnière, 75002 Paris",
      "booking_source": "Booking.com",
      "status": "confirmed",
      "price": 340,
      "paid": true,
      "breakfast_included": true
    }
  ],
  "car_rentals": [
    {
      "company": "Hertz",
      "car_type": "suv",
      "car_model": "Peugeot 5008",
      "booking_start_date": "2026-09-07",
      "booking_start_time": "10:00",
      "booking_end_date": "2026-09-11",
      "booking_end_time": "15:00",
      "pickup_date": "2026-09-07",
      "pickup_time": "10:15",
      "pickup_location": "Tours railway station",
      "dropoff_date": "2026-09-11",
      "dropoff_time": "14:00",
      "dropoff_location": "Toulouse-Blagnac Airport",
      "booking_number": "HZ-90412",
      "status": "confirmed",
      "price": 415,
      "paid": "paid",
      "additional_drivers": 1
    }
  ]
}
```

---

## Global rules

- **Only include a field if the source actually states it.** Never invent
  bookings, prices, dates, or times. Omitting an optional field lets the tool
  fall back to a sensible default (listed above).
- The top level is one JSON **object** with the keys shown above; `days` must be
  a non-empty array.
- Write dates/times/durations exactly in the formats above; convert "6pm" →
  `"18:00"`, "June 8, 2026" → `"2026-06-08"`.
- When a value is unknown but the field is **required**, leave a clear `"FIXME"`
  placeholder so it stands out to the user (the tool's validator will also flag
  it later).
- **Only set coordinates you actually know — never guess them.**
- **A KML/KMZ file is the principal source of truth for coordinates.** When one
  is provided, take every `coordinate` from it. If another document states
  different coordinates for the same place, trust the KML/KMZ.
- **A GPX track is the principal source of truth for a hike's (or off-road
  drive's) figures.** When a GPX is provided for a hike, take its `distance_km`,
  `elevation_m` and start/end from the track. If the prose text states different
  numbers, use the GPX values in the JSON — but flag the discrepancy in the
  end-of-run inconsistency report (below), naming both figures.
- **After writing the JSON, report the gaps.** List the optional fields you left
  empty (with a one-line note on what each would add) so the user can fill in
  anything the source didn't cover.
- **Once you're done, report the inconsistencies.** Present them as a **bullet
  list**, one bullet per conflict, and for each one state clearly: *what* was in
  conflict (the field/place and the differing values, e.g. "arrival time: email
  says 14:00, voucher says 14:30"), *which value you chose* for the JSON, and
  *why* (which source you trusted). Cover every conflict you found between the
  source documents — a place, date, time, price, coordinate, hike figure…
  stated differently in two places.
- **Trust user-supplied details.** If the user adds or corrects a value by hand,
  keep it even when it isn't in the source document — treat it as ground truth,
  not something to second-guess or overwrite.

## Before you emit it — self-check

You cannot run the validator, so verify these by hand:

- **It parses.** Valid JSON — double-quoted keys/strings, no trailing commas, no
  comments, balanced braces/brackets.
- **Top level** is one object; `days` is present and a **non-empty** array. Key
  names are exact: `travel_description`, `defaults`, `days`, `transport`
  (singular), `accommodations`, `car_rentals` (underscore).
- **Every required field is present** on every object (see the field tables) —
  or carries a `"FIXME"` when genuinely unknown.
- **Formats match** the shared-formats table: dates `YYYY-MM-DD`, times `HH:MM`,
  durations/timezones as shown, prices bare numbers, coordinates `{lat,long}`.
- **Enums** use only the listed values (activity `type`, PoI `category`, hike
  `route`, transport `type`, accommodation `type`, car `car_type`, `meal_type`,
  `status`, `paid`).
- **Date coherence:** accommodation `departure` after `arrival`; car-rental
  drop-off after pick-up and both inside the booking window; any manual trip
  `start_date`/`end_date` actually span the days/legs.
- **Currency:** any object-level `currency` is the default or one of
  `defaults.secondary_currencies`.
- **Coordinates** only where you actually know them — never guessed.
