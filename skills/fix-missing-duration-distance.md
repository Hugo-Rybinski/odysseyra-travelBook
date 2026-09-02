# Skill: fix missing durations & distances

**Input:** an Odysseyra TravelBook itinerary JSON **and** a list of validator warnings about
missing size information — the ⚠️ lines `odysseyra-travelBook validate` prints for
activities, roads, hikes and transports that carry no duration/distance/
elevation (English or French).

**Output:** a single Markdown worksheet, `<title>-missing.md`, with one
fill-in-the-blank entry per missing value, grouped by day in itinerary order —
ready for the user to complete and hand back. For each missing **road** distance
you add a Google Maps link so the figure can be read straight off the map; for
each **hike** you pre-fill a best estimate from the web, always tagged
`[to be checked]` and backed by a source link and a verbatim quote.

You do **not** edit the JSON. You only build the worksheet; the user completes
it (and confirms the `[to be checked]` values), then it gets merged back.

This document is self-contained: everything you need to read the JSON and build
the worksheet is here — no source code, no other file, no tool.

**Start from a blank slate.** Work only from this skill and the documents
provided in this conversation — do not draw on past memory, earlier
conversations, or prior assumptions. If a fact is not in this skill or the
supplied sources, it does not exist for this task.

**Settle the language before you write anything.** The worksheet's own wording is
yours to write — its headings, the per-entry labels, the instructions to the
user, the `[to be checked]` notes. It must all be in **one** language. **If the
language to use is unclear — the JSON is in one language and the request in
another, the warnings are in a third, or nothing states it — stop and ask the
user which language to write in before proceeding.** Do not guess: in
particular, the warnings arriving in French (or English) tells you which language
the validator ran in, **not** which language the worksheet should be in. Item
names copied from the JSON, and the verbatim quotes backing a hike estimate, stay
exactly as their source writes them — the choice only governs the prose you
write.

---

## The warnings you handle

Each warning names its **line**, an **identifier in parentheses**, and — after
`missing:` — the exact field(s) to fill. The identifier is the activity/hike
`name`, or, for a drive, `origin → destination`. Use it (with the line number) to
find the object in the JSON. Only ever ask for the fields the warning lists.

| Warning (EN) | Warning (FR) | Item | Fields |
|---|---|---|---|
| `this activity (NAME) has no duration and none can be inferred…` | `cette activité (NAME) n'a pas de durée…` | point of interest / place | `duration` |
| `this road (A → B) should give a duration and a 'distance_km' — missing: …` | `cette route (A → B) devrait indiquer une durée et « distance_km » — manquant : …` | a plain (single-leg) drive | listed |
| `this road's leg (A → B) should give … — missing: …` | `l'étape de cette route (A → B) devrait indiquer … — manquant : …` | the drive's leg **A → B** | listed |
| `this hike (NAME) should give a duration, a 'distance_km' and an 'elevation_m' — missing: …` | `cette randonnée (NAME) devrait indiquer une durée, « distance_km » et « elevation_m » — manquant : …` | hike | listed |
| `this leg has no duration and none can be inferred…` | `ce trajet n'a pas de durée…` | a transport **leg** | `duration` |

`missing:` lists the raw JSON keys: `duration`, `distance_km`, `elevation_m`.

The **leg** warning names nothing in parentheses, so its **line number is the
only way to tell one leg from another** — a booking with three legs can raise it
three times, identically. Match each warning to the leg whose `start_time` sits
on that line, and label the worksheet entry with that leg's own
`start → end` so the reader knows which hop is being asked about.

For a **`place`** the first warning has two answers, and the better one is
usually the second: a place with no `duration` lasts whatever its nested
activities add up to, so timing the stops inside it (a `duration` each) settles
the place too. Ask for the place's own `duration` only when the source gives the
whole visit as one figure.

---

## How to read the JSON

The itinerary is one JSON **object**. You only need a few of its keys:

- **`days`** — an array; `days[i]` is day *i* (0-based). Each day has a `title`,
  an optional `city`/`date`, and **`activities`** — an ordered array.
