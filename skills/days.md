# Skill: `days/day-<INDEX>.json`

**Target file:** `<ROOT>/days/day-<INDEX>.json` — **one file per day**.

Files are read in **filename order and that becomes the day order**, so number
them along the trip with a zero-padded index: `day-01.json`, `day-02.json`, …

Each file is one **day**: a title, optional date/city/intro, and an ordered
list of **activities** (what you do, in sequence).

## The day object

| Field | Required | Format | Default | Notes |
|---|---|---|---|---|
| `title` | **yes** | text | — | The day's headline (e.g. "The Sanctuary & Old Town"). |
| `date` | no | date `YYYY-MM-DD` | trip start + this day's index | Set it if the source states the date; otherwise it's inferred from position. |
| `city` | no | text | none | City/region label (e.g. "Lourdes", or "Paris → Lourdes"). |
| `description` | no | text | none | An intro paragraph for the day. |
| `activities` | **yes** | array (non-empty) | — | The ordered timeline — see below. |

## Activities

`activities` is an ordered array of objects, each with a `type`. There are six
types. **Timing is usually inferred** — you rarely need to give every time:

- Provide **any two** of `start_time` / `end_time` / `duration` and the third
  is computed. Give one, or none, and the chain fills in.
- The first activity starts at the day's default start (`default.start_time`,
  else 08:00). Each next activity starts when the previous one ends.
- Gaps (and the trip's default buffer) become **buffer** activities
  automatically — you seldom add those by hand.

So: capture the **order** and whatever concrete times/durations the source
gives; leave the rest out.

### Scheduling fields (any non-`buffer` activity may include these)

| Field | Format | Notes |
|---|---|---|
| `start_time` | time `HH:MM` | Clock start. |
| `end_time` | time `HH:MM` | Clock end. |
| `duration` | duration (`"1h30"`, `"45 min"`) | How long it lasts. |
| `start_tz` / `end_tz` | UTC offset | Only if this activity is in a different timezone than the trip default. |

### Type `road` — a drive or transfer

| Field | Required | Format | Notes |
|---|---|---|---|
| `start` | **yes** | text | Where the drive begins. |
| `end` | **yes** | text | Where it ends. |
| `distance_km` | no | positive number | Driving distance. |
| `off_road` | no | boolean | `true` if part is off-road. |
| `activities` | no | array of **meal** objects | Meal stops along the drive (see nesting). |

### Type `point_of_interest` — a specific sight

| Field | Required | Format | Notes |
|---|---|---|---|
| `name` | **yes** | text | The place's name. |
| `category` | no | enum (default `other`) | One of: `museum`, `church`, `building`, `viewpoint`, `ruins`, `castle`, `temple`, `street`, `natural park`, `mountain`, `lake`, `beach`, `waterfall`, `other`. |
| `address` | no | text | |
| `description` | no | text | |
| `activities` | no | array of `point_of_interest` / `hike` / `meal` | Nested sights/hikes/meals (see nesting). |

### Type `place` — a town/area grouping several stops

| Field | Required | Format | Notes |
|---|---|---|---|
| `name` | **yes** | text | The place name. |
| `description` | no | text | |
| `activities` | no | array of `point_of_interest` / `hike` / `meal` | The things you do there. |

### Type `hike`

| Field | Required | Format | Notes |
|---|---|---|---|
| `name` | **yes** | text | Trail/hike name. |
| `distance_km` | recommended | number | Length; `validate` warns if missing. |
| `elevation_m` | no | number | Elevation gain in metres. |
| `start` | no | text | Trailhead. |
| `end` | no | text | End point. |
| `route` | no | enum (default `back_and_forth`) | One of `loop`, `back_and_forth`, `one_way`. For `loop`/`back_and_forth`, `end` should match `start` (or be omitted); for `one_way`, `end` should differ. |
| `activities` | no | array of **meal** objects | Meal stops along the hike. |

### Type `meal` — a stop to eat

| Field | Required | Format | Notes |
|---|---|---|---|
| `meal_type` | no | enum | One of `breakfast`, `lunch`, `dinner`, `brunch`, `snack`, `picnic`, `meal`. **If omitted it is inferred** from the start time as breakfast/lunch/dinner (using `default.breakfast_until`/`lunch_until`). Set it explicitly for brunch/snack/picnic/meal. |
| `restaurant` | no | text | The restaurant's name. |
| `area` | no | text | Where to eat, if no named restaurant. Ignored when `restaurant` is set. |
| `address` | no | text | |

### Type `buffer` — explicit free time

| Field | Required | Format | Notes |
|---|---|---|---|
| `duration` | **yes** | duration (`"30 min"`) | Length of free time. A `0`-minute buffer *suppresses* the default buffer at that point. |

Only add `buffer` when the source explicitly calls for a fixed break; gaps are
otherwise generated for you.

## Nesting rules

A container activity can hold a nested `activities` array, **one level deep
only** (a nested activity may not itself nest). Allowed nesting:

| Container | May nest |
|---|---|
| `road` | `meal` |
| `hike` | `meal` |
| `place` | `point_of_interest`, `hike`, `meal` |
| `point_of_interest` | `point_of_interest`, `hike`, `meal` |

## Example

Source: *"Day 2 in Lourdes — the Sanctuary of Our Lady (a church) all morning,
ending at 12:30, lunch at Le Magret, then wander the old town from 13:30 for
about 1h30, visiting the Château fort (a castle, ~45 min)."*

```json
{
  "date": "2026-06-09",
  "city": "Lourdes",
  "title": "The Sanctuary & Old Town",
  "description": "A full day in Lourdes: the pilgrimage sanctuary in the morning and the château fort quarter in the afternoon.",
  "activities": [
    {
      "type": "point_of_interest",
      "name": "Sanctuary of Our Lady of Lourdes",
      "category": "church",
      "address": "1 Av. Mgr Théas, Lourdes",
      "end_time": "12:30"
    },
    {
      "type": "meal",
      "restaurant": "Le Magret",
      "address": "10 Rue de la Grotte, Lourdes",
      "start_time": "12:30"
    },
    {
      "type": "place",
      "name": "Lourdes old town",
      "start_time": "13:30",
      "duration": "1h30",
      "activities": [
        {
          "type": "point_of_interest",
          "name": "Château fort de Lourdes",
          "category": "castle",
          "duration": "45 min"
        }
      ]
    }
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
