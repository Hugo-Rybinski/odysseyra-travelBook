# Skill: extract bookings

**Input:** any mix of raw booking material for one trip — screenshots or photos
of confirmations (treat them as images; do **not** assume the text is
selectable), an MBOX export of confirmation emails (e.g. a Gmail label saved via
Google Takeout), copy-pasted email/booking text, PDFs of vouchers, or plain
notes. Sources may be in any language and may overlap or contradict each other.

**Output:** a single Markdown **file** that gathers every booking found across
the sources into one structured, human-readable document,
one entry per booking, grouped by kind (transport / accommodation / car rental).
It is a faithful transcription of what the sources say, with each fact attributed
to its source and every gap and contradiction called out. Suggested filename —
include the moment it was generated (`<YYYY-MM-DD_HHhMM>`, the current date and
time): `bookings_<trip>_<YYYY-MM-DD_HHhMM>.md` (e.g.
`bookings_france-june2026_2026-05-03_12h34.md`). This file is meant to be fed
next to the **build full json** skill as clean, consolidated source material.

**This document is self-contained.** It defines the absolute no-invention rule,
how to read each input type, the exact list of fields to gather for each kind of
booking, the value formats to normalise to, the output template, and a final
checklist — you need no other file, no source code, and no tool.

**Start from a blank slate.** Work only from this skill and the documents
provided in this conversation — do not draw on past memory, earlier
conversations, or prior assumptions. If a fact is not in this skill or the
supplied sources, it does not exist for this task.

**Settle the language before you write anything.** The document's own wording is
yours to write — the headings, the field labels, the notes, the conflict and gap
descriptions. It must all be in **one** language. **If the language to use is
unclear — the sources are in one language and the request in another, the
sources are themselves mixed (they often are), or nothing states it — stop and
ask the user which language to write in before proceeding.** Do not guess, and
do not silently default to the sources' language. **Transcribed values are never
translated**: names, addresses, room types, conditions and quoted small print
stay exactly as the source prints them, in the source's language — translating
one would break the no-invention rule below. The choice governs only the prose
around them (including the `— not in sources` / `— illegible in source` markers,
which you may render in the chosen language as long as you use one wording
throughout).

---

## Absolute rule — never invent or infer

Transcribe; do not create. Every value in the file must be **explicitly
present in the provided sources**.

- Do **not** invent, infer, estimate, complete, "correct", or silently
  supplement any fact — not a price, a time, a terminal, a room type, an
  address, a confirmation number, a timezone, nothing.
- Do **not** use general knowledge, memory, assumptions, map knowledge, airline
  timetables, or outside sources to fill a gap. (The only transformation allowed
  is **transcription formatting** — rewriting a stated value into the canonical
  format below, e.g. "June 8, 2026, 6 pm" → `2026-06-08` / `18:00`. That is not
  invention; changing or adding information is.)
- If a field is not stated in the sources, write it as **`— not in sources`**.
  Never guess it, and never leave it silently absent.
- If two sources disagree, keep **both** values and record the conflict (see
  *Conflicts* below) — do not pick one silently.
- If you genuinely cannot tell whether something is a booking, list it under
  *Uncertain / needs confirmation* rather than dropping or promoting it.

When in doubt, prefer `— not in sources` over a plausible-looking value.

---

## How to read each input type

- **Screenshots / photos / scanned PDFs** — read them **visually**, page by page;
  do not assume any text layer. Transcribe exactly what is printed, including
  confirmation numbers and small print. If part of an image is illegible, say so
  (`— illegible in source`) rather than guessing.
- **MBOX exports** — each message is one confirmation (or update) email. For every
  message, scan the body **and**, where present, the HTML part. Pull the
  reservation reference / PNR, the booking source (sender/brand), the price, the
  dates and times, and especially the **direct "manage / view / modify your
  booking" link** — prefer that stable link over one-time tracking URLs. When a
  later email amends an earlier one for the same reservation, treat the latest as
  current and note the change as a conflict.
- **Copy-pasted text / notes** — transcribe the stated values; apply the same
  no-invention rule. Fragmentary notes often omit fields — mark those
  `— not in sources`.

Always record **which source** each entry (and each conflicting value) came from,
e.g. *"(from booking.com email, 2026-05-02)"* or *"(from screenshot IMG_2231)"*.

---

## What is a booking