- **`transport`** — an array of **bookings** (`transport[i]`): one reservation
  each, carrying `type` / `booking_number` / `price` and a **`legs`** array. The
  places and times are on the legs, so a warned leg is
  `transport[i].legs[j]`, with `start`, `end`, `start_date`, `start_time`, … A
  one-hop booking still has one leg (`legs[0]`), so the path shape never
  changes.

**Activities.** Each entry of an `activities` array is an object with a `type`:
`point_of_interest`, `place`, `hike`, `road`, `meal`, or `buffer`. The ones that
get warned here:

- `point_of_interest` / `place` — have a **`name`**. A warning
  `this activity (NAME) …` points to the object whose `name` is *NAME*.
- `hike` — has a **`name`** (and optional `start`/`end` trailhead text). A warning
  `this hike (NAME) …` points to the hike whose `name` is *NAME*. A hike that
  embeds a `gpx` is never warned about `distance_km` (the track measures it), nor
  about `elevation_m` when the track carries elevations — so if such a hike *is*
  warned, the missing field is genuinely missing and the estimate is still wanted.
- `road` — a drive; see below. Has no `name`; it is identified by its route.

**Nesting (important for hikes).** A `place` or `point_of_interest` may hold its
own nested **`activities`** array (one level deep). So a warned hike can sit
either at the top level of a day —
`days[2].activities[3]` — or nested inside a container —
`days[2].activities[1].activities[0]`. When you look up a hike/POI by its `name`,
search **both** levels. Record the full path as the entry's locator.

**Coordinates.** Wherever a `coordinate` appears it is
`{ "lat": <number>, "long": <number> }` in decimal degrees. It may sit on:

- an activity (`point_of_interest`, `place`, `hike`, `meal`),
- **each end of each road leg** (`start_coordinate` / `end_coordinate`), and
- a road leg's route-shaping `waypoints`, which are bare `{lat,long}` objects.

`show_on_map: false` may also be present — ignore it here.

**Roads and their legs.** A `road` object holds a **`legs`** array — one entry
per hop, in travel order — and nothing else about the route (there is no `start`,
`coordinate`, `waypoints` or `off_road` on the road itself). Each leg is
`{ "start_location": <name?>, "start_coordinate": {lat,long}?,
"end_location": <name?>, "end_coordinate": {lat,long}?, "duration": <?>,
"distance_km": <?>, "off_road": <?>, "waypoints": [{lat,long}, …]? }`.

**An endpoint may be written on the neighbouring leg instead**, so read the chain
before matching a warning:

- **origin** = this leg's `start_location`/`start_coordinate`; when they're absent,
  the *previous* leg's `end_location`/`end_coordinate`.
- **destination** = this leg's `end_location`/`end_coordinate`; when they're
  absent, the *next* leg's `start_location`/`start_coordinate`.

So for a warning `this road's leg (A → B) …`, find the road whose legs resolve to
`A → B` at that position — usually the leg whose `end_location` is `B`. Its
`waypoints` (bare coordinates, if any) are that hop's shaping points.

For `this road (A → B) …` the road has a **single** leg: A is its origin, B its
destination, and the missing figure may be wanted on the road itself (its own
`duration` / `distance_km` cover a one-leg drive) — fill the leg's, which is
always correct.

---

## Workflow

1. For each warning, read `(line, identifier, item type, missing fields)` and
   locate the object per **How to read the JSON** above.
2. Emit one worksheet entry per warning, in the format for its item type below.
3. Group entries under a heading per day, in itinerary order; put transport
   entries under a final **Transport** heading.
4. Save the worksheet as `<title>-missing.md`.

---

## Entry formats

Give every entry a locator so the completed value can be merged back: the JSON
path (`days[2].activities[0]`, or the nested `…activities[1].activities[0]`) and,
for a road leg, its index in `legs` and the two endpoint names. List **only**
the missing fields.

### Road / road leg — missing `distance_km` and/or `duration`

**First, look for the same drive in the other direction.** A trip that drives
`A → B` and later `B → A` along the same road has one distance and one driving
time, so a figure written on either direction answers for both. Before you leave
a blank, search the whole JSON for a leg (or a one-leg road) running between the
same two places the other way round, and if it carries the missing field,
pre-fill it from there — no `[to be checked]` tag, since it comes from the user's
own file, and cite it as its JSON path instead of a link.

Here a day drives up the valley and back down again, and only the way down was
measured:

