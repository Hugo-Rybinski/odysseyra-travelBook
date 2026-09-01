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

**Settle the language before you write anything.** The JSON is full of prose you
author — `title`, `subtitle`, `summary`, every day's `title`/`description`, every
activity `name`/`description`. All of it must be in **one** language, the one the
book will be rendered in. **If the language to use is unclear — the sources are
in one language and the request in another, the sources are themselves mixed, or
nothing states it — stop and ask the user which language to write in before
proceeding.** Do not guess, and do not silently default to the sources' language.
JSON **keys** and enum values are always English (`point_of_interest`, `loop`,
`hotel`, …), and proper nouns, booking references and addresses stay exactly as
the sources print them — the choice only governs the prose you write.

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
  "misc":               { ... },   // object — reference data off the timeline (all optional)
  "days":               [ ... ],   // array  — REQUIRED, non-empty; one entry per day, in order
  "transport":          [ ... ],   // array  — inter-city bookings, each with its "legs"
  "accommodations":     [ ... ],   // array  — places you sleep
  "car_rentals":        [ ... ]    // array  — rental-car bookings
}
```

- Only `days` is required (non-empty). Every other key may be omitted.
- Note the exact key names: **`transport`** is singular, **`car_rentals`** uses
  an underscore, **`accommodations`** is plural.
- `title` (and the other `travel_description` fields) may also sit at the top
  level instead of inside `travel_description`, but the grouped form is cleaner —
  prefer it. **`misc` is different**: its contents are read from inside `misc`
  only, so never hoist `emergency_contacts` to the top level.
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
| `summary` | no | text | none | **Write one.** The paragraph on the cover: a 4–6 sentence overview that sells the trip — see below. |
| `cover_color` | no | hex color (`"#2f6b4f"`) | `"#1f4e5f"` (teal) | Accent color for the whole PDF. |
| `start_date` | no | date `YYYY-MM-DD` | inferred (earliest date in the trip) | Only set if the source states an explicit trip start; otherwise omit and let it be inferred. |
| `end_date` | no | date `YYYY-MM-DD` | inferred (latest date in the trip) | Same — omit unless explicitly given. |

**Always write a `summary`, and make it sell the trip.** It is the only prose on
the cover and the first thing anyone opening the book reads, so give it **4–6
sentences** that make the reader want to go. A shape that works: open with the
trip's arc (where it goes, over how many days, by what means), move through its
two or three high points in the order the trip meets them, and close on the note
it ends on.

> `"A week across France, from the museums and boulevards of Paris to the high
> Pyrenees. The first days are city days on foot — the Louvre, the river, the
> quarters between them — before the TGV south and a hire car for the Renaissance
> châteaux above the Loire. The road then runs down to the Dordogne, to medieval
> Sarlat, its market streets and the painted caves nearby. The last two days
> climb: a base at Lourdes, the Col du Tourmalet, and a proper mountain hike
> above the valley. It ends where the mountains do, flying out of Toulouse."`

This is the **one place in the whole document where evocative writing belongs**. A
day's `description` may only re-state that day's own activities, flatly (see
*Always give every day a `description`*); the summary is allowed to step back and
characterise the trip as a whole, because it is a cover blurb rather than a
schedule. What does *not* change:

- **No facts from outside the itinerary.** Enticing is a matter of *how* you
  write the places, days and legs already in the JSON — not of adding history, a
  site's importance, what a region is famous for, prices or hours you happen to
  know. If it is nowhere in the trip you built, it is not in the summary.
- **Say what the trip does, not what the reader will feel.** No promises
  (`"you'll never forget"`), and no verdict on the pacing (`"a relaxed week"`,
  `"an ambitious loop"`) unless a source used those words — the same rule the day
  intros follow.
- **No brochure filler.** "Unforgettable", "trip of a lifetime", "hidden gem",
  "must-see", "breathtaking", "immerse yourself", "nestled" — cut them all. A
  sentence that would fit any itinerary in the world is a wasted sentence.
  Concrete nouns sell harder than adjectives: *"Renaissance châteaux above the
  Loire"* beats *"stunning historic castles"*.
- **Don't march through the days and don't list the towns.** No `"Day 1 … Day 2
  …"`, and no comma-separated run of every stop: the day-by-day table is printed
  on the same page directly underneath, and the trip's own days follow it.
- **Don't shorten it to save room on the page.** The cover grows to fit and the
  day-by-day table flows onto a second page if it must. Do stop at six sentences
  though — it's a cover, not an introduction.
- **Keep it distinct from `subtitle`.** The tagline goes there; don't open the
  summary by restating it, or the title.
- The language rule at the top of this document applies, as does *A description
  is for the traveller* below — which names the `summary` explicitly: no sources,
  no process, no guidebook pages, no `[to be checked]`.

---

## `defaults` (object)

Trip-wide defaults that fill gaps. **Entirely optional** — omit it and every
field takes its default. Only set a field when the source implies a global
setting (e.g. "all times are local Paris time (UTC+2)" or "we start at 9am").

| Field | Required | Format | Default | Notes |
|---|---|---|---|---|
| `start_time` | no | time `HH:MM` | `"08:00"` | When the first activity of each day begins if it gives no start. |
| `end_time` | no | time `HH:MM` | `"18:00"` | Where each day's last activity should land: the buffers are sized to spread the day out to it, and `validate` warns about anything ending later. |
| `auto_sized_buffer` | no | boolean | `true` | Size the buffers between a day's activities so the day ends on `end_time` (in 5-minute steps). Leave it out unless the source wants a fixed break instead. |
| `buffer` | no | duration (`"15 min"`) | `0` (none) | A **fixed** break between consecutive activities. **Ignored** while `auto_sized_buffer` is on, so only set it together with `"auto_sized_buffer": false` — setting both is a validator warning. |
| `timezone` | no | UTC offset (`"+02:00"`, `"UTC-3"`, `"Z"`) | `GMT` (UTC+0) | The default offset for every time in the trip that gives none. |
| `breakfast_until` | no | time `HH:MM` | `"10:00"` | A meal with no `meal_type` starting at/before this is a **breakfast**. |
| `lunch_until` | no | time `HH:MM` | `"16:00"` | A meal starting after breakfast and at/before this is **lunch**; later is **dinner**. |
| `meal_duration` | no | duration (`"1h"`) | `0` | Default length of a meal that gives neither a duration nor an end time. |
| `accommodation_start_time` | no | time `HH:MM` | `"22:00"` | Evening clock time each accommodation night starts on the calendar (`ics` export only). |
| `accommodation_end_time` | no | time `HH:MM` | `"00:00"` | Clock time each accommodation night ends on the calendar (`ics` export only); midnight by default. |
| `currency` | no | 3-letter ISO code | `"EUR"` | The currency every price is in unless the price sets its own `currency`. |
| `secondary_currencies` | no | array of `{currency, change_rate}` | `[]` | Extra currencies each price is *also* shown in on the PDF (converted from the default). |
| `include_maps_in_render` | no | boolean | `false` | Draw a per-day OpenStreetMap with a pin for each located activity. |
| `include_hike_maps` | no | boolean | `true` | Draw the trail map + elevation profile of any hike that carries a `gpx`. Independent of `include_maps_in_render` (attaching the GPX is the opt-in). Leave it out unless you are switching it off. |
| `infer_coordinates_from_address` | no | boolean | `false` | Geocode activities that have no explicit `coordinate`. When false, only activities with a `coordinate` appear on the map. |
| `inference_countries` | no | array of 2-letter ISO codes | `[]` (any) | Restrict geocoding to these countries, e.g. `["FR"]`. Only used when inference is on. |
| `show_moon_phase` | no | boolean | `true` | Show the night's moon phase (emoji + name). With `show_sun_times` on too it closes that line (`☀️ Sunrise: 07:12, Sunset: 20:27, 🌕 Full moon`); otherwise it sits in each day's "tonight" section. Set `false` to hide it. |
| `show_sun_times` | no | boolean | `true` | Show each day's sun times (`☀️ Sunrise: 06:12, Sunset: 21:34`) in its header band. Computed offline and read in `timezone`'s wall clock, so it needs no extra data — set it to `false` only to hide the line. The sunset uses that night's accommodation `coordinate` (else the day's *last* located stop); the sunrise uses the *previous* night's stay (else the day's *first* located stop). A day whose location is more than 3 h of solar time from `timezone` shows none, so give a day abroad its real `start_tz`. |

