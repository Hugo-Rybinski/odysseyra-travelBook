# JSON file format

The complete Odysseyra TravelBook itinerary format, field by field: one table per
object, each giving **Required / Type / Format / Default**. This file is
authoritative — see [`README.md`](README.md) for what the tool does with it, and
[`skills/build-full-json.md`](skills/build-full-json.md) for the self-contained
guide an LLM uses to write one of these from raw notes.

## Contents

- [Global structure](#global-structure)
- [`travel_description`](#travel_description)
- [`defaults`](#defaults)
- [`misc`](#misc)
- [`days[]` — a day](#days--a-day)
- [`activities[]` — common fields](#activities--common-fields)
- [`transport[]`](#transport)
- [`accommodations[]`](#accommodations)
- [`car_rentals[]`](#car_rentals)

Each day needs a `title`, each day needs at least one activity, and `days` must
be non-empty; everything else is optional and falls back to a sensible default.

## Global structure

The top-level object has three config groups and three content arrays:

- **`travel_description`** *(object)* — what the trip is: cover title, summary,
  accent color, and an optional date range (inferred from the earliest/latest
  date across days, transport and accommodation when not set).
- **`defaults`** *(object)* — fallback settings applied across the trip: the
  day start and end time, how the buffers between activities are sized, time
  zone.
- **`misc`** *(object, optional)* — trip-wide reference data that belongs to no
  point on the timeline. Today: the emergency contacts.
- **`days`** *(array, required, non-empty)* — the itinerary, one per day.
- **`transport`** *(array, optional)* — travel bookings, each with its `legs`
  (the legs are also woven into the days).
- **`accommodations`** *(array, optional)* — where you sleep.
- **`car_rentals`** *(array, optional)* — rental-car bookings.

```json
{
  "travel_description": {
    "title": "Grand Tour of France",
    "subtitle": "Paris, the Loire, the Dordogne and the Pyrenees",
    "cover_color": "#2f5d8c",
    "summary": "A short paragraph shown on the cover."
  },
  "defaults": {
    "start_time": "08:30",
    "end_time": "21:00",
    "timezone": "+02:00"
  },
  "misc": {
    "emergency_contacts": [ /* { "name": …, "contact": … } */ ]
  },
  "days": [ /* day objects */ ],
  "transport": [ /* transport bookings, each with its "legs" */ ],
  "accommodations": [ /* accommodation objects */ ],
  "car_rentals": [ /* car rental objects */ ]
}
```

Throughout, dates use `YYYY-MM-DD`, times use `HH:MM`, durations look like
`"1h30"` / `"45 min"` / `"1:30"`, and UTC offsets like `+02:00` / `UTC-3` /
`Z`. The descriptive and config keys may live either in their groups
(`travel_description` / `defaults`) or at the top level, but the old renamed
aliases (`default_start_time` / `default_end_time` / `default_buffer`,
`start_timezone` / `end_timezone`, transport `date`, `transports`, `default`)
are no longer accepted — use the canonical names. **`misc` is the exception**:
its keys are read from the group only, never from the top level (it is new, so
there is no older shape to stay compatible with).

## `travel_description`

`start_date` / `end_date` are optional: if omitted they are **inferred** as the
earliest / latest date across days, transport and accommodation; if set, they
override and validation cross-checks the itinerary against them.

| Field | Required | Description | Type | Format | Default |
| ----- | -------- | ----------- | ---- | ------ | ------- |
| `title` | ✅ | Trip title shown on the cover | string | any text | — |
| `subtitle` |  | Line under the title | string | any text | `""` (hidden) |
| `start_date` |  | Trip start date (overrides inference) | string | `YYYY-MM-DD` | inferred (earliest date) |
| `end_date` |  | Trip end date (overrides inference) | string | `YYYY-MM-DD` | inferred (latest date) |
| `cover_color` |  | Accent color driving the whole palette | string | hex `#RRGGBB` | `"#1f4e5f"` |
| `summary` |  | Paragraph shown on the cover | string | any text | `""` (hidden) |

## `defaults`

| Field | Required | Description | Type | Format | Default |
| ----- | -------- | ----------- | ---- | ------ | ------- |
| `start_time` |  | First activity's start time each day | string | `HH:MM` | `"08:00"` |
| `end_time` |  | Where each day's last activity should land: auto-sized buffers spread the day out to it, and validation warns past it | string | `HH:MM` | `"18:00"` |
| `auto_sized_buffer` |  | Size the buffers between a day's activities so the day ends on `end_time` (supersedes `buffer`) | boolean | `true`/`false` | `true` (auto-sized) |
| `buffer` |  | Fixed buffer inserted between consecutive activities — ignored while `auto_sized_buffer` is on | string | duration | `0` (no fixed buffer) |
| `timezone` |  | Default UTC offset for all times | string | offset (`+02:00`, `UTC-3`, `Z`) | `GMT` (UTC+0) |
| `breakfast_until` |  | A meal starting before this is inferred as breakfast | string | `HH:MM` | `"10:00"` |
| `lunch_until` |  | A meal starting up to this (after breakfast) is lunch; later, dinner | string | `HH:MM` | `"16:00"` |
| `meal_duration` |  | Default length of a meal with no duration/end time | string | duration | `0` (instant) |
| `accommodation_start_time` |  | Evening clock time each accommodation night starts on the calendar (`ics` export) | string | `HH:MM` | `"22:00"` |
| `accommodation_end_time` |  | Clock time each accommodation night ends on the calendar (`ics` export) | string | `HH:MM` | `"00:00"` (midnight) |
| `currency` |  | Currency every price is in unless a price sets its own | string | 3-letter ISO code | `"EUR"` |
| `secondary_currencies` |  | Extra currencies each price is also shown in on the PDF | array | `{currency, change_rate}` objects | `[]` (none) |
| `include_maps_in_render` |  | Draw a per-day OpenStreetMap with a pin for each located activity | boolean | `true`/`false` | `false` (no maps) |
| `include_hike_maps` |  | Draw the trail map + elevation profile of a hike that embeds a `gpx` (independent of `include_maps_in_render`) | boolean | `true`/`false` | `true` (drawn) |
| `infer_coordinates_from_address` |  | Geocode activities that lack an explicit `coordinate` (else only ones with a coordinate are mapped) | boolean | `true`/`false` | `false` |
| `inference_countries` |  | Restrict geocoding to these countries when inferring coordinates | array | 2-letter ISO codes, e.g. `["FR"]` | `[]` (any) |
| `show_moon_phase` |  | Show the night's moon phase (emoji + name) — appended to the sunrise/sunset line when `show_sun_times` is on too, else in each day's "tonight" section | boolean | `true`/`false` | `true` (shown) |
| `show_sun_times` |  | Show each day's sunrise/sunset (`☀ 06:12 → 21:34`) in its header, computed at that night's accommodation | boolean | `true`/`false` | `true` (shown) |

### Auto-sized buffers — spreading a day out to `end_time`

By default (`defaults.auto_sized_buffer`) the pauses between a day's activities
aren't a fixed length: they're **sized** so the day spreads out and its last
activity lands on `defaults.end_time` (`18:00` unless you set it). Four visits of
an hour each from `09:00` don't finish at `13:00` and leave five empty hours —
they get about 1h40 of breathing room between them, which is what the day
actually looks like.

The rules:

- The slack is shared out **evenly** over the gaps between consecutive
  activities, in whole steps of **5 minutes** (a leftover of under 5 minutes
  isn't spent, so a day can end up to 4 minutes early).
- **A `start_time` you wrote is never moved.** It cuts the day in two: what comes
  before it is spread out only as far as that time, and what comes after starts
  there. An explicit `end_time` is a promise too — the activity carrying one ends
  the stretch it's in, so padding never shortens it.
- A gap you filled with a **`buffer` activity** is left alone — it already says
  how long that pause is — and its length counts against the slack.
- A day with **more** in it than fits before `end_time` is left packed as it is
  (and validation warns about the overrun); so is a single activity with no gap
  to spread into.
- A day where **nothing** gives a duration is left alone too: there's no
  schedule to space out, and spreading would invent one. Fill in the durations
  validation is asking for and the spacing follows.

`defaults.buffer` — a *fixed* pause between every two activities — is the
alternative, not a floor underneath it: with auto-sizing on, `buffer` is ignored
and validation warns that you set both. Switch `auto_sized_buffer` off to go back
to the fixed buffer and a day that stays packed.

Each `secondary_currencies` entry is `{"currency": "<ISO code>", "change_rate":
<number>}`, where `change_rate` is **units of that currency per one unit of the
default currency** (with a `EUR` default, a `USD` rate of `1.09` means
1 € = $1.09). On the PDF every price prints in the default currency followed by
each secondary conversion in parentheses, e.g. `€612 ($667, £520)` — converted
amounts show two decimals below 25 and are rounded to whole numbers at or above
25. Major currencies (`EUR`, `USD`, `GBP`, `JPY`) print with their symbol; others
show the ISO code.

### Maps & coordinates

When `defaults.include_maps_in_render` is `true`, each day page gets a small
OpenStreetMap with a numbered pin for every located activity and the day's drives
drawn as routes. The night's accommodation, if it has a coordinate, is pinned with
a `*`. A place (an `area`) is shown as a single pin, and — when it has two or more
located sub-activities — a second map zoomed to those points is drawn right after
it, with those pins lettered **A, B, C…** plus that night's `*`. The zoom map's
framing comes from the area's own points alone, so adding the `*` never shifts or
widens it — which does mean a hotel that falls outside the rendered frame isn't
visible there. Each pin's label (number, `*`, or area letter) also appears as a
small disc next to that activity's title in the itinerary, so there's no separate
map key.

**One place, one pin.** A day often names the same spot twice — a drive's
junction is the next drive's departure, an out-and-back passes its turning point
on the way there and back, the village you park in is also the sight you visit.
Two of a day's points that carry the **same name** and sit **within a kilometre**
of each other are treated as one place: they share a single pin and a single
number, so the sequence counts places rather than mentions. The comparison
ignores case, accents and the curly/straight apostrophe, so a name typed by hand
and the same name copied from elsewhere still match — but it is a *name* match, so
`Cauterets — car park` stays its own place, distinct from `Cauterets`. Same name
much further apart (two towns of one name on a long driving day) keeps two pins,
and so do two different names at one spot. The rule applies to the numbered day
map and to an area's lettered pins; the whole-trip map is unaffected (its pins
carry the day, and it merges a day's neighbours on its own, coarser rule).

The book also opens with a **whole-trip map page**, right after the cover: one
full-page map holding every day's located points, each pinned with its **day
number** (not the per-day `1..N` / `*` / `A, B, C…`, which only mean something
inside one day), plus every day's drives as routes and every transport leg as a
dotted line. Points of the same day within about 4 km share one pin — at that
zoom a city day's dozen sights would just be a pinwheel of identical numbers.
It's the same map the viewer's 🗺️ **Overview** tab draws, and it's skipped when
maps are off or nothing on the trip is located.

**Every locatable object may carry a `coordinate`:**

| Field | Required | Description | Type | Format | Default |
| ----- | -------- | ----------- | ---- | ------ | ------- |
| `lat` | ✅ | Latitude | number | −90…90 | — |
| `long` | ✅ | Longitude | number | −180…180 | — |
| `show_on_map` |  | Whether to plot this point | boolean | `true`/`false` | `true` when a coordinate is set |

```json
"coordinate": { "lat": 43.0974, "long": -0.0583 }
```

Segment objects that go from A→B carry endpoint coordinates: a `transport`
**leg** accepts `start_coordinate` / `end_coordinate` (they belong to the leg,
which is what has a departure and an arrival — not to its booking), and
`car_rentals` accept `pickup_coordinate` / `dropoff_coordinate`. Give a transport
leg both endpoints and it's drawn as a **dotted straight line** between them — on the per-day maps
(PDF and viewer alike), on the PDF's whole-trip page and on the viewer's
whole-trip 🗺️ **Overview** map. It's dotted because the real path isn't known,
and for a flight isn't a path on the ground at all. A leg is drawn on every day
map it's *in progress* on, so an **overnight** leg appears on both its departure
and its arrival day. Legs never widen the extent of a **printed** map — a
transatlantic flight would zoom the page out to the ocean — so the line simply
runs off the edge toward where it goes; only a map with nothing else locatable is
framed on its legs. (The viewer's Overview does let them widen its initial view:
there you can zoom out, on paper you can't.) A `road` instead carries its
coordinates on its **legs** — `start_coordinate` / `end_coordinate` per hop, plus
that hop's route-shaping `waypoints` (see below).

With `infer_coordinates_from_address` off (the default) only objects with an
explicit `coordinate` appear on the map, so builds stay deterministic and offline.
Turn it on to geocode the rest from their `name`/`address` at build time
(restricted to `inference_countries` when set). Both are trip data, set in
`defaults` — there is no build flag or export toggle for them, so the CLI and the
viewer always produce the same map for a given file.

### Sunrise & sunset

Every day carries `☀️ Sunrise: 06:12, Sunset: 21:34` (in French,
`☀️ Lever : 06:12, Coucher : 21:34`). Both renderers open the day's body with it,
just above the intro (and below the bank-holiday banner, when there is one).
It's on by default; set `defaults.show_sun_times` to `false` to hide it.

The two ends are located **separately**, because on a day you change town they
happen in different places — the sunset where you'll sleep, the sunrise where you
woke. Each has its own chain, mirroring the other:

| | **Sunrise** (start of day) | **Sunset** (end of day) |
| --- | --- | --- |
| 1 | the stay covering the **previous** night — where you woke | **that** night's accommodation `coordinate` — where you'll watch it go down |
| 2 | the day's own **first** located activity | the day's own **last** located activity |
| 3 | the nearest dated located stay | the nearest dated located stay |

`show_on_map` is ignored throughout: it hides a pin, it doesn't move where you
are. Step 2 covers a night with no stay listed — aboard an overnight leg, or a
day you fly out — and reads a drive's first leg as its departure and its last
leg's arrival as its arrival, so a day's opening and closing positions are both
real. It's why arriving from another continent doesn't print a sunrise from the
far side of it: France day 2 wakes at Roissy, where the flight lands, not in
New York. If the sunrise chain yields nothing usable it settles for the sunset's
reference rather than dropping the line.

Times are read in the day's wall clock — the `start_tz` of its first activity
when one is set explicitly, otherwise `defaults.timezone` — so set `timezone` to
the trip's actual offset (a trip in France left on the `GMT` default reads two
hours early in summer). If the reference point turns out to be more than three
hours of solar time from that clock, **nothing is shown**: a New York morning
printed on Paris time would be honest (`☀ 12:57 → 01:33`) but read as a bug, so
it's left out. Tag that day's activities with their real `start_tz` and the times
come back. That's why day 1 of `examples/france.json` — an afternoon in New York
before the night flight — carries no sun times while every later day does.

Nothing is shown either when the trip has no dates, no coordinate is reachable,
or the sun never crosses the horizon there that day (polar day / night). An
accommodation with only an `address` has no coordinate to compute from; run
[`geocode`](README.md#geocode--bake-in-coordinates) to fill them in and the times appear.

**Navigation links.** Every locatable object gets a clickable **(Navigate)**
link (labelled *(S'y rendre)* in French) right next to its address / location
line — activities, transport, accommodation and car rentals alike. Opening it on
a phone launches the maps / navigation app with the destination pre-filled; in a
browser it opens the chosen provider's web map. The target app is Google Maps by
default, or Apple Maps / OpenStreetMap / Waze / MAPS.ME — pick it with
`--map-provider` (the web viewer has a matching **Navigate links open in** option
that also drives its PDF export). The link points at the object's `coordinate` when
it has one, otherwise it falls back to its `address` / place name, so it appears
even when maps are off and independently of `show_on_map`. A multi-leg `road`
gets one **(Navigate)** per leg in its *VIA* list, each pointing at that leg's
`end_coordinate` (or its `end_location`).

## `misc`

Trip-wide reference data that belongs to the whole trip but to **no point on its
timeline** — so it has nowhere to live among the days, the bookings or the stays.
The whole group is optional, and so is everything in it.

| Field | Required | Description | Type | Format | Default |
| ----- | -------- | ----------- | ---- | ------ | ------- |
| `emergency_contacts` | ❌ | Who to call in an emergency where you're going | array | see below | `[]` (no emergency-contacts section) |

Unlike `travel_description` and `defaults`, whose keys are also accepted at the
top level, `misc` is read **only** from its own object: a bare top-level
`emergency_contacts` would read as trip content rather than reference material,
and there is no older file shape to stay compatible with.

### `misc.emergency_contacts[]`

One entry per number to reach. **Both fields are optional**, and whichever is
present is drawn: a number with no label is still dialable, and a label with no
number still tells the traveller what to look up. An entry with **neither** is
dropped (the validator warns about it), and a missing half is a ⚠️ warning —
because a gap you meant to fill is worth naming, while *inventing* an emergency
number is worse than leaving it out.

| Field | Required | Description | Type | Format | Default |
| ----- | -------- | ----------- | ---- | ------ | ------- |
| `name` | ❌ | Who this contact reaches | string | any text | `""` (the number is listed on its own) |
| `contact` | ❌ | How to reach them | string | any text | `""` (nothing to call — a label only) |

`contact` is deliberately **free text, never parsed**: emergency numbering is
local (`112`, `15`, `999`, `+996 312 …`), and an entry may just as well hold an
email or a street address. So a country's own conventions survive exactly as
written.

```json
"misc": {
  "emergency_contacts": [
    { "name": "Emergency — any service (EU-wide)", "contact": "112" },
    { "name": "SAMU — medical emergencies", "contact": "15" },
    { "name": "US Embassy, Paris — consular emergencies", "contact": "+33 1 43 12 22 22" },
    { "name": "Your embassy in Bishkek" }
  ]
}
```

**Where it shows up.** The PDF gives the contacts its **last page** (a plain
directory: name left, number right in the accent color), reachable from a
*Jump to → Emergency* shortcut on the cover; the web viewer lists them at the
foot of the **🗺️ Overview** tab, where a contact that looks like a phone number
or an email becomes a tap-to-call / mail link. Neither section is drawn when the
list is empty. They are not in the `.ics` export — a phone number is not an
event.

## `days[]` — a day

Every day needs a `title` and a non-empty `activities` array.

| Field | Required | Description | Type | Format | Default |
| ----- | -------- | ----------- | ---- | ------ | ------- |
| `title` | ✅ | The day's title | string | any text | — |
| `city` |  | City/region label | string | any text | `""` |
| `date` |  | The day's date (matched to stays & transport) | string | `YYYY-MM-DD` | trip start date + the day's index |
| `description` |  | Intro paragraph for the day | string | any text | `""` |
| `bank_holiday` |  | The day is a public holiday where you are | bool | `true` / `false` | `false` |
| `activities` | ✅ | The day's items (at least one) | array | activity objects | — |

**Bank holidays.** Set `bank_holiday` on a day that falls on a public holiday in
the country you're in — what's open, and how transport runs, changes. Both
renderers then open the day with a call-out banner (⚠️ **BANK HOLIDAY** — *Expect
closures and reduced opening hours.*), ahead of the intro and the day map, so it's
the first thing you read. It's a flag, not a name: the banner is the same whichever
holiday it is. Nothing infers it — the dates differ by country and by year, so
they have to be looked up (`skills/build-full-json.md` tells the assistant filling
in a trip to do exactly that).

## `activities[]` — common fields

Every activity carries a `type`. All types except `buffer` share the scheduling
fields below: provide any two of `start_time` / `end_time` / `duration` and the
third is inferred (`end = start + duration`). Times chain — the first activity
starts at `defaults.start_time`, each next one at the previous item's end.

| Field | Required | Description | Type | Format | Default |
| ----- | -------- | ----------- | ---- | ------ | ------- |
| `type` | ✅ | The activity kind | string | `road` \| `point_of_interest` \| `place` \| `hike` \| `meal` \| `buffer` | — |
| `start_time` |  | Clock time it starts | string | `HH:MM` | previous item's end, else `defaults.start_time` |
| `end_time` |  | Clock time it ends | string | `HH:MM` | `start_time` + `duration` |
| `duration` |  | How long it lasts | string | duration (`1h30`, `45 min`) | inferred from `end_time`; for a `place`, its nested activities' total; else 0 |
| `start_tz` |  | Start time zone | string | UTC offset | `defaults.timezone` |
| `end_tz` |  | End time zone | string | UTC offset | `defaults.timezone` |
| `detour` |  | A stop kept for reference, left off the timeline (see below) | boolean | `true` / `false` | `false` |
| `price` |  | What this stop costs — an entrance fee, a guided visit, a meal (see below) | number | a bare amount, no symbol (`12`, `7.5`) | none (no price shown) |
| `currency` |  | The currency of `price` | string | 3-letter ISO code | `defaults.currency` |
| `contact` |  | A phone, an email, or how to get in | string | any text | `""` |

A tz label is only shown in the PDF when it differs from `defaults.timezone`.

**Price and contact.** Both are available on every type but `buffer`, because a
fee is a fee whether it buys a museum, a guided walk or a dinner, and a
restaurant's phone number is as worth having as a monument's.

- `price` is a bare amount, like a booking's, and `currency` must be
  `defaults.currency` or one of `defaults.secondary_currencies` — otherwise
  there is no rate to convert it with, and the validator errors. It is printed
  at the end of the stop's figures line, with any secondary conversions faded
  alongside.
- **`0` is meaningful and prints as *Free*.** A guidebook stating that entry
  costs nothing is telling you something an omitted price would not, so a zero
  survives both renderers and the Edit tab's save-time pruning.
- There is **no `paid`** flag, unlike transport / accommodation / car rental: a
  fee at the gate has nothing to settle in advance. A pre-paid ticket is a
  booking, not an activity.
- `contact` is free text and is **never parsed** — it may be a number, an
  email, or an instruction ("call the guardian to open the museum"). It gets its
  own labelled row under the stop's details in both renderers; the viewer alone
  wraps a dialable or mailable value in a `tel:` / `mailto:` link.

**Detours.** `detour` marks a stop you probably *won't* make but want the book to
carry anyway, in case the day goes differently — the cave you'd visit if the
weather turns, the museum an hour off the route. It is kept **beside** the day
rather than on it:

- it counts as **0 minutes** in the schedule, and **no buffer** is inserted
  between it and the activity before it, so nothing after it moves;
- it has **no clock time**: its `duration` is shown (how long the stop *would*
  take) and its start/end are not. A `start_time` / `end_time` written on a
  detour is therefore dropped — if you give both and no `duration`, the span
  between them is kept as the duration and validation says so;
- both renderers **mark it and draw it a step down in emphasis**: the PDF leads
  the title with a small grey `OPTIONAL DETOUR` pill and greys the type badge,
  the title and the description, the viewer puts `Optional detour` in the gutter
  where the start time would be, greys the same two texts and dims the row;
- it keeps its **map pin**: it's still a place you might end up at, so it stays
  on the day map, numbered like any other located stop;
- it is **not** a day highlight on the cover, and it is **not** in the calendar
  export — a calendar entry is a time, and a detour has none.

It works on every type except `buffer` (a buffer *is* time), nested activities
included — a nested detour adds nothing to its container's inferred duration.
A **detour `meal`** should state its `meal_type`: the category is normally
inferred from the start time, and a detour has none (it falls back to lunch).

**Guidebook pages.** The four types that carry a `description` — `road`,
`point_of_interest`, `place` and `hike` — also accept an optional
`guidebook_pages`: the page(s) of the trip's guidebook covering that activity, as
a single page (`"14"`), a range (`"15-18"`) or a comma-separated list
(`"16, 23, 25-30"`). Validation errors on anything that isn't page numbers, so
keep the `p.` out of the value. Both renderers append it to the **end of the
description text** as a light-accent pill reading `Guidebook p. 15-18` — a soft
accent fill with accent text, not bold and not uppercased, so it trails the prose
as a pointer instead of taking a row of its own. It drops to its own line only
when it wouldn't fit after the last line, or when the activity has pages but no
description. It works the same on a nested activity.

### `road` — a drive/transfer

| Field | Required | Description | Type | Format | Default |
| ----- | -------- | ----------- | ---- | ------ | ------- |
| `legs` | ✅ | The hops the drive is made of, in travel order | array | non-empty array of `leg` objects (see below) | — |
| `distance_km` |  | Driving distance for the whole drive | number | positive number | none |
| `display_start_on_maps` |  | Give the departure a numbered map pin | boolean | `true` / `false` | `false` |
| `display_end_on_maps` |  | Give the final arrival a numbered map pin | boolean | `true` / `false` | `false` |
| `display_intermediate_point_on_maps` |  | Give every junction between two legs a numbered map pin | boolean | `true` / `false` | `true` |
| `same_start_as_previous_activity` |  | The drive departs from the previous activity's place | boolean | `true` / `false` | `false` |
| `same_end_as_next_activity` |  | The drive arrives at the next activity's place | boolean | `true` / `false` | `false` |
| `description` |  | Anything the other fields don't cover | string | any text | `""` |
| `guidebook_pages` |  | Guidebook page(s) covering the drive | string | page numbers (`14`, `15-18`, `16, 23, 25-30`) | `""` |
| `activities` |  | Nested meals (a stop along the drive) | array | `meal` objects, each with a `type` (see below) | `[]` |

A drive is its **legs**: one hop each, in travel order, carrying the places, the
driving time, the distance and the route. There is no `start`, `coordinate`,
`waypoints` or `off_road` on the road itself — the departure is the first leg's
`start_location`, the arrival the last leg's `end_location`, and the drive counts
as off-road only when **every** one of its legs does. A plain A → B drive is a
one-leg road, so there is exactly one shape to write.

`description` is free prose for what the structured fields can't say — the state
of the road, a scenic stretch, a pass that closes in winter, a toll or a ferry
crossing. Both renderers print it under the drive's meta line and **above** the
`VIA` leg list; leave it out when the legs already tell the story.

#### `leg` — one hop of a drive

| Field | Required | Description | Type | Format | Default |
| ----- | -------- | ----------- | ---- | ------ | ------- |
| `start_location` | ✅ on the first leg | Where the hop departs from | string | any text | the previous leg's `end_location` |
| `start_coordinate` |  | The departure point on the map | object | `{ "lat": .., "long": .. }` | the previous leg's `end_coordinate` (geocoded from the name on the first leg) |
| `end_location` | ✅ on the last leg | Where the hop arrives | string | any text | the next leg's `start_location` |
| `end_coordinate` | ✅ unless deducible | The arrival point on the map | object | `{ "lat": .., "long": .. }` | the next leg's `start_coordinate` |
| `duration` |  | Driving time for this hop | string | duration (`1h30`, `45 min`) | none |
| `distance_km` |  | Driving distance for this hop | number | positive number | none |
| `off_road` |  | This hop runs off-road | boolean | `true` / `false` | `false` |
| `waypoints` |  | Points the hop's route bends through, in order | array | array of `{ "lat": .., "long": .. }` coordinates | `[]` (a straight route between the hop's ends) |
| `gpx` |  | A recording of this hop, drawn as its line on the map | string | the `.gpx` file base64-encoded (gzip allowed) | none (the line is routed) |

**A junction is written once.** Two consecutive legs meet at one place, so
either side may name it: a leg's `start_location` / `start_coordinate` fall back
to the previous leg's `end_*`, and its `end_location` / `end_coordinate` to the
next leg's `start_*`. What no leg names is an **error** — the drive would have a
hole in it — so the first leg must give its own departure and the last its own
arrival. Where both sides state it, the **earlier leg's `end_*` wins**, and
validation warns when the two disagree (a differing name, or coordinates a
kilometre or more apart): the drive can't jump between the two.

The first leg's `start_*` and the last leg's `end_*` are the two ends the chain
can't fill in — unless the road sets
[`same_start_as_previous_activity` / `same_end_as_next_activity`](#a-drive-that-shares-an-end-with-its-neighbour),
which hand that end to the neighbouring **activity** instead.

The departure *coordinate* is the one point that stays optional: with maps on it
is geocoded from `start_location` when absent (and
[`geocode`](README.md#geocode--bake-in-coordinates) fills every endpoint of every
leg). Every other point of the route is plotted from its coordinate, so those
must resolve. The map draws the whole chain — first departure → each leg's
waypoints → each leg's arrival — with a full-opacity accent disc on the departure
and on each leg's arrival; the route-shaping `waypoints` bend the drawn route
without a disc of their own.

Each leg is a row under the road in the PDF (in a lower accent), reading
`from → to` with its own duration / distance and a **(Navigate)** link — but the
list is omitted for a **one-leg** road, since the drive *is* that hop and the
title already shows all of it. If the leg `duration`s sum to more than the road's own `duration`,
validation warns (the leg times can't fit the drive). A leg with no `duration` or
no `distance_km` warns too, naming the hop.

**Off-road, per hop.** `off_road` belongs to a leg, so a drive that is paved to
the village and rough for the last 5 km flags that leg alone: its row carries a
small `OFF-ROAD` chip after the duration/distance, in the PDF and the viewer
alike. A drive whose **every** leg is off-road also prints the `OFF-ROAD
SECTIONS` chip beside the title, since the whole of it leaves the tarmac. That
covers the **one-leg** drive, which has no row list to hang a flag on: its
leg's flag is the drive's.

#### Pinning a drive's own points

A drive is drawn as a **route**, not as pins: with maps on, its line runs from
the departure through every leg, with a small accent disc on each named point.
The three `display_*_on_maps` switches additionally give those points a
**numbered pin**, joining the day's `1..N` sequence in timeline order (so a
pinned drive shifts the numbers of everything after it):

| Switch | Pins | Default |
| ------ | ---- | ------- |
| `display_start_on_maps` | the very first `start_location` | `false` |
| `display_intermediate_point_on_maps` | every junction between two legs | **`true`** |
| `display_end_on_maps` | the very last `end_location` | `false` |

**The junctions are pinned by default; the two ends are not.** Splitting a drive
at a place is what says the place matters, and a junction has nothing else on the
page to identify it — so a multi-leg drive numbers its junctions unless you set
`display_intermediate_point_on_maps` to `false`. The two ends are usually the
activity before and the activity after (you leave the château and arrive at the
hotel), which already carry numbers of their own; pinning them by default would
put two on one place. Say they're the same place with
[`same_start_as_previous_activity` / `same_end_as_next_activity`](#a-drive-that-shares-an-end-with-its-neighbour)
instead, and set an end's switch only for a departure or arrival that really is
a place of its own.

Turn on all three and **every named point of the drive is pinned**. As with any
other pin, a point whose coordinate says `"show_on_map": false` is left out, and
each pin's number is shown as an accent disc **beside the place it points at**:
the departure's on the drive's title, each arrival's on that leg's row — and on
a **one-leg** drive, which prints no leg row, the arrival's disc sits mid-title
(`Tours → (1) Château de Chambord`), so the number still reads against its own
place.

#### A drive that shares an end with its neighbour

Most drives on a day begin where the last activity left you and end where the
next one starts: you leave the château you just visited and drive to the town
you're about to walk around. Two switches say so — both **off** by default:

| Switch | Says |
| ------ | ---- |
| `same_start_as_previous_activity` | the drive departs from the **previous** activity's place |
| `same_end_as_next_activity` | the drive arrives at the **next** activity's place |

Each does two independent things.

**It fills the endpoint in.** That leg endpoint becomes optional: leave the first
leg's `start_location` / `start_coordinate` or the last leg's `end_location` /
`end_coordinate` out and they are taken from that activity — its name and its
`coordinate`. This is a *fallback*: an endpoint you write yourself still wins, so
you can name the drive's end "Amboise — car park" while the visit is "Château
d'Amboise".

**It shares the map pin.** That end never takes a number of its own — it wears
the neighbouring activity's, on the map and in the day's itinerary alike. One
place keeps one number, which is the reason to set the switch even when you spell
the endpoint out. The matching `display_*_on_maps` switch then adds nothing
(validation says so as an info); the pin still appears, as the neighbour's.

The "previous / next activity" is the one written next to the drive in `activities`,
**skipping buffers** — free time is a length, not a place, so `[museum, 45 min
buffer, drive]` departs from the museum. Three things are **errors**:

* there is no previous / next activity at all (the drive is first or last in the
  day) — the switch has nothing to resolve against;
* that activity names no place (an unnamed meal, say) and the leg doesn't either;
* for an arrival only: that activity has no `coordinate` and the last leg has no
  `end_coordinate`. A drive's arrival is a point on the drawn route, so it has to
  be located — the same requirement the last leg always carried.

Drives are settled in order, so one drive can hand its arrival to the next
drive's departure. Two drives each pointing at the other resolve to nothing and
error: neither states the junction they share.

The whole-trip map is unaffected: there a pin carries the **day**, not the stop,
and it already shows every named road point.

#### Recording a leg (`gpx`)

A leg may carry a `gpx` — the file base64-encoded, gzip allowed, stored exactly
like [a hike's](#a-hikes-gpx-track). It is used for one thing: **that leg's line
on the map** is the recording instead of the routed guess, so the drawn route
follows the road you actually took (a forest track, a pass, a detour no router
knows). The leg's `waypoints` become unnecessary — the recording already runs
through them.

Unlike a hike's, a leg's track is **never drawn as a figure of its own**: no
trail map, no elevation profile, and a file with no elevations in it is no loss
here. `defaults.include_hike_maps` governs hikes only; attaching a `gpx` to a leg
is itself the opt-in, and with maps off it simply draws nothing (validation says
so). The viewer offers the file back on the leg's row — **(Get GPX track)**,
byte-for-byte what you attached — which paper has no twin for.

A leg *without* a `gpx` gets a different link there: **(Build GPX file)**, which
asks the app to write one from the line the map draws for that leg. Two things
follow from where it comes from. It is a **route** (`<rte>`), not a track — the
geometry was computed, not recorded, and calling it a track would hand your GPS a
journey that never happened. And it needs a real route: when the router can't be
reached the link reports that instead of handing back the straight line the map
would draw, because a crow-flight line between two towns is a wrong route rather
than a rough one. Nothing is written into your JSON either way — the file is
built on the click and downloaded.

### `point_of_interest` — a specific place

| Field | Required | Description | Type | Format | Default |
| ----- | -------- | ----------- | ---- | ------ | ------- |
| `name` | ✅ | Point-of-interest name | string | any text | — |
| `category` |  | Kind of place, shown as the badge | string | `museum` \| `church` \| `building` \| `viewpoint` \| `ruins` \| `castle` \| `temple` \| `street` \| `natural park` \| `mountain` \| `mountain pass` \| `lake` \| `beach` \| `waterfall` \| `canyon` \| `spring` \| `market` \| `other` | `"other"` |
| `address` |  | Address | string | any text | `""` |
| `description` |  | Description | string | any text | `""` |
| `guidebook_pages` |  | Guidebook page(s) covering it | string | page numbers (`14`, `15-18`, `16, 23, 25-30`) | `""` |
| `website` |  | Link to the venue's website, shown as a clickable link | string | a link like `https://example.com` | `""` |
| `opening_days` |  | The days it opens | string | weekday names / ranges (`tue-sun`, `mon-fri, sun`) | every day |
| `opening_hours` |  | The hours it opens, optionally per weekday | string | `HH:MM-HH:MM` ranges (`09:30-18:00`, `09:30-12:30, 14:00-18:00`), or `;`-separated day-prefixed groups (`mon-sat 09:00-17:00; sun 10:00-17:00`) | all day |
| `activities` |  | Nested points of interest, hikes and meals | array | `point_of_interest`, `hike` or `meal` objects, each with a `type` (see below) | `[]` |

**Opening days and hours.** Both are compact strings, so a guidebook line
transcribes as it stands rather than being taken apart into an object:

* `opening_days` — single days and/or ranges, comma-separated, case-insensitive,
  full English names or three-letter abbreviations: `"tue-sun"`,
  `"monday-friday, sunday"`, `"wednesday"`. A range may wrap the week
  (`"sat-mon"` is Sat, Sun, Mon). Leaving it out means **every day** — not
  "unknown": a sight with no stated closing day is one you can turn up at.
* `opening_hours` — one or more `HH:MM-HH:MM` ranges: `"09:30-18:00"`,
  `"09:30-12:30, 14:00-18:00"`. Keep the midday closure as **two ranges**; that
  is what lets a visit be caught straddling it. A range whose close is *before*
  its open crosses midnight (`"18:00-02:00"`). Leaving it out means **all day**.

  The hours may also **differ by weekday**, written as `;`-separated groups each
  optionally prefixed with the days it applies to:
  `"mon-sat 09:00-17:00; sun 10:00-17:00"`. No punctuation is needed between the
  days and the times — a day spec never contains a digit, and a time range
  always starts with one. A group naming **no** days is the default for every day
  no other group names, so `"09:00-17:00; sun 10:00-17:00"` reads as "9-5, but
  10-5 on Sundays". Two groups may not name the same weekday, and there may be at
  most one default group: either would leave a day's hours ambiguous, and both
  are errors.

  When `opening_days` is absent but the hours name weekdays, **those become the
  open days** — `"mon-fri 09:00-17:00"` alone says the place is shut at the
  weekend. A default group leaves the set empty, since it applies to every day
  and claims none in particular.

Both renderers print what is known under the address, as `Open   Tue–Sun  ·
09:30–12:30, 14:00–18:00` (localized weekday names; the hours are digits, so
they read the same in both languages), and the calendar export packs it as an
`Open:` line. Per-weekday hours are drawn as one part per group instead —
`Open   Mon–Sat 09:00–17:00  ·  Sun 10:00–17:00` — because the overall day run
says nothing about which hours belong to which day. Neither renderer flags a visit falling *outside* the opening —
**validation** does, with two warnings that read the day's *resolved* timeline
(so a visit whose start time was inferred is checked like any other):

* the visit lands on a weekday the place doesn't open;
* the visit doesn't fit inside a single opening range — checked against **that
  day's** group when the hours differ by weekday, and the warning quotes those
  hours rather than the union of every day's.

A nested stop is never put on the timeline, so it has no resolved time — the
closed-day check still applies to it, the hours check can't.

### `place` — a place (a town, say) grouping several nested activities

| Field | Required | Description | Type | Format | Default |
| ----- | -------- | ----------- | ---- | ------ | ------- |
| `name` | ✅ | Place name | string | any text | — |
| `description` |  | Description | string | any text | `""` |
| `guidebook_pages` |  | Guidebook page(s) covering the area | string | page numbers (`14`, `15-18`, `16, 23, 25-30`) | `""` |
| `activities` |  | Nested points of interest, hikes and meals | array | `point_of_interest`, `hike` or `meal` objects, each with a `type` (see below) | `[]` |

**A place lasts what it contains.** A place has no length of its own — it *is*
what you do there — so when it gives neither a `duration` nor an `end_time`, its
duration defaults to the **sum of its nested activities'** durations (each taken
from its own `duration`, or from its `start_time`/`end_time` span; nested items
that say nothing add nothing). That total then chains into the day's timeline
like any other duration, so a town with three timed visits no longer collapses to
a zero-minute row. It's a default, not a cap: an explicit `duration` (or an
`end_time`) still wins — but set one *below* the nested total and validation
warns, since the nested activities can't all fit inside it. This applies to
`place` alone; a `point_of_interest` has a visit length of its own beyond
whatever is nested under it.

`road`, `hike`, `place` and `point_of_interest` may each carry an `activities`
array of nested activities. Every entry must be an object with an explicit
`type`, and the allowed types depend on the container: `place` and
`point_of_interest` accept `point_of_interest`, `hike` or `meal`; `road` and
`hike` accept `meal` only. A missing or disallowed `type` is an error. Nesting is
only **one level deep** — a nested activity that carries its own `activities` is
a validation error.

### `hike`

| Field | Required | Description | Type | Format | Default |
| ----- | -------- | ----------- | ---- | ------ | ------- |
| `name` | ✅ | Hike name | string | any text | — |
| `description` |  | Description | string | any text | `""` |
| `guidebook_pages` |  | Guidebook page(s) covering the hike | string | page numbers (`14`, `15-18`, `16, 23, 25-30`) | `""` |
| `distance_km` |  | Distance | number | positive number | none |
| `elevation_m` |  | Elevation gain | number | positive number | none |
| `start` |  | Trailhead address | string | any text | `""` |
| `end` |  | End address | string | any text | `""` |
| `route` |  | Route shape | string | `loop` \| `back_and_forth` \| `one_way` | `"back_and_forth"` |
| `gpx` |  | The trail's GPX file, drawn as a trail map + elevation profile | string | the `.gpx` file base64-encoded (gzip allowed) | none |
| `activities` |  | Nested meals (a stop along the hike) | array | `meal` objects, each with a `type` (see below) | `[]` |

**Distances and climbs are rounded when shown.** Write the figure you have —
nothing rewrites your file — but the book, the viewer and the calendar export all
print it rounded, since a routed distance and an altimeter's ascent are estimates
and the useful precision falls off with the magnitude. A **distance** shows to
0.1 km below 10 km, to 0.5 km up to and including 20 km, and to whole km above it
(so `12.3` prints as `12.5 km`, `345.7` as `346 km`). A **climb** shows to 5 m
below 100 m and to 10 m from there up (`47` → `45 m`, `784` → `780 m`). This
applies to a road's and a leg's `distance_km` too.

For a `loop` / `back_and_forth` hike, `end` should equal `start` (or be omitted)
— validation warns otherwise; for a `one_way` hike, `end` should differ from
`start` — validation warns if it's missing or the same.

#### A hike's GPX track

Attach the trail itself and both renderers draw it: a **trail map** over the same
basemap the other maps use, and an **elevation profile** under it. `gpx` holds the
`.gpx` file base64-encoded, so the track travels inside the itinerary — nothing is
fetched, and the profile works offline.

```bash
base64 -i gaube.gpx | tr -d '\n'          # paste the result as "gpx"
gzip -9 -c gaube.gpx | base64 | tr -d '\n'  # ~10× smaller, also accepted
```

A `data:` URI prefix is stripped and line-wrapped base64 is fine, so most ways of
producing the string work. In the viewer's **Edit** tab the `gpx` field is a file
picker that does the encoding (and the gzipping) for you.

Track points (`<trkpt>`) are preferred; a file with none falls back to route
points (`<rtept>`), then plain waypoints (`<wpt>`), and multiple `<trkseg>`s are
one continuous trail. The distance and the elevation gain are measured off the
**full-resolution** recording and **fill in** `distance_km` / `elevation_m` when
you leave those out — give them explicitly and yours win, so you can quote the
guidebook's round numbers over the GPS's. Elevation gain is smoothed and
accumulated with hysteresis, so an altimeter's metre-scale wobble doesn't add up
to phantom climb. A file without elevations still draws its map; it just has no
profile.

`defaults.include_hike_maps` (default **on**) switches the pair off. It is
deliberately independent of `include_maps_in_render`: that one governs the maps
inferred for the whole trip, while a GPX is a file you attached to one hike —
attaching it *is* the opt-in. With the switch off the track isn't even sent to the
viewer, so the geometry costs nothing.

One difference between the two renderers, and it's on purpose: the PDF embeds a
rendered raster map, the viewer draws the interactive one (the geometry is already
in hand, so it appears with the text rather than with the per-day map render) and
follows the **Options → interactive maps** toggle — with that off, the profile
stands alone.

In the viewer the hike also gets a **`(Get GPX track)`** link beside its other
inline links, which downloads the `.gpx` — the bytes you attached, byte-for-byte
(inflated back from gzip where it was stored that way), not a re-export of the
simplified line the map draws. So the file can go straight to a watch, a GPS or
another app. It's screen-only: paper can't hand back a file.

### `meal` — a stop to eat

A meal is scheduled like any other activity (the shared `start_time` /
`end_time` / `duration` fields above) but rendered compactly, like a slightly
accented buffer row rather than a full card — e.g. **Lunch at Le Magret**. A
named restaurant is also listed in the cover overview's highlights.

`meal_type` is optional. If omitted it is inferred from the start time —
**breakfast** before `defaults.breakfast_until` (10:00), **lunch** up to
`defaults.lunch_until` (16:00), **dinner** after (lunch when there's no start
time at all). Those two thresholds are configurable per trip in the `defaults`
object. `brunch`, `snack`, `picnic` and `meal` are also valid but are **never
inferred** — set them explicitly.

If a meal gives no `duration`/`end_time`, it uses `defaults.meal_duration` (0 —
instant — unless you set one).

The head shows the restaurant when named (**Lunch at Les Deux Palais**); otherwise it
falls back to `area` (**Picnic near Limoges**), or just the meal type. Setting
both `restaurant` and `area` triggers a validation warning — `area` is ignored
when a restaurant is named.

| Field | Required | Description | Type | Format | Default |
| ----- | -------- | ----------- | ---- | ------ | ------- |
| `meal_type` |  | Which meal it is | string | `breakfast` \| `lunch` \| `dinner` \| `brunch` \| `snack` \| `picnic` \| `meal` (last four explicit-only) | inferred from `start_time` |
| `restaurant` |  | Restaurant name | string | any text | `""` |
| `area` |  | Town/region to eat in (used when no `restaurant` is named) | string | any text | `""` |
| `address` |  | Address | string | any text | `""` |

### `buffer` — free time between activities

A `0 min` buffer only suppresses the trip's default buffer at that spot (no line
drawn). A default buffer and an inferred gap that meet are merged into one. A
buffer you write yourself is never resized by `defaults.auto_sized_buffer`: it
states how long that particular pause is, so the spreading skips that gap.

| Field | Required | Description | Type | Format | Default |
| ----- | -------- | ----------- | ---- | ------ | ------- |
| `duration` | ✅ | Length of the free time | string | duration | — |

## `transport[]`

One **booking** and the **legs** it moves you over. What you reserve once — the
type, the reference, the price, the links, the status — sits on the booking;
where and when you actually travel sits in `legs`, one entry per hop. A
single-hop booking is a one-leg booking, not a special case: `legs` is required
and must hold at least one entry.

That split is what lets a round trip, or a flight with a connection, be the one
thing it is: one PNR, one price, one "Reservation" link, several movements.

Both renderers draw a booking as one card, in one of **two shapes**:

- **Several legs** — everything the reservation covers first (its `name`, type
  badge, status/payment, reference, `description`, price and links), then, under
  a grey rule, **one inset block per leg**, each badged `Leg 1`, `Leg 2`… beside
  its route. Shared information and per-hop information can't be mistaken for
  each other.
- **One leg** — a single flat block: no rule, no inset, no badge, because there
  is nothing to tell apart and the booking *is* that movement. Its route line is
  dropped when it would only repeat the heading, which is the usual case since an
  unnamed booking is headed with its route.

Each day's itinerary, meanwhile, shows only the legs that depart that day,
**enriched with the booking's shared fields**, so a day's row still carries its
type badge, reference and source without the booking around it.

**Two levels, two notes.** The booking's `description` is about the reservation —
a baggage allowance, a fare condition, a check-in window — and shows on the
transport card (and on every one of that booking's calendar events, as
`Booking note`). A leg's `description` is about that hop — a seat, a terminal, a
coach number — and shows under that leg, on the day's row and, for a sleep-aboard
leg, in the stay bar. Put each fact where it belongs and neither renderer repeats
it.

**The `name`** is what the card is headed with. Left out, it defaults to the
route through every leg — `New York JFK → Paris CDG → Toulouse-Blagnac → Paris
CDG → New York JFK` — where a connection is named once (leg 2 starting where leg
1 ended) but a break is not, since dropping either end would misdescribe the
booking. Set it to something shorter and truer when the chain gets long
("Round trip New York ↔ France").

A leg that spans midnight is treated as that night's accommodation (stay bar +
"sleep" column, `+1` on the arrival time). Its `start_time` is required; provide
one of `end_time` / `duration` and the other is inferred, across time zones when
they differ. A field written on the wrong side of the split is not read by the
model, so the validator warns and names the level it belongs to.

| Field | Required | Description | Type | Format | Default |
| ----- | -------- | ----------- | ---- | ------ | ------- |
| `type` |  | Transport kind, shown as the badge on the booking and its legs | string | `plane` \| `train` \| `bus` \| `taxi` \| `ferry` \| `other` | `"other"` |
| `name` |  | What to call the whole booking, shown as the card's heading | string | any text | the route through its legs (`A → B → C`) |
| `booking_number` |  | Reservation reference / PNR, covering every leg | string | any text | `""` |
| `booking_source` |  | Where it was booked | string | any text | `""` |
| `website` |  | Link to the carrier's website, shown as a clickable link | string | a link like `https://example.com` | `""` |
| `booking_link` |  | Direct link to this reservation, shown as a clickable link | string | a link like `https://example.com` | `""` |
| `status` |  | Reservation status, shown as a badge | string | `booked` \| `confirmed` | none (no badge) |
| `description` |  | A short note about the **whole booking** (a baggage allowance, a fare condition) | string | any text | `""` |
| `price` |  | Price of the whole booking, every leg included (amount only, no symbol) | number | number | none (not shown) |
| `currency` |  | Currency this price is in | string | 3-letter ISO code | `defaults.currency` |
| `paid` |  | Payment state, shown as a badge | string or boolean | `paid` \| `to pay` (or `true` / `false`) | none (no badge) |
| `legs` | ✅ | The hops this booking moves you over | array | non-empty array of leg objects | — |

### `transport[].legs[]`

One hop: where it goes, when, its own number and its own note. An optional
`description` carries a short note the structured fields don't — a seat, a
terminal, a baggage allowance — drawn as prose under that leg's number, both on
the transport page and on the day's row. It is per leg because an outbound and a
return rarely share a seat. An overnight leg also fills that night's stay bar,
which leaves the note to the itinerary row above rather than printing it twice.

| Field | Required | Description | Type | Format | Default |
| ----- | -------- | ----------- | ---- | ------ | ------- |
| `start` | ✅ | Departure address | string | any text | — |
| `end` | ✅ | Arrival address | string | any text | — |
| `start_date` | ✅ | Departure date; slots the leg into that day | string | `YYYY-MM-DD` | — |
| `end_date` |  | Arrival date | string | `YYYY-MM-DD` | inferred (+1 day if it crosses midnight) |
| `start_time` | ✅ | Departure time | string | `HH:MM` | — |
| `end_time` |  | Arrival time | string | `HH:MM` | inferred (`start_time + duration`) |
| `start_tz` |  | Departure time zone | string | UTC offset | `defaults.timezone` |
| `end_tz` |  | Arrival time zone | string | UTC offset | `defaults.timezone` |
| `duration` |  | Travel time | string | duration | inferred from the two times |
| `flight_number` |  | Flight number of this leg (planes only) | string | any text | `""` |
| `train_number` |  | Train number of this leg (trains only) | string | any text | `""` |
| `distance_km` |  | How far this leg covers, in km | number | a number (`200`, `30.5`) | none (no distance shown) |
| `description` |  | A short note about this leg (a seat, a terminal, a baggage allowance) | string | any text | `""` |
| `start_coordinate` |  | Departure point, for the maps | object | `{lat, long}` | none (never geocoded) |
| `end_coordinate` |  | Arrival point, for the maps | object | `{lat, long}` | none (never geocoded) |

## `accommodations[]`

Where you sleep, rendered as a summary page plus a bottom bar on each covered
day. A stay covers nights from `arrival` up to (but not including) `departure`,
so the checkout day shows no bar. An optional `description` carries a short note
the structured fields don't — drawn in full under the contact line on the
summary page, and in the day's stay bar (capped at two lines in the PDF, since
the bar is pinned near the page foot; the viewer clamps it instead).

| Field | Required | Description | Type | Format | Default |
| ----- | -------- | ----------- | ---- | ------ | ------- |
| `name` | ✅ | Accommodation name | string | any text | — |
| `arrival` | ✅ | Check-in date | string | `YYYY-MM-DD` | — |
| `departure` | ✅ | Check-out date | string | `YYYY-MM-DD` | — |
| `city` | ✅ | Town shown in the cover overview | string | any text | — |
| `type` |  | Kind of accommodation | string | `hotel` \| `camping` \| `b&b` \| `other` | `"hotel"` |
| `address` |  | Street address | string | any text | `""` |
| `contact` |  | Phone or email | string | any text | `""` |
| `booking_source` |  | Where it was booked | string | any text | `""` |
| `website` |  | Link to the property's website, shown as a clickable link | string | a link like `https://example.com` | `""` |
| `booking_link` |  | Direct link to this reservation, shown as a clickable link | string | a link like `https://example.com` | `""` |
| `status` |  | Reservation status, shown as a badge | string | `booked` \| `confirmed` | none (no badge) |
| `description` |  | A short note for whatever the other fields don't cover (a door code, where to park, which bell to ring) | string | any text | `""` |
| `price` |  | Price for the whole stay (amount only, no symbol) | number | number | none (not shown) |
| `currency` |  | Currency this price is in | string | 3-letter ISO code | `defaults.currency` |
| `paid` |  | Payment state, shown as a badge | string or boolean | `paid` \| `to pay` (or `true` / `false`) | none (no badge) |
| `breakfast_included` |  | Show a "Breakfast included" line | boolean | `true` / `false` | `false` |

## `car_rentals[]`

A rental-car booking, rendered under the transport page, with its **pick-up**
and **drop-off** also woven into their days' itineraries (on `pickup_date` /
`dropoff_date`, at their times). The booking runs from a start datetime to an
end datetime; the pick-up and drop-off datetimes must fall inside that window —
validation errors otherwise (and the drop-off must not precede the pick-up). A
pick-up or drop-off that overlaps an activity or transport on the same day is a
validation warning. Each of the four times takes an optional UTC offset that
falls back to `defaults.timezone`; a tz label is only shown when it differs. The
drop-off location defaults to the pick-up location. An optional `description`
carries a short note the structured fields don't — drawn under the card's meta
line, and repeated on **both** the pick-up and drop-off rows woven into their
days, since that is where you read it.

| Field | Required | Description | Type | Format | Default |
| ----- | -------- | ----------- | ---- | ------ | ------- |
| `booking_start_date` | ✅ | Booking start date | string | `YYYY-MM-DD` | — |
| `booking_start_time` | ✅ | Booking start time | string | `HH:MM` | — |
| `booking_end_date` | ✅ | Booking end date | string | `YYYY-MM-DD` | — |
| `booking_end_time` | ✅ | Booking end time | string | `HH:MM` | — |
| `pickup_date` | ✅ | Pick-up date (must be within the booking period) | string | `YYYY-MM-DD` | — |
| `pickup_time` | ✅ | Pick-up time | string | `HH:MM` | — |
| `dropoff_date` | ✅ | Drop-off date (must be within the booking period) | string | `YYYY-MM-DD` | — |
| `dropoff_time` | ✅ | Drop-off time | string | `HH:MM` | — |
| `pickup_location` | ✅ | Where you pick up the car | string | any text | — |
| `dropoff_location` |  | Where you drop off the car | string | any text | the pick-up location |
| `booking_start_tz` |  | Booking-start time zone | string | UTC offset | `defaults.timezone` |
| `booking_end_tz` |  | Booking-end time zone | string | UTC offset | `defaults.timezone` |
| `pickup_tz` |  | Pick-up time zone | string | UTC offset | `defaults.timezone` |
| `dropoff_tz` |  | Drop-off time zone | string | UTC offset | `defaults.timezone` |
| `company` |  | Rental company | string | any text | `""` |
| `booking_number` |  | Reservation reference | string | any text | `""` |
| `website` |  | Link to the rental company's website, shown as a clickable link | string | a link like `https://example.com` | `""` |
| `booking_link` |  | Direct link to this reservation, shown as a clickable link | string | a link like `https://example.com` | `""` |
| `status` |  | Reservation status, shown as a badge | string | `booked` \| `confirmed` | none (no badge) |
| `description` |  | A short note for whatever the other fields don't cover (the insurance excess, a fuel policy, where the desk is) | string | any text | `""` |
| `price` |  | Rental price (amount only, no symbol) | number | number | none (not shown) |
| `currency` |  | Currency this price is in | string | 3-letter ISO code | `defaults.currency` |
| `paid` |  | Payment state, shown as a badge | string or boolean | `paid` \| `to pay` (or `true` / `false`) | none (no badge) |
| `car_type` |  | Car category, shown as the badge | string | `regular` \| `small` \| `SUV` \| `4x4` | `"regular"` |
| `car_model` |  | Car make/model | string | any text | `""` |
| `contact` |  | Phone or email for the rental company | string | any text | `""` |
| `additional_drivers` |  | Number of additional drivers | number | whole number ≥ 0 | `0` |
| `pickup_duration` |  | How long the pick-up takes | string | duration | none (not shown) |
| `dropoff_duration` |  | How long the drop-off takes | string | duration | none (not shown) |