```
- **Road leg** Cauterets → Pont d'Espagne · `days[6].activities[4].legs[0]`
  - distance_km: 12 · from the return leg `days[6].activities[6].legs[0]` (Pont d'Espagne → Cauterets)
```

Two cautions. Only do it when it is genuinely the **same road** — a loop that
comes back over a different pass is a different drive, and two same-named
endpoints with a detour on one side are not comparable. And when one direction is
split into more legs than the other, the totals match but the individual legs do
not: say so and leave the split as a blank
(`distance_km: ______ · the return hop is 12 km for both of these legs
together`) rather than putting the whole figure on one leg.

Otherwise, take the leg's **origin** and **destination** coordinates from the leg
chain (see above). Build a Google Maps **directions** link and read the distance
off it:

```
https://www.google.com/maps/dir/?api=1&origin=<ORIGIN>&destination=<DEST>&travelmode=driving
```

- Prefer coordinates — `origin=47.4132,0.9857&destination=46.5802,0.3404`.
- If a coordinate is unknown, use the place name instead (URL-encoded):
  `origin=Amboise&destination=Poitiers`.
- If the leg carries route-shaping `waypoints`, add them so the distance follows
  the real road: `&waypoints=47.10,0.70|46.80,0.55`.

Entry (only lists the fields the warning flagged):

```
- **Road leg** Amboise → Poitiers · `days[4].activities[0].legs[0]`
  - distance_km: ______ · [open in Google Maps](https://www.google.com/maps/dir/?api=1&origin=47.4132,0.9857&destination=46.5802,0.3404&travelmode=driving)
  - duration: ______
```

(The link is only for the distance; leave `duration` a plain blank.)

### Hike — missing `distance_km` / `elevation_m` / `duration`

Search the web for the named trail (use its `start`/`end` and the day's region to
disambiguate). Fill your best figure, **always** tagged `[to be checked]`, and
back **every** web-derived value with its evidence: a clickable **link to the
source** and a short **verbatim quote** from that page showing the figure, so the
user can verify without re-searching:

```
- **Hike** Vézère valley riverside path · `days[5].activities[4]`
  - distance_km: 5 [to be checked]
    - source: [AllTrails — Montignac to Thonac riverside](https://www.alltrails.com/…)
    - quote: "Length 5.2 km • Elevation gain 40 m • Point to point"
  - elevation_m: 40 [to be checked]
    - source: [AllTrails — Montignac to Thonac riverside](https://www.alltrails.com/…)
    - quote: "Length 5.2 km • Elevation gain 40 m • Point to point"
  - duration: 1h30 [to be checked]
    - source: [Vallée de la Vézère — walks](https://www.lascaux-dordogne.com/…)
    - quote: "comptez 1 h 30 de marche entre Montignac et Thonac"
```

- Give a link **and** a quote for each value. If two values come from the same
  page, cite it under each (or reuse one `source`/`quote` block covering both).
- Quote only the words that state the figure — keep it short and exact; don't
  paraphrase (a paraphrase isn't evidence).
- Keep the `[to be checked]` tag on every web-derived value until the user
  removes it — never present an inferred figure as confirmed.
- If the web yields nothing reliable, leave the blank and say so:
  `______ [to be checked] · source: none found`.

### Activity / transport — missing `duration`

No link, no inference — just a blank to fill:

```
- **Point of interest** Musée du Louvre · `days[1].activities[2]`
  - duration: ______
- **Transport leg** New York JFK → Paris CDG (plane) · `transport[0].legs[0]`
  - duration: ______
```

---

## Value formats (put this at the top of the worksheet)

- **duration** — `"1h30"`, `"2h"`, `"45 min"`, or a plain number of minutes (`90`)
- **distance_km** — a bare number in kilometres (e.g. `42`)
- **elevation_m** — a bare number in metres (e.g. `800`)

No units or currency symbols go inside the JSON values.

---

## When you're done

Report a short summary: how many blanks you left for the user to fill, and how
many values you pre-filled from the web (all `[to be checked]`, each with a source
link and quote, needing confirmation). Once the user completes the worksheet, each value merges back into
its JSON path — durations/distances onto the activity or road leg, hike figures
onto the hike — after which `odysseyra-travelBook validate` should no longer warn.