**`secondary_currencies`.** Each entry is `{"currency": "<ISO code>",
"change_rate": <number>}`. The `change_rate` is **units of that currency per one
unit of the default currency** — with a `EUR` default, `{"currency": "USD",
"change_rate": 1.09}` means 1 € = $1.09. On the PDF every price is printed in the
default currency followed by each secondary conversion in parentheses (e.g.
`€612 ($667, £520)`).

---

## `misc` (object — optional)

Trip-wide reference data that belongs to the whole trip but to **no point on its
timeline**. Everything here is optional, group included. One field so far:

| Field | Required | Format | Default | Notes |
|---|---|---|---|---|
| `emergency_contacts` | no | array of `{name, contact}` | `[]` | Who to call in an emergency where the trip goes — see below. |

### `emergency_contacts` (array)

Each entry is one number to reach:

| Field | Required | Format | Default | Notes |
|---|---|---|---|---|
| `name` | no | text | `""` | Who it reaches: the service, the embassy, the person. |
| `contact` | no | text | `""` | How to reach them: a phone number, an email, or an address. **Free text** — write it exactly as the country writes it. |

```json
"misc": {
  "emergency_contacts": [
    { "name": "Emergency — any service (EU-wide)", "contact": "112" },
    { "name": "SAMU — medical emergencies", "contact": "15" },
    { "name": "US Embassy, Paris — consular emergencies", "contact": "+33 1 43 12 22 22" }
  ]
}
```

**You may look these up — and you must then cite them.** This is the **second
and last** field you are allowed to fill from your own knowledge or from the web
rather than from the supplied documents (the first is a day's `bank_holiday`),
because no booking confirmation lists a country's ambulance number. It comes with
a hard condition:

- **Every value you did not take from a supplied document goes in the
  inconsistency report, with the URL you took it from** — see *Report what you
  looked up online* at the end of this document. One bullet per contact.
- **Not filling it is better than hallucinating it.** If you are not certain of a
  number, **leave that entry out**, or write the `name` alone and no `contact` —
  a half entry is valid, and it tells the traveller what to look up. An invented
  emergency number is the single most dangerous thing this file could contain.
- Prefer numbers that are **stable and verifiable**: the national/EU short codes
  (`112`, `15`, `17`, `18`, `999`, `911`, `102`/`103`), then the traveller's own
  embassy or consulate in the destination country.

What to fill it with, in this order:

1. Anything the **sources** state (an insurer's 24-hour line, a tour operator's
   emergency contact, the number on a rental voucher) — that needs no citation,
   like any other sourced field.
2. The **destination country's** emergency short codes.
3. The **traveller's embassy or consulate** in the destination country — only
   when the sources tell you the traveller's nationality (a passport, a
   departure airport, the language of the trip). Don't guess a nationality in
   order to add one.

Other rules:

- **Country of the trip, not of the traveller** — a trip to France lists French
  numbers. A trip crossing borders may list both, each `name` saying which
  country it is for (`"Emergency — Spain"`).
- **Write the `contact` as it is dialled locally.** A short code stays short
  (`112`, not `+33 112`); a full number keeps its international form
  (`+33 1 43 12 22 22`). Nothing parses the string, so no format is imposed.
- **The `name` says who, not how.** Keep it short enough to read at a glance and
  put the service first (`"SAMU — medical emergencies"`). No advice sentences, no
  URLs, no "call this if…".
- Leave the whole group out when you have nothing certain to put in it.

---

## `days` (array — REQUIRED, one entry per day, in order)

Each entry is one **day**: a title, optional date/city/intro, and an ordered
list of **activities**.

| Field | Required | Format | Default | Notes |
|---|---|---|---|---|
| `title` | **yes** | text | — | The day's headline (e.g. "Renaissance châteaux"). |
| `date` | no | date `YYYY-MM-DD` | trip start + this day's index | Set it if the source states the date; otherwise it's inferred from position. |
| `city` | no | text | none | City/region label (e.g. "Paris", or "Amboise → Sarlat-la-Canéda") — **always fill it**, see below. |
| `description` | no | text | none | An intro paragraph for the day — **always write one**, see below. |
| `bank_holiday` | no | `true` / `false` | `false` | `true` if the day is a **public holiday** in the country you're in — **look these up**, see below. |
| `activities` | **yes** | array (non-empty) | — | The ordered timeline — see below. |

**How to fill a day's `city`.** It is printed in the day's header band beside the
date, so it must be short — a place label, never a sentence. Fill it on **every**
day:

- **A day in one place** → that place alone: `"Paris"`.
- **A day you move** → `"Origin → Destination"` with a real arrow (`→`, U+2192),
  where the **destination is where you sleep**: `"Amboise → Sarlat-la-Canéda"`.
  Name only those two even if the drive passes through others — the road's
  legs carry the rest. Never chain three (`"A → B → C"`).
- **A day out of town that returns to the same base** → keep the **base town**,
  not the excursion: a day hiking in Ala Archa out of Bishkek is `"Bishkek"`, not
  `"Ala Archa National Park"`. Use an **area** name only when the day genuinely
  belongs to it rather than to a town (`"Cirque de Gavarnie"`).
- **A travel-only day** (you fly out and sleep aboard, or in transit) → where the
  day *starts*: france.json's departure day is `"New York"`.

**The night's accommodation city must appear inside it, spelled identically.**
`validate` compares the two as a *substring*, case-insensitively, and warns
`the day's city (…) doesn't match the accommodation city (…)` when the stay's
`city` is not contained in the day's. So if the stay's `city` is
`"Sarlat-la-Canéda"`, the day must say `Sarlat-la-Canéda` — `"Sarlat"` alone
triggers the warning. Only the arrival end is checked, so shortening the
*origin* is free: `"Sarlat → Cauterets"` is fine on the night you sleep in
Cauterets. A day with no stay at all (an overnight leg, a night train) is never
checked.

Keep out of `city`: dates, times, activity or hotel names, the country, and
region padding when a town name exists.

**Always give every day a `description`.** The field is optional to the tool, but
write one for **every** day: **1–2 sentences** that set the day up for the reader
at a glance. When the source supplies a day intro, use it. When it doesn't —
usually — **compose one from that day's own activities**: where the day goes, its
two or three anchors, and how it ends up.