Gather four kinds. The test is a **reservation**: something with a date/time, a
confirmation, a ticket, or a payment attached to it. A mere idea or a place with
no reservation (a sightseeing suggestion, a restaurant you haven't booked) is
**not** a booking — leave it out.

1. **Transport** — one leg of inter-city travel: a flight, train, bus, taxi, or
   ferry. One entry **per leg** (Paris → New York via London = two entries).
2. **Accommodation** — one stay in one place: hotel, campsite, B&B, other. One
   entry per stay; two towns = two entries.
3. **Car rental** — one rental-car booking, with its booking window and its
   pick-up / drop-off events.
4. **Activity** — a **booked** experience with a reservation or ticket: a guided
   tour, a timed-entry museum/monument ticket, a show, a boat trip, a tasting, a
   cooking class, etc. Include it only when the source shows an actual booking
   (a date/time, a ticket, a reference, or a payment) — not a "things to do"
   list. One entry per booked activity.

---

## Value formats to normalise to

Transcribe stated values into these exact formats (this is formatting, not
invention). If a value isn't stated, use `— not in sources`.

| Kind | Write it as | Examples |
|---|---|---|
| **Date** | `YYYY-MM-DD` | `2026-06-08` |
| **Time** | 24-hour `HH:MM` (local time as printed) | `09:00`, `18:45` |
| **Duration** | `<h>h<mm>` / `<n> min` | `1h30`, `45 min` |
| **Timezone** | UTC offset `+HH:MM` — only if the source states it | `+02:00`, `-04:00` |
| **Price** | the number **and** its currency, exactly as stated | `89 EUR`, `256.50 GBP` |
| **Payment** | `paid` or `to pay` — only if the source says so | `paid` |
| **Status** | `booked` or `confirmed` — only if the source says so | `confirmed` |
| **Link** | the full URL, verbatim | `https://…` |

Keep the price's real currency even if it isn't EUR and you have no exchange
rate — the currency travels with the amount; never convert it yourself.

**Ignore a source's own conversion — keep only the charged amount.** When a
source states a price with a parenthetical/approximate conversion into another
currency (e.g. `$100 (≈ €98.54)` or `100 USD, about 98.54 EUR`), record **only
the original charged amount and its currency** (`100 USD`) and drop the
converted figure. The two are not a conflict.

---

## Fields to gather

For each booking, capture every field below **that the sources state**; mark the
rest `— not in sources`. Field names mirror the `build full json` schema so the
file maps cleanly downstream.

### Transport (per leg)

- **type** — `plane` / `train` / `bus` / `taxi` / `ferry` / `other`
- **start** — departure point (station / airport / city)
- **end** — arrival point
- **start_date**, **start_time** — departure date & local time
- **end_date**, **end_time** — arrival date & local time
- **start_tz**, **end_tz** — departure / arrival UTC offset (esp. for flights
  between zones) — only if stated
- **duration** — if the source states it
- **flight_number** (planes) / **train_number** (trains) — the public service ID
- **booking_number** — reservation reference / PNR (distinct from the service ID)
- **booking_source** — where it was booked (e.g. "SNCF Connect")
- **website** — carrier's site
- **booking_link** — direct manage-booking URL
- **status** — `booked` / `confirmed`
- **price** — amount + currency
- **paid** — `paid` / `to pay`
- **seat / class / baggage / extras** — capture verbatim under *Notes* if stated
- **passengers** — names, if stated

### Accommodation (per stay)

- **name** — property name
- **arrival** — check-in date
- **departure** — check-out date
- **city** — town / city
- **type** — `hotel` / `camping` / `b&b` / `other`
- **address** — street address
- **contact** — phone or email
- **booking_source** — e.g. "Booking.com"
- **website**
- **booking_link** — direct manage-booking URL
- **status** — `booked` / `confirmed`
- **price** — amount + currency (for the whole stay, if stated as such — note the
  basis)
- **paid** — `paid` / `to pay`
- **breakfast_included** — yes / no
- **room type / guest count / cancellation policy** — under *Notes* if stated

### Car rental (per booking)

- **company** — e.g. "Europcar"
- **booking_start_date / booking_start_time** — when the booking window opens
- **booking_end_date / booking_end_time** — when it closes
- **pickup_date / pickup_time**, **pickup_location**
- **dropoff_date / dropoff_time**, **dropoff_location** (note if same as pick-up)
- **timezones** — for any of the four datetimes, only if stated
- **booking_number** — reservation reference
- **website**, **booking_link**
- **status** — `booked` / `confirmed`
- **price** — amount + currency
- **paid** — `paid` / `to pay`
- **car_type** — `regular` / `small` / `suv` / `4x4`
- **car_model** — e.g. "Dacia Duster"
- **contact** — rental-desk phone / email
- **additional_drivers** — count, if stated
- **insurance / mileage / deposit** — under *Notes* if stated

### Activity (booked)

Activities have no dedicated booking fields downstream, so capture the essentials
plus the reservation details as notes — `build full json` will place them (times
on the activity, the reference/price in its description).

- **name** — what it is (e.g. "Sagrada Família guided tour")
- **kind** — tour / ticket / entry / show / experience, as described
- **date** — the booked date
- **start_time** — timed-entry / tour start time (local), if stated
- **end_time** / **duration** — if stated
- **location** — venue / meeting point
- **address** — if stated
- **booking_number** — reservation reference / ticket number
- **booking_source** — where booked (e.g. "GetYourGuide")
- **website**, **booking_link** — direct manage / e-ticket URL
- **status** — `booked` / `confirmed`
- **price** — amount + currency
- **paid** — `paid` / `to pay`
- **participants** — count / names, if stated
- **Notes** — language, inclusions, conditions, verbatim if stated

---

## Output template

Produce Markdown shaped like this. Include a section only if you found at least
one booking of that kind. Under each field, write the value or `— not in
sources`, followed by the source in parentheses.

```markdown
# Bookings — [trip name if stated, else "untitled trip"]

- Sources: [list each source you were given, e.g. "Gmail 'trip' label MBOX",
  "3 screenshots", "pasted hotel email"].
- Every value below is transcribed from those sources. `— not in sources` means
  the sources did not state it. Conflicts are listed at the end.

## Transport

### T1 — [start] → [end], [start_date]
- type: plane (from …)
- start: Paris CDG, Terminal 2E (from …)
- end: Toulouse-Blagnac (from …)
- start_date: 2026-06-08 (from …)
- start_time: 07:35 (from …)
- end_time: 08:55 (from …)
- flight_number: AF7512 (from …)
- booking_number: XR4K2P (from …)
- booking_source: Air France (from …)
- booking_link: https://… (from …)
- status: confirmed (from …)
- price: 129 EUR (from …)
- paid: paid (from …)
- passengers: Jane Doe, John Doe (from …)
- Notes: 1 checked bag included (from …)
- Missing: end_date, start_tz, end_tz, duration, website — not in sources.

## Accommodation

### A1 — [name], [city]
- name: … (from …)
- arrival: … (from …)
- departure: … (from …)
- …
- Missing: … — not in sources.

## Car rental

### C1 — [company], pick-up [pickup_location]
- company: … (from …)
- …
- Missing: … — not in sources.

## Activities

### AC1 — [name], [date]
- name: … (from …)
- kind: … (from …)
- date: … (from …)
- start_time: … (from …)
- booking_number: … (from …)
- price: … (from …)
- …
- Missing: … — not in sources.

## Conflicts
- **A1 price** — booking email says 256 EUR, screenshot says 268 EUR. Both kept;
  not resolved.
- …

## Uncertain / needs confirmation
- A message mentions a "return shuttle" but gives no date, time, or reference —
  possibly a booking, left out pending confirmation.
```

Order entries chronologically within each section when dates are known;
otherwise keep source order. Number them (`T1`, `A1`, `C1`, `AC1`) so the
conflict list can reference them.

---

## Conflicts, duplicates, and updates

- **Conflict:** two sources give different values for the same field of the same
  booking → keep both inline (`price: 256 EUR (email) / 268 EUR (screenshot)`) and
  add a bullet to the **Conflicts** section naming the field and both values. Do
  not choose between them — that is `build full json`'s job.
- **Tiny price differences are not a conflict.** If two sources give prices that
  differ by **1 unit or less** in the same currency (e.g. 256 vs 256.50, or 256
  vs 257 — rounding, fees), treat them as equal: record either value and do
  **not** raise a conflict. Only flag a price conflict when the gap exceeds 1
  (or the currencies differ).
- **Duplicate:** the same booking appears in several sources with matching values
  → record it once, listing all the sources it was confirmed by.
- **Update:** a later email changes an earlier one (new time, new room) → use the
  latest value in the entry and note the change under **Conflicts** with dates,
  so the trail is visible.

---

## Before you deliver — checklist (internal — do NOT put in the file)

Run this check on yourself before returning the file. It is for your own
verification only: **do not include this checklist (or any task/tick list) in the
generated `.md`** — the file ends at the *Uncertain / needs confirmation*
section. Perform every check; just don't write it out.

- [ ] Every value is present in the sources; nothing was invented, inferred, or
      filled from outside knowledge.
- [ ] Every unstated field is marked `— not in sources` (not silently omitted).
- [ ] Each fact and each conflicting value names the source it came from.
- [ ] One entry per transport leg, per stay, per car rental, per booked activity
      — nothing collapsed.
- [ ] Only genuinely booked activities are listed (a reservation/ticket exists);
      sightseeing ideas are not.
- [ ] Prices keep their real currency and amount, unconverted.
- [ ] Dates/times normalised to `YYYY-MM-DD` / `HH:MM`; nothing else changed.
- [ ] Direct booking links captured where the sources contain them.
- [ ] Conflicts, duplicates, and later-email updates are all recorded.
- [ ] Anything ambiguous is under *Uncertain / needs confirmation*, not guessed.
- [ ] The file is valid Markdown, self-explanatory without the original sources.