> `"Morning in the châteaux above the Loire, then the long drive south to the
> Dordogne, arriving in Sarlat for dinner."`

Rules for the sentence you compose:

- **Only re-state what the day already contains.** It is a summary of the
  activities, transport legs and stay you have written — not a place to add a
  fact that appears nowhere else. Names, towns and times are fair game; opening
  hours, prices or history you happen to know are not.
- **No verdicts on the day.** Don't call it busy, packed, relaxed, ambitious,
  long, or well balanced, and don't advise pacing — unless a source says so in
  those terms.
- **Don't just list the titles.** The activities are printed right underneath;
  the intro should read like a sentence, not a comma-separated index of them.
- The language rule at the top of this document applies to it like any other
  prose, as does *A description is for the traveller* below.

**Set `bank_holiday` on every day that is one — and look them up.** This is the
**one fact you are expected to supply from your own knowledge** rather than from
the documents, because it is public, dated, and almost never mentioned in a
booking confirmation. Everywhere else, *Only include a field if the source
actually states it* still holds.

For each **dated** day, ask: is that date a **national public holiday in the
country the day is spent in**? If it is, set `"bank_holiday": true`. The renderers
then open the day with a ⚠️ banner about closures and reduced opening hours, so
the traveller sees it before planning around it.

- **Country of the day, not of the traveller.** A US traveller in Paris on 14
  July is on a French holiday; the same traveller in Paris on 4 July is not.
  On a day you change country, use the one you spend most of the day in.
- **A flag, not a name.** There is nowhere to put "Bastille Day" — the banner is
  identical whichever holiday it is. Name the holiday in the day's `description`
  only if a *source* mentions it; don't add it yourself (that would break the
  description rules above).
- **Only when you're sure of the date.** Movable holidays (Easter Monday,
  Ascension, Whit Monday, Eid, Chinese New Year) shift every year, and many
  countries have regional-only ones. If you can't place the date confidently for
  that specific year, **leave the field out** and list it in the gaps report
  (below) as "bank holidays not checked for <country>" — a wrong banner is worse
  than none.
- **Undated days get nothing.** A day whose `date` you left to inference has no
  date to check against, so omit the field.
- Substitute/observed days (a holiday falling on a Sunday and taken on the
  Monday) count as the holiday: flag the day people actually take off.

### Activities

`activities` is an ordered array of objects, each with a `type`. There are six
types. **Timing is usually inferred** — you rarely give every time:

- Provide **any two** of `start_time` / `end_time` / `duration` and the third is
  computed. Give one, or none, and the chain fills in.
- The first activity starts at the day's default start (`defaults.start_time`,
  else 08:00). Each next activity starts when the previous one ends.
- Gaps become **buffer** activities automatically — you seldom add those by
  hand. By default they are *sized* so the day's last activity lands on
  `defaults.end_time` (18:00), so a day with a few timed visits is spread out
  rather than packed into the morning. A `start_time` you write is never moved
  by that spreading, so give the times the source actually states and let the
  rest breathe.

Capture the **order** and whatever concrete times/durations the source gives;
leave the rest out.

**Flights and trains are never activities.** A plane or train leg belongs in the
top-level **`transport`** array (see its section below), never in a day's
`activities` — there is no activity type for it, and a `road` means a ground
drive, not a flight. Give the leg its `start_date`/`start_time` and the tool
places it in that day's timeline automatically, so the reader still sees it in
the right slot: you lose nothing by keeping it out of `activities`, and putting
it in both **double-books** the day. The same goes for an inter-city bus or
ferry. A short local transfer *may* stay a `road` activity — the taxi across town
to the airport, say — but the flight it delivers you to is a `transport` entry.

**Guidebook page references go in `guidebook_pages`, never in the prose.** If the
source cites guidebook pages for a place, activity, or zone (e.g. "Lonely Planet
p. 142" or "see pp. 88–91"), put the **page numbers alone** in that activity's
`guidebook_pages` field — the four types that have a `description` (`road`,
`point_of_interest`, `place`, `hike`) all accept it. The value holds nothing but
digits, commas and ranges:

| Source says | `guidebook_pages` |
|---|---|
| "Lonely Planet p. 142" | `"142"` |
| "see pp. 88–91" | `"88-91"` |
| "pp. 16, 23 and 25–30" | `"16, 23, 25-30"` |

Drop the `p.`, the guidebook's name and any "see" — the renderers add the
`p.` themselves, and validation **errors** on a value that isn't page numbers.
Never restate the pages in the `description` too: that prints them twice.

**Lift a shared page reference up to the area.** When several stops nested under
one container (a `place`, or a `point_of_interest` with sub-activities) all cite
the *same* guidebook pages, leave each nested `guidebook_pages` empty and set it
once on the container instead. Give a nested stop its own `guidebook_pages` only
when the pages are *specific to that stop* and differ from the area's.

**Opening days and hours: if the source states them, keep them.** A guidebook or
website that bothers to print *"Tue–Sun 9.30–12.30 & 2–6pm"* is telling you the
one thing that can waste a morning, so it must survive extraction. Whenever the
source gives a sight's opening days or hours, put them in that
`point_of_interest`'s **`opening_days` / `opening_hours`** — never drop them, and
never bury them in the `description` instead (the tool checks the visit against
these fields; prose it cannot read).

| Source says | `opening_days` | `opening_hours` |
|---|---|---|
| "Tue–Sun 9.30am–6pm" | `"tue-sun"` | `"09:30-18:00"` |
| "closed Mondays" | `"tue-sun"` | — |
| "daily 9–12 & 2–6" | — | `"09:00-12:00, 14:00-18:00"` |
| "open every day, 10am–7pm" | — | `"10:00-19:00"` |
| "Mon–Fri and Sun, 8am–8pm" | `"mon-fri, sun"` | `"08:00-20:00"` |
| "Wed only, 2pm–5pm" | `"wednesday"` | `"14:00-17:00"` |

Rules for the two values:

- **Convert to 24-hour `HH:MM`** — `2pm` is `14:00`, `9.30` is `09:30`.
- **Keep a midday closure as two ranges** (`"09:00-12:00, 14:00-18:00"`). Never
  flatten it into one long span: the whole point is that a visit can be caught
  straddling the closure.
- **A closing day becomes the days it *is* open.** The fields say when it opens,
  so "closed Mondays" is `"tue-sun"`, not `"monday"`.
- **Weekday names are English** (`monday`…`sunday`, or `mon`…`sun`) whatever
  language the source and the trip are in — they are keys, and the renderers
  localize them.
- **Omit what the source doesn't state.** No `opening_days` means every day, no
  `opening_hours` means all day; both are absences, not guesses.
- **Never invent them, and never look them up.** Unlike a day's `bank_holiday`
  (the one field you *are* asked to supply from your own knowledge), opening
  hours change constantly and are wrong more often than they are useful — take
  them from the documents or leave them out.
- **Seasonal or complicated hours don't fit.** If the source gives per-season
  hours, last-admission rules or "closed the first Sunday of the month", put the
  simple year-round pair in the fields if there is one and put the nuance in the
  `description` as prose for the traveller; if there is no simple pair, leave
  both fields out and describe it. Don't try to encode it.
- **Only `point_of_interest` has these fields.** A `place` (a town) or a `hike`
  doesn't open and close; hours belonging to one sight inside an area go on that
  nested `point_of_interest`.

**A description is for the traveller, not a record of how you built the JSON.**
Every `description` (and the trip `summary`) must earn its place on the day: what
this is, what to see or do, what to watch out for, how to get in. **Never mention
your sources or your process** — no "GPX track", "figures taken from the GPX",
"information processed from source X", "per the booking email", "transcribed from
the screenshot", "estimated from the guidebook", no `[to be checked]`. Someone
reading *"Ridge walk above the valley (GPX track)"* learns nothing from that
parenthesis; it is noise printed in their book. There is **no exception** — not
even a guidebook page, which has its own `guidebook_pages` field (above) and must
never appear in the prose. Everything you want to say about where a value came
from, how confident you are, or which document you trusted belongs in the
end-of-run gaps and inconsistency report, never in the JSON.

**Scheduling fields (any non-`buffer` activity may include these):**

| Field | Format | Notes |
|---|---|---|
| `start_time` | time `HH:MM` | Clock start. |
| `end_time` | time `HH:MM` | Clock end. |
| `duration` | duration (`"1h30"`, `"45 min"`) | How long it lasts. On a `place`, omitting it means "as long as its nested activities add up to" (see `place` below). |
| `start_tz` / `end_tz` | UTC offset | Only if this activity is in a different timezone than the trip default. |

**Map coordinates (any located activity may include these):** if the trip
renders maps (`defaults.include_maps_in_render` on), an activity can carry a
`coordinate` (applies to `point_of_interest`, `place`, `hike` and `meal`; a
`road` carries its coordinates on its **legs** instead — see below). A coordinate
is plotted by default;
add `"show_on_map": false` to record one without drawing its pin. With
`infer_coordinates_from_address` on, activities with no coordinate are geocoded
from their `name`/`address`; otherwise only explicit coordinates appear.

#### Type `road` — a drive or transfer

A drive is written as its **`legs`**: one entry per hop, in travel order, each
carrying its two ends, its driving time, its distance and its route. There is no
`start`, `coordinate`, `waypoints` or `off_road` on the road itself. A road is
always a **ground** leg you drive or ride; a flight or train is a `transport`
entry, never a road.

| Field | Required | Format | Notes |
|---|---|---|---|
| `legs` | **yes** | non-empty array of **leg** objects | The hops, in travel order. A plain A → B drive has exactly one. |
| `distance_km` | recommended | positive number | Driving distance for the **whole** drive. A road should carry a duration (its own/inferred times, or its legs') **and** a `distance_km`; `validate` warns naming either that's missing. |
| `display_start_on_maps` | no | boolean | `true` to give the drive's departure a numbered map pin. Default `false`. |
| `display_end_on_maps` | no | boolean | `true` to give the drive's final arrival a numbered map pin. Default `false`. |
| `display_intermediate_point_on_maps` | no | boolean | `true` to give every junction between two legs a numbered map pin. Default `false`. |
| `description` | no | text | Free prose for what the other fields can't say — see below. |
| `guidebook_pages` | no | page numbers (`"14"`, `"15-18"`, `"16, 23, 25-30"`) | The guidebook page(s) covering the drive. Numbers only — see *Guidebook page references*. |
| `activities` | no | array of **meal** objects | Meal stops along the drive (see nesting). |

Each **leg** is an object:

| Field | Required | Format | Notes |
|---|---|---|---|
| `start_location` | **yes on the first leg** | text | Where the hop departs from. On any later leg, omit it and it reuses the previous leg's `end_location`. |
| `start_coordinate` | no | `{ "lat": .., "long": .. }` | The departure point. Omit on a later leg to reuse the previous leg's `end_coordinate`. Only set coordinates you actually know. |
| `end_location` | **yes on the last leg** | text | Where the hop arrives. On an earlier leg the next leg's `start_location` can name it instead. |
| `end_coordinate` | **yes unless the next leg's `start_coordinate` gives it** | `{ "lat": .., "long": .. }` | The arrival point — it is plotted on the map, so it must resolve. |
| `duration` | recommended | duration (`"45 min"`) | Driving time for this hop. |
| `distance_km` | recommended | positive number | Driving distance for this hop. |
| `off_road` | no | boolean | `true` if **this hop** runs off-road. |
| `waypoints` | no | array of `{ "lat": .., "long": .. }` | Points the hop's route bends through, in order from its start to its end. Coordinates only — no names, no figures. |
| `gpx` | no | the `.gpx` file base64-encoded (gzip allowed) | A recording of **this hop**, drawn as its line on the map instead of the routed guess. Only ever a file the user supplied — see below. |

- A road needs **at least one** leg. For a plain A → B drive that is a single leg
  with `start_location: "A"` and `end_location: "B"`.
- **Write each junction once.** Two consecutive legs meet at one place, so give
  it on one side only: the usual shape is a first leg with both of its ends, then
  each later leg with just its `end_location` / `end_coordinate`. If you do write
  both sides they must **match** — `validate` warns when the names differ or the
  coordinates are a kilometre or more apart, and the earlier leg's `end_*` is
  what gets used. What no leg names at all is an **error**: the first leg must
  give its own departure and the last its own arrival.
- **A named stop is a leg; a bend in the road is a waypoint.** Split the drive
  into a leg per place the reader should see (each prints as its own row with its
  own duration/distance and a *Navigate* link). Points that only **shape the
  route** on the map — a pass, a river crossing, a detour the road takes — go in
  that leg's `waypoints` as bare coordinates.
- Give **every** leg a `duration` **and** a `distance_km`; `validate` warns for
  each leg missing either. The one exception: on a **one-leg** drive the road's
  own duration/`distance_km` cover it, since the drive *is* that hop.
- Keep the leg `duration`s adding up to no more than the road's own `duration`;
  `validate` warns if they don't fit the drive.
- **Off-road belongs to the hop.** When the source says one stretch is rough —
  paved to the village, then 5 km of track — set `off_road: true` on **that leg**
  alone; its row carries an `OFF-ROAD` chip. A drive that is off-road from end to
  end has it on every leg, and then (and only then) the whole road is flagged
  beside its title. Never set it on legs the source doesn't describe that way.
- **Leave the three `display_*_on_maps` switches alone unless the user asks.**
  A drive is drawn as a route; the switches only add numbered pins to its own
  points, which is a presentation choice, not something to infer from a source.
  Set one only on an explicit instruction ("pin the stops", "show where we
  break the drive"), and remember all three on means every named point of the
  drive gets a pin.
- **A leg's `gpx` is only ever a file the user gave you.** If the trip material
  contains a `.gpx` for a drive (or a segment of one), attach it to the leg it
  records, base64-encoded, and drop that leg's `waypoints` — the recording
  already runs through them. **Never** synthesize one: not from a KML track, not
  from a list of coordinates, not from your own idea of the road. A fabricated
  recording is a wrong map drawn with total confidence. Nothing else about the
  leg changes: keep its stated `duration` / `distance_km` rather than measuring
  them off the file.
- A road's **`description` is optional and holds only what no other field can**:
  the state of the road, a scenic or difficult stretch, a pass that may be shut,
  a toll, a ferry crossing, where to refuel. It is **not** the place to restate
  the route, the distance, the duration or the stops — the legs already print
  those, and repeating them just doubles the text. Leave it out when the source
  says nothing beyond the itinerary itself; most drives don't need one. (Both
  renderers print it above the leg list.)

```json
{
  "type": "road",
  "distance_km": 345,
  "start_time": "08:30",
  "duration": "4h",
  "legs": [
    {
      "start_location": "Amboise",
      "start_coordinate": { "lat": 47.4132, "long": 0.9857 },
      "end_location": "Poitiers",
      "end_coordinate": { "lat": 46.5802, "long": 0.3404 },
      "duration": "1h20",
      "distance_km": 120
    },
    {
      "end_location": "Sarlat-la-Canéda",
      "end_coordinate": { "lat": 44.889, "long": 1.216 },
      "duration": "2h40",
      "distance_km": 225
    }
  ]
}
```

**A KML/KMZ directions track becomes `waypoints`, never a `gpx`.** If a KML/KMZ
holds a *directions* geometry matching this drive, use it instead of guessing the
route. Keep every **named** point of the directions that falls on the drive as
the `end_location` of a leg (in order), and then, for each leg, fill its
`waypoints` with **25 evenly spaced points** taken along the directions geometry
for that leg's own segment — so the map route follows the real road rather than a
straight line. Sampling a KML into `waypoints` is fine; re-encoding it as a
leg's `gpx` is not — that field is reserved for a `.gpx` the user actually
provided.

**Link separate places with a `road`.** Between two consecutive activities that
happen in different places (a different town, area, or trailhead), insert a
`road` whose first leg departs from the first place and whose last leg arrives at
the second. Skip it only when the two stops share the same area (nested under one
`place`, or clearly in one town) — there's no leg to draw within a single place.

**Never chain roads — merge them into one.** When back-to-back roads form
`A → B` then `B → C`, do **not** emit two road objects. Emit **one** road whose
`legs` are those hops:

- the first leg is `A → B`, carrying that hop's `duration` and `distance_km`;
  the second is `B → C` (its `start_location` omitted — it inherits `B`).
- Each original road's route-shaping points stay with the leg they belong to, in
  its `waypoints`.
- The merged road's `distance_km` is the **sum** of the legs, and its
  `duration`/times span the whole drive: its `start_time` is the first hop's, its
  `end_time` the last hop's.
- `off_road` stays on whichever legs were off-road, and the merged `activities`
  are every original road's nested meals, in order.

A longer chain collapses the same way: `A → B`, `B → C`, `C → D` becomes a single
road with three legs. This is exactly what legs are for — both renderers display
each leg as its own row, so nothing is lost by merging, while two chained road
objects read as two separate drives and double-count the transition.

**The one exception: something happens at `B`.** If an activity sits *between*
the two roads (you stop at `B` to visit, eat, or hike), the roads are not
back-to-back — keep them as two roads, so the timeline reads
drive → activity → drive. Merge only when the two roads are adjacent in the
`activities` array with nothing between them.

#### Type `point_of_interest` — a specific sight

| Field | Required | Format | Notes |
|---|---|---|---|
| `name` | **yes** | text | The place's name. |
| `category` | no | enum (default `other`) | One of: `museum`, `church`, `building`, `viewpoint`, `ruins`, `castle`, `temple`, `street`, `natural park`, `mountain`, `lake`, `beach`, `waterfall`, `other`. |
| `address` | no | text | |
| `description` | no | text | |
| `guidebook_pages` | no | page numbers (`"14"`, `"15-18"`, `"16, 23, 25-30"`) | The guidebook page(s) covering this sight. Numbers only — see *Guidebook page references*. |
| `website` | no | a link like `https://example.com` | The venue's website — shown as a clickable link. |
| `opening_days` | no | weekday names / ranges (`"tue-sun"`, `"mon-fri, sun"`) | The days it opens. **Keep these whenever the source states them** — see *Opening days and hours*. |
| `opening_hours` | no | `HH:MM-HH:MM` ranges (`"09:30-18:00"`, `"09:30-12:30, 14:00-18:00"`) | The hours it opens. **Keep these whenever the source states them** — see *Opening days and hours*. |
| `activities` | no | array of `point_of_interest` / `hike` / `meal` | Nested sights/hikes/meals (see nesting). |

#### Type `place` — a town/area grouping several stops

| Field | Required | Format | Notes |
|---|---|---|---|
| `name` | **yes** | text | The place name. |
| `description` | no | text | |
| `guidebook_pages` | no | page numbers (`"14"`, `"15-18"`, `"16, 23, 25-30"`) | The guidebook page(s) covering the area — the right home for pages shared by its nested stops. |
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

**Leave a place's `duration` out unless the source states one.** A place has no
length of its own, so an omitted `duration` (and `end_time`) means "however long
the nested activities add up to" — the tool sums them and chains that into the
day's timeline. Give it explicitly only when the source says how long the whole
visit takes (and then make sure it is **not below** the nested total, which
`validate` warns about). Never invent a round number to fill it: an invented `3h`
silently overrides three real sub-durations.

#### Type `hike`

| Field | Required | Format | Notes |
|---|---|---|---|
| `name` | **yes** | text | Trail/hike name. |
| `description` | no | text | |
| `guidebook_pages` | no | page numbers (`"14"`, `"15-18"`, `"16, 23, 25-30"`) | The guidebook page(s) covering the hike. Numbers only — see *Guidebook page references*. |
| `distance_km` | recommended | number | Length. A hike (top-level **or nested** under a place/point of interest) should carry a duration, a `distance_km` **and** an `elevation_m`; `validate` warns naming any of the three that's missing. |
| `elevation_m` | recommended | number | Elevation gain in metres (see `distance_km`). |
| `start` | no | text | Trailhead. |
| `end` | no | text | End point. |
| `route` | no | enum (default `back_and_forth`) | One of `loop`, `back_and_forth`, `one_way`. For `loop`/`back_and_forth`, `end` should match `start` (or be omitted); for `one_way`, `end` should differ. |
| `gpx` | no | base64 string | The trail's `.gpx` file, base64-encoded (gzip accepted). Drawn as a trail map + elevation profile. **Only emit this when you were given the actual GPX file** — see *Embedding a GPX track* below. |
| `activities` | no | array of **meal** objects | Meal stops along the hike. |

**Embedding a GPX track.** When a GPX file is available to you *as a file*, put
it base64-encoded in the `gpx` field of the thing it records — a hike, or a
**road leg** (see *Type `road`*) — so the track travels inside the itinerary and
the renderers can draw it. The encoding and the never-invent-one rule are the
same for both; what differs is what gets drawn: a hike's becomes a trail map plus
an elevation profile, a leg's becomes that leg's line on the day map (no profile,
and no measured figures filled in for you).

```bash
gzip -9 -c trail.gpx | base64 | tr -d '\n'    # preferred: ~10× smaller
base64 -i trail.gpx | tr -d '\n'              # plain, also fine
```

Rules:

- **Never invent or reconstruct a GPX.** If you only have prose, a screenshot or
  a list of waypoints, leave `gpx` out — a fabricated track is a wrong map, which
  is worse than no map. Only a real file you were handed goes in.
- **Copy it byte-for-byte.** Don't trim, resample or reformat the XML; the tool
  simplifies the line and resamples the profile itself.
- With a `gpx` present you may **omit** `distance_km` and `elevation_m` — the
  tool measures both off the track. Write them only when a source gives a figure
  you trust more (see *A GPX track is the principal source of truth*, below); a
  written figure always wins over the measured one.
- A GPX without `<ele>` elevations is fine: the trail map still draws, there is
  just no profile, and `elevation_m` stays unmeasured (so give it if you know it).
  On a **road leg** elevations are never used at all.
- The two bullets above about *measuring* apply to a hike only. A road leg's
  `duration` and `distance_km` stay exactly as the source states them — the
  track's measurements are never substituted.

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

Only add `buffer` when the source explicitly calls for a fixed break ("an hour
free before dinner"); gaps are otherwise generated for you, and a buffer you
write is the one thing the auto-sizing leaves at exactly the length you gave.

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
duration out if unsure — the warning only fires when both sides are known, and
for a `place` an omitted duration becomes the nested total anyway.

---

## `transport` (array — one entry per booking, each with its `legs`)

Inter-city travel: flights, trains, buses, taxis, ferries. Each entry is **one
reservation** — one thing you bought, with one reference and one price — and its
`legs` array holds the hops that reservation moves you over.

**`legs` is required and must hold at least one entry.** A direct one-hop
journey is a one-leg booking; there is no flat form.

### The booking

| Field | Required | Format | Default | Notes |
|---|---|---|---|---|
| `type` | no | enum | `other` | One of `plane`, `train`, `bus`, `taxi`, `ferry`, `other`. Applies to every leg. |
| `name` | no | text | the route through its legs (`A → B → C`) | What the booking is called, used as the card's heading. **Infer one** — see below. |
| `booking_number` | no | text | none | Reservation reference / PNR, covering the whole booking. |
| `booking_source` | no | text | none | Where booked (e.g. "SNCF Connect"). |
| `website` | no | link | none | The carrier's website — clickable. |
| `booking_link` | no | link | none | Direct link to this reservation — clickable. |
| `status` | no | `booked` / `confirmed` | none | Reservation status. |
| `description` | no | text | none | A **short note about the whole booking** — a baggage allowance, a fare condition, a check-in window. A note about one hop goes on that leg instead. |
| `price` | no | number | none | Amount for the **whole booking**, every leg included, e.g. `89` (no symbol). |
| `currency` | no | 3-letter ISO code | trip default currency | Set only if this price is in a different currency. |
| `paid` | no | `paid` / `to pay` | none | Payment state. |
| `legs` | **yes** | array | — | One entry per hop, in travel order. Never empty. |

### A leg (`transport[].legs[]`)

| Field | Required | Format | Default | Notes |
|---|---|---|---|---|
| `start` | **yes** | text | — | Departure point (station/airport/city). |
| `end` | **yes** | text | — | Arrival point. |
| `start_date` | **yes** | date `YYYY-MM-DD` | — | Departure date; slots the leg into that day. |
| `start_time` | **yes** | time `HH:MM` | — | Departure time (local). |
| `end_date` | no | date `YYYY-MM-DD` | inferred (+1 day if it crosses midnight) | Set for overnight legs when known. |
| `end_time` | no | time `HH:MM` | inferred from `start_time` + `duration` | Arrival time (local). |
| `start_tz` | no | UTC offset | trip default timezone | Departure zone — **set it for flights** between zones. |
| `end_tz` | no | UTC offset | trip default timezone | Arrival zone. |
| `duration` | no | duration (`"4h20"`) | inferred from the two times (timezone-aware) | Give it if the two times aren't both known. |
| `flight_number` | no | text | none | **Planes only** — e.g. `"AF9"`. This leg's own flight. |
| `train_number` | no | text | none | **Trains only** — e.g. `"TGV 8541"`. This leg's own train. |
| `description` | no | text | none | A **short note** about this leg for what its fields don't cover — a seat, a terminal, a baggage allowance. One or two sentences. |
| `start_coordinate` / `end_coordinate` | no | `{ "lat": .., "long": .. }` | none | For maps; a dotted straight line is drawn between them on each day map the leg is in progress on (both days of an overnight leg) and on the whole-trip map. |

**Name it.** `name` is optional to the tool, but **write one for every booking**:
it is the heading the card carries, and left out it falls back to the route
through every leg — `New York JFK → Paris CDG → Toulouse-Blagnac → Paris CDG →
New York JFK`, which is accurate but a mouthful. Compose it from what the booking
*is*:

> `"Round trip New York ↔ France"` · `"Flight home via Paris"` ·
> `"Paris → Tours by TGV"` · `"Night train back to Paris"`

- **Say the shape of the journey, not the ticket's paperwork.** Where it goes,
  in which direction, and by what means if it isn't obvious from `type`. Never
  put the reference, the price, the dates or the carrier's name in it — those all
  have their own fields and are printed beside it.
- **Only from the itinerary.** Use the place names already in the legs (shortened
  to the city where the airport code adds nothing: "New York", not "New York
  JFK"). Don't invent a product name ("Air France Business Saver") the source
  never states.
- **Short.** Under about 40 characters, one line.
- **A one-leg booking may go unnamed.** Its card is a flat block headed with the
  route, and the renderers drop the route line when the name would repeat it —
  so `"Paris → Tours"` as a `name` adds nothing. Name it only when you can say
  something the route doesn't ("Night train back to Paris").
- **The language rule at the top of this document applies**, like any other prose
  you author.

**Notes:**

- **Booking-level or leg-level? Ask what you bought once.** One reference, one
  price, one cancellation link → one entry. Each separate movement inside it →
  one leg. A field written on the wrong side is **not read** — `validate` warns
  and names the level it belongs on, but don't rely on that: get it right.
- **A connection is one booking with several legs.** Paris → New York *via*
  London on a single ticket is **one** entry with two legs (Paris → London,
  London → New York), each with its own times, zones and flight numbers. So is a
  **round trip** on one reservation: outbound and return are two legs of the same
  entry, however many days apart.
- **Separate tickets stay separate entries** even between the same two cities. If
  the source shows two references, two prices or two cancellation links, that is
  two bookings — don't merge them just because they connect.
- **Provide any two of** `start_time` / `end_time` / `duration` per leg; the tool
  derives the third. Each leg's departure date and time are always required.
- **Timezones matter.** For a flight `22:30 (UTC-4) → 11:45 (UTC+2)`, set both
  `start_tz` and `end_tz` on that leg so the duration comes out right (here
  7h15). If the source doesn't state them, look them up from the airport codes /
  station cities (use the offset in effect on the travel date — mind DST). Only
  skip this when both endpoints clearly share the trip's default timezone.
- An **overnight** leg (arrival earlier than departure, or `end_date` after
  `start_date`) is treated as *that night's accommodation* — don't also add a
  hotel for that night.
- **`flight_number` / `train_number` vs `booking_number`** are different, and
  they now sit at different levels: the first is the public service identifier of
  **one leg** (`AF9`, `TGV 8541`), the second is your reservation reference / PNR
  for the **whole booking** (`AF1234-XY`). Capture both when given. Only set
  `flight_number` on a `plane`, `train_number` on a `train`.
- **One price, not one per leg.** If the source prices a round trip as a single
  fare, put that fare on the booking. If it prices each direction separately and
  they are one reservation, add them up and say nothing about the split (there is
  nowhere to put it); if they are genuinely two reservations, they are two
  entries.
- If `status` or `paid` is set, include the matching `booking_number` / `price`
  when available (`validate` warns otherwise).
- **Two `description` fields, two jobs.** The **booking's** is about the
  reservation: a baggage allowance, a fare condition, a check-in window, a
  cancellation rule — anything true of every leg. A **leg's** is about that hop:
  a seat, a terminal, a coach number. Put each fact on one level only; stating
  the bag allowance on both prints it twice. Neither is prose — one or two
  sentences of what no other field can carry, never invented, never restating a
  value that already has its own field.

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
| `description` | no | text | none | A **short note** for what the fields above don't cover — a door code, where to park, which bell to ring. One or two sentences. |
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
- **`description` is a note, not prose.** Put in it only what no other field can
  carry, in one or two sentences. Never invent one, and never restate a value
  that already has its own field — omit it if the source says nothing extra.

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
| `description` | no | text | none | A **short note** for what the fields above don't cover — the insurance excess, a fuel policy, where the desk is. One or two sentences. |
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
- **`description` is a note, not prose.** Put in it only what no other field can
  carry, in one or two sentences. Never invent one, and never restate a value
  that already has its own field — omit it if the source says nothing extra.

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
`examples/france.json`.) The three `misc.emergency_contacts` here are looked-up
values, so a real run would cite all three under *Looked up online*.

```json
{
  "travel_description": {
    "title": "Grand Tour of France",
    "subtitle": "Paris, the Loire châteaux, the Dordogne and the high Pyrenees",
    "cover_color": "#2f5d8c",
    "summary": "Eight days that start in a city and end on a mountain pass. Paris comes first and on foot: the Louvre, the Seine, the streets in between, with nothing to drive. A TGV south and a hire car turn the trip outward — Renaissance châteaux standing over the Loire, then the long road down to the Dordogne and the market streets of Sarlat. The last stretch climbs into the Pyrenees for the Cirque de Gavarnie and a full day's walk above the valley. The flight home leaves from Toulouse, an hour from the peaks."
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
  "misc": {
    "emergency_contacts": [
      { "name": "Emergency — any service (EU-wide)", "contact": "112" },
      { "name": "SAMU — medical emergencies", "contact": "15" },
      { "name": "US Embassy, Paris — consular emergencies", "contact": "+33 1 43 12 22 22" }
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
          "distance_km": 32,
          "start_time": "12:30",
          "duration": "50 min",
          "legs": [
            {
              "start_location": "Paris-Charles de Gaulle Airport",
              "start_coordinate": { "lat": 49.0097, "long": 2.5479 },
              "end_location": "Hôtel des Grands Boulevards",
              "end_coordinate": { "lat": 48.8713, "long": 2.3436 }
            }
          ]
        },
        {
          "type": "point_of_interest",
          "name": "Musée du Louvre",
          "category": "museum",
          "address": "Rue de Rivoli, 75001 Paris",
          "guidebook_pages": "44-47",
          "opening_days": "wed-mon",
          "opening_hours": "09:00-18:00",
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
          "distance_km": 345,
          "legs": [
            {
              "start_location": "Amboise",
              "start_coordinate": { "lat": 47.4132, "long": 0.9857 },
              "end_location": "Poitiers",
              "end_coordinate": { "lat": 46.5802, "long": 0.3404 },
              "duration": "1h20",
              "distance_km": 120
            },
            {
              "end_location": "Limoges",
              "end_coordinate": { "lat": 45.8336, "long": 1.2611 },
              "duration": "1h15",
              "distance_km": 125
            },
            {
              "end_location": "Sarlat-la-Canéda",
              "end_coordinate": { "lat": 44.8890, "long": 1.2160 },
              "duration": "1h25",
              "distance_km": 100
            }
          ]
        }
      ]
    }
  ],
  "transport": [
    {
      "type": "plane",
      "name": "Round trip New York ↔ France",
      "booking_number": "AF77-QWLM",
      "status": "confirmed",
      "description": "One booking both ways, so the bags are checked through from Toulouse. One checked bag each (23 kg) included.",
      "price": 1410,
      "currency": "USD",
      "paid": "paid",
      "legs": [
        {
          "start": "New York JFK",
          "end": "Paris CDG",
          "start_date": "2026-09-04",
          "end_date": "2026-09-05",
          "start_time": "22:10",
          "start_tz": "-04:00",
          "end_time": "11:45",
          "end_tz": "+02:00",
          "flight_number": "AF23"
        },
        {
          "start": "Paris CDG",
          "end": "New York JFK",
          "start_date": "2026-09-11",
          "start_time": "21:30",
          "start_tz": "+02:00",
          "end_time": "23:40",
          "end_tz": "-04:00",
          "flight_number": "AF6"
        }
      ]
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
  fall back to a sensible default (listed above). **Exactly two exceptions**,
  both because the fact is public and no booking confirmation carries it: a
  day's `bank_holiday` (see *Set `bank_holiday` on every day that is one*) and
  `misc.emergency_contacts` (see *`misc`*). Everything you fill from your own
  knowledge or the web — and **only** those two may be — is reported with its
  source; see *Report what you looked up online* below.
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
- **Nearby coordinates aren't a conflict.** Two sources pinning the same place
  **less than 1 km apart** are describing the same spot — a car park vs. the
  entrance, a town centroid vs. a specific address. Keep the authoritative one
  (the KML/KMZ, then the GPX, then the more precise-looking source) and do **not**
  list it in the inconsistency report. Only report a coordinate conflict when the
  two points are at least 1 km apart — which usually means they are genuinely
  different places, or one is a typo (a flipped sign, a transposed digit, swapped
  lat/long), and that is worth naming. To judge the gap without computing it
  exactly: 0.01° of latitude is ~1.1 km everywhere, and 0.01° of longitude is
  ~1.1 km at the equator shrinking toward the poles (~0.8 km at 45°). So a
  difference of **0.005° or less in both** is safely under 1 km, more than
  **0.02° in either** is safely over, and in between it is worth estimating
  properly.
- **A GPX track is the principal source of truth for a hike's (or off-road
  drive's) figures.** When a GPX is provided for a hike, take its `distance_km`,
  `elevation_m` and start/end from the track — or, better, embed the file itself
  in the hike's `gpx` and let the tool measure them (see *Embedding a GPX track*). If the prose text states different
  numbers, use the GPX values in the JSON — but flag the discrepancy in the
  end-of-run inconsistency report (below), naming both figures. **Unless the gap
  is within the tolerances just below** — then it is not a discrepancy at all.
- **Small size differences aren't a conflict.** Two sources rarely agree to the
  metre on a distance, a climb or a duration, and reporting every such gap buries
  the conflicts that matter. Treat the values as **equal** — and leave them out
  of the inconsistency report entirely — when they differ by no more than:

  | Figure | Tolerance |
  |---|---|
  | a road's `distance_km` | 5 km |
  | a hike's `distance_km` | 1 km |
  | a hike's `elevation_m` | 50 m |
  | any `duration` (road, hike, activity, transport) | 5 min |

  Within the tolerance, write the **roundest** of the values: the whole number
  over the decimal, the multiple of 10 or 5 over the awkward figure — `12` over
  `12.4` km, `400` over `380` m, `"1h30"` over `"1h27"`. This is the one case
  where a round prose figure outranks the GPX track. If two values are equally
  round, keep the one from the more authoritative source (the GPX first, then the
  KML/KMZ). Past the tolerance nothing changes: take the authoritative figure and
  report the conflict, naming both.
- **One place, one name — normalise every name across the whole file.** Sources
  disagree on spelling far more often than on facts: `Sarlat-la-Caneda` vs
  `Sarlat-la-Canéda`, `St-Malo` vs `Saint-Malo`, `Florence` vs `Firenze`, `CDG`
  vs `Paris Charles de Gaulle`, `Lac de Gaube` vs `lac du Gaube`. Before you
  emit, sweep the file and make each real-world place appear under **one** form
  everywhere — day `city`, accommodation `city`, transport `start`/`end`, a road
  leg's `start_location`/`end_location`, `place`/`point_of_interest`/`hike` names,
  a meal's `area`, car-rental pick-up/drop-off locations, and the prose in every
  `description`.
  - **Choosing the form to keep**, in order: the trip's language (per the
    language rule at the top); then the local/official full spelling **with its
    diacritics** (`Sarlat-la-Canéda`, not `Sarlat-la-Caneda`); then the form most
    of the sources use; then, for a place that is also in a KML/KMZ, the name that
    file gives it.
  - Prefer the **full** name over an abbreviation or a code, except where the
    short form is what the traveller will actually look for on a sign or a board
    (an airport terminal, a station). Never invent a fuller name you are not sure
    of.
  - **Don't normalise what identifies a booking:** a hotel/company name, a flight
    or train number and a booking reference stay exactly as printed, even when the
    surrounding place name is canonicalised.
  - **Never touch an `address`.** Copy every `address` exactly as its source
    writes it — do not re-spell it, expand it, translate it, add or drop a
    postcode or country, or align it with the name you canonicalised elsewhere. An
    address is machine-consumed, not decorative: the viewer turns the raw string
    into a map search link, and `infer_coordinates_from_address` / the `geocode`
    command feed it to a geocoder, so an "improved" address is one that stops
    resolving. A town canonicalised to `Sarlat-la-Canéda` in `city` therefore sits
    happily beside an `address` that still reads `24200 Sarlat la Caneda` — that
    is not an inconsistency and needs no report.
  - This is not cosmetic. A day's `city` must contain that night's accommodation
    `city` *spelled identically* or `validate` warns (see the `city` rules), and a
    reader can only match a stay to its day when the two agree.
  - **List every name you unified in the inconsistency report** — the variants you
    saw, the form you kept, and why. This one *is* reported, unlike the price,
    size and coordinate tolerances above.
- **After writing the JSON, report the gaps.** List the optional fields you left
  empty (with a one-line note on what each would add) so the user can fill in
  anything the source didn't cover.
- **Once you're done, report the inconsistencies.** Present them as a **bullet
  list**, one bullet per conflict, and for each one state clearly: *what* was in
  conflict (the field/place and the differing values, e.g. "arrival time: email
  says 14:00, voucher says 14:30"), *which value you chose* for the JSON, and
  *why* (which source you trusted). Cover every conflict you found between the
  source documents — a place, date, time, price, coordinate, hike figure…
  stated differently in two places. Three exceptions, all above — a price gap of
  1 unit or less, a distance/elevation/duration gap inside its tolerance, and two
  coordinates less than 1 km apart — are not conflicts and belong nowhere in this
  list.
- **Report what you looked up online.** Anything in the JSON that did **not**
  come from a supplied document — which can only ever be a `bank_holiday` flag or
  a `misc.emergency_contacts` entry — gets its own bullet in the inconsistency
  report, under a **"Looked up online"** heading, stating the value, where it
  sits in the JSON, and **the URL you took it from**. One bullet per value; a
  page covering several contacts may be cited once for all of them.
  - **No URL, no value.** If you cannot point at a source, leave the value out
    and say so in the gaps report instead. This rule exists so the user can check
    every number that isn't theirs, and *not filling a field is always better
    than hallucinating it*.
  - It is a separate heading from the conflicts, not mixed in with them: nothing
    here disagreed with anything — it simply wasn't in the sources.
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
- **No chained roads:** no day holds two adjacent `road`s where the first's
  arrival is the second's departure. Those are one road, with the intermediate
  place as the junction between two legs (see *Never chain roads*).
- **Every road has `legs`:** no `road` carries a `start`, `coordinate`,
  `waypoints` or `off_road` of its own (all four moved onto the legs), every
  road's `legs` is non-empty, the first leg names its `start_location`, the last
  its `end_location`, and each junction written on both sides matches.
- **No provenance in the prose:** no `description`/`summary` mentions a GPX, a
  KML, an email, a screenshot, a source name, your own uncertainty, or
  `[to be checked]` — no exceptions.
- **Guidebook pages are in `guidebook_pages`, not the prose:** no `description`
  contains a `p.`/`pp.` page reference or a guidebook's name, and every
  `guidebook_pages` value is digits, commas and ranges only (`"15-18"`, not
  `"pp. 15-18"`). Pages shared by an area's nested stops sit once on the
  container.
- **Every stated opening day/hour was kept:** each sight whose source printed
  opening days or hours carries them in `opening_days` / `opening_hours`, in
  24-hour time, with a midday closure left as two ranges — none of it dropped,
  and none of it left as prose in the `description` instead. Nothing was invented
  or looked up for these two fields.
- **No flights or trains in `activities`:** every plane/train (and inter-city
  bus/ferry) leg sits in the top-level `transport` array, exactly once — not also
  as a `road` or a `point_of_interest` inside the day.
- **Every transport entry has a non-empty `legs` array**, with `start`, `end`,
  `start_date` and `start_time` on each leg — and nothing left at the booking
  level that belongs on a leg (a place, a date, a time, a flight/train number) or
  vice versa (a reference, a price, a link, the `type`). Hops of one reservation
  are legs of one entry; separate tickets are separate entries.
- **Every multi-leg transport entry has a `name`** — short, describing the
  journey, with no reference/price/date in it — since its default (the whole
  route chain) gets long. A one-leg entry may go unnamed. Any `description` sits
  on the level it is true of: the reservation's on the booking, one hop's on that
  leg, never both.
- **Every day has a `description`** — 1–2 sentences drawn from that day's own
  activities, with no verdict on how busy it is.
- **The trip has a `summary`** — 4–6 sentences that sell the trip, built only from
  places and legs the JSON already contains, free of brochure filler
  ("unforgettable", "must-see", "breathtaking"), not a day-by-day march, not a
  restatement of the `subtitle`.
- **Bank holidays checked:** every dated day's date has been weighed against the
  public holidays of the country it's spent in, and `bank_holiday` set on the ones
  that are (or the country listed in the gaps report when you couldn't confirm
  its calendar for that year).
- **Emergency contacts are certain and cited:** every `misc.emergency_contacts`
  entry is either from a supplied document or listed under *Looked up online*
  with its URL — and any number you weren't sure of was left out (or reduced to a
  `name` with no `contact`) rather than guessed. `contact` is written as it is
  dialled locally, and no entry has both halves empty.
- **Every day has a `city`**, and that night's accommodation `city` appears
  inside it spelled identically (`"Amboise → Sarlat-la-Canéda"` for a stay in
  `"Sarlat-la-Canéda"`).
- **Names are consistent:** each place appears under one spelling throughout —
  search the file for each town/site name and confirm there is no second variant
  (missing accent, abbreviation, translated form) left behind. **Every `address`
  is exempt** — those stay byte-for-byte as the source wrote them.
