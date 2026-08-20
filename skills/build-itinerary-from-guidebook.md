# Skill: build a detailed day-by-day itinerary from a guidebook PDF

**Input:** a guidebook PDF (often a scan — do **not** assume the text is
selectable) covering the trip's region, **and** a very brief trip outline — a
sequence of days → destinations (e.g. `Day 1 → Paris`, `Day 2 → Mont
Saint-Michel`, …). The outline need not carry any timings or activities.

**Output:** a single Markdown file
(`<destination>_<dates>_detailed_itinerary.md`) that expands each day of the
outline into a detailed, chronological, guidebook-sourced program — activities
with a few descriptive lines, clearly-labelled walks/hikes with whatever metrics
the guide gives, explicit **"Route from X to Y"** entries between localities, and
printed-page citations throughout. It enriches the supplied outline; it does not
redesign the trip.

**This document is self-contained.** It defines the source-fidelity rule, the
research method (page numbering, destination index, route corridors), the
per-activity detail level, the Markdown structure, and a full quality-control
checklist — you need no other file, no source code, and no tool.

---

## Purpose

This workflow explains how to turn:

1. a **guidebook PDF**, and
2. a **very brief trip outline**

into a detailed Markdown itinerary.

The method is designed for an outline as short as:

```text
Day 1 -> Paris
Day 2 -> Mont Saint-Michel
Day 3 -> Saint-Malo
Day 4 -> Loire Valley
Day 5 -> Paris
```

The final Markdown file should:

- expand each day into a detailed program;
- use the guidebook as the primary source;
- include the activities the guide suggests in each visited area;
- include relevant activities mentioned by the guide along the route between overnight stops;
- insert an explicit **"Route from X to Y"** entry whenever consecutive activities are in different locations;
- describe each activity in a few useful lines;
- clearly highlight hikes and walks;
- include duration, distance, elevation gain, and other quantitative details when the guide provides them;
- reference the **printed page number in the guidebook**, not the PDF viewer page number;
- avoid inventing facts that are absent from the guide;
- avoid judgments about whether a day is too busy, too long, realistic, unrealistic, easy, difficult, or well balanced unless the guide itself explicitly makes such a statement.

The objective is not to redesign the trip. The objective is to **enrich the supplied outline with as much guidebook-supported information as possible**.

## Absolute source-fidelity rule

The LLM **must not invent, infer, estimate, complete, correct, or silently supplement any factual information**.

Every factual statement in the final itinerary must be supported by the supplied guidebook PDF. This applies to, among other things:

- attraction descriptions;
- historical facts and dates;
- locations;
- road distances;
- driving times;
- walking times;
- hike distances;
- elevation gain or loss;
- difficulty;
- opening hours;
- entrance prices;
- seasonal access;
- transport information;
- permits;
- recommended activities;
- route suggestions;
- geographic relationships between places.

If the guidebook does not state a fact, the LLM must either omit it or explicitly write that the information is **not specified by the guide**.

The LLM must **not use general knowledge, memory, assumptions, common sense, map knowledge, or outside sources** to fill gaps unless the user explicitly asks for external research. If external research is requested, information from outside the guidebook must be clearly separated and labelled as external.

The guidebook is the sole factual source by default.

---

# 1. Inputs

## 1.1 Guidebook PDF

The PDF is the source of truth for:

- destination descriptions;
- attractions;
- museums;
- monuments;
- viewpoints;
- cultural activities;
- scenic drives;
- road-trip suggestions;
- hikes and walks;
- practical information;
- distances;
- durations;
- elevation gain;
- access information;
- opening times if useful;
- transport notes;
- nearby excursions;
- places suggested along the road between two destinations.

The guidebook may contain:

- normal body text;
- maps;
- sidebars;
- "don't miss" boxes;
- suggested itineraries;
- road-trip panels;
- hiking cards;
- tables;
- captions;
- practical-information boxes;
- icons and legends.

All of these should be treated as potentially useful source material.

## 1.2 Brief itinerary outline

Assume the outline contains little more than a sequence of days and destinations.

Example:

```text
Day 1 -> Paris
Day 2 -> Mont Saint-Michel
Day 3 -> Saint-Malo
Day 4 -> Amboise
Day 5 -> Paris
```

It may optionally contain a little extra information:

```text
Day 1 -> Paris
Day 2 -> Pick up car + drive to Mont Saint-Michel
Day 3 -> Mont Saint-Michel + Saint-Malo
Day 4 -> Loire Valley
Day 5 -> Return to Paris
```

Do not require the input to contain detailed timings or activities.

---

# 2. Output

Produce one Markdown file.

Recommended filename:

```text
<destination>_<dates>_detailed_itinerary.md
```

Example:

```text
france_10-14_may_2027_detailed_itinerary.md
```

The file should be:

- chronological;
- organized day by day;
- written mostly as bullet points;
- detailed but readable;
- easy to edit manually afterward;
- fully understandable without the original conversation.

---

# 3. Establish the guidebook's printed page numbering

This is one of the most important steps.

PDF page numbers and guidebook page numbers are often different.

For example:

- PDF viewer page 12 may show printed page **61**;
- PDF viewer page 13 may show printed page **62**.

Always cite the number physically printed on the page.

Use:

```text
**Page 61.**
```

or:

```text
**Pages 61-63.**
```

Do not use:

```text
PDF page 12
```

unless the user explicitly requests PDF page indices.

## How to determine the mapping

Inspect several pages and record:

```text
PDF page 12 -> printed page 61
PDF page 13 -> printed page 62
PDF page 14 -> printed page 63
```

If the offset is consistent, it can help navigation, but still verify printed numbers whenever possible because:

- front matter may be unnumbered;
- inserts may interrupt pagination;
- maps may span pages;
- chapter breaks may affect the offset.

---

# 4. Build a destination index before writing the itinerary

Do not start writing immediately.

First identify all major destinations from the outline.

For the fictional example:

```text
Paris
Mont Saint-Michel
Saint-Malo
Amboise / Loire Valley
Paris
```

Then search the guidebook for each one.

For every destination, collect:

- the main destination section;
- nearby excursions;
- walks and hikes;
- museums;
- monuments;
- viewpoints;
- neighbourhoods;
- scenic routes;
- cultural experiences;
- relevant sidebars;
- relevant road-trip suggestions;
- nearby places explicitly recommended by the guide.

A useful working table is:

| Location | Printed pages | Main activities | Walks/hikes | Nearby excursions |
|---|---:|---|---|---|
| Paris | 40-65 | Louvre, Île de la Cité, Marais | Seine walk | Versailles |
| Mont Saint-Michel | 120-124 | Abbey, ramparts | Bay walk | Avranches |
| Saint-Malo | 126-131 | Old town, walls | Coastal walk | Cancale |
| Loire Valley | 180-205 | Chambord, Chenonceau | Forest walks | Amboise |

This is an internal research aid. It does not need to appear in the final file.

---

# 5. Read destination sections broadly, not just exact place-name matches

A common mistake is to extract only the paragraph directly under a place name.

Instead, inspect the entire relevant section.

A destination chapter may contain:

- a city introduction;
- a "top sights" list;
- a map;
- an attraction description on the following page;
- a walking tour two pages later;
- a day-trip sidebar;
- a road-trip panel;
- a practical box with access information.

All of these may contribute to the itinerary.

For example, a fictional Paris section might contain:

- Louvre Museum — p. 44
- Île de la Cité — p. 46
- Sainte-Chapelle — p. 47
- Le Marais — p. 50
- "Walk through historic Paris" — p. 52
- Canal Saint-Martin — p. 56
- Versailles day trip — p. 63

If Day 1 is simply "Paris", these are all candidate activities.

---

# 6. Identify activities suggested by the guide

For every relevant area, extract explicit activities.

Typical activity types include:

- visit a museum;
- visit a church, castle, abbey, archaeological site, or historic building;
- walk through a neighbourhood;
- follow a signed walking route;
- hike to a viewpoint;
- visit a market;
- visit a local workshop;
- take a boat trip;
- go to a beach;
- visit a thermal bath;
- see a waterfall;
- explore a canyon;
- take a scenic road;
- visit a viewpoint;
- attend a cultural performance;
- visit a memorial;
- stop at a village;
- take part in a food or craft experience.

Do not reduce everything to only the most famous sights.

If the guide clearly suggests an activity in the zone, include it somewhere in the relevant day's list, either:

1. in the main program, or
2. under an **"Other activities suggested by the guide in this area"** subsection.

---

# 7. Extract activity descriptions

Each activity should receive a short description of several lines.

The description should explain:

- what the place or activity is;
- why it is mentioned by the guide;
- what the visitor actually sees or does;
- any distinctive historical, cultural, architectural, or natural feature described by the guide.

Avoid vague descriptions such as:

```text
- Visit the Louvre.
  - Famous museum in Paris.
```

Prefer:

```text
- **Louvre Museum**
  - The guide presents the Louvre as one of the major collections of art and antiquities in the city.
  - Its galleries cover multiple periods and civilizations, with collections ranging from ancient archaeology to European painting.
  - The visit can be focused on a selected department rather than attempting to cover the entire museum.
  - **Pages 44-45.**
```

The description should be based on the guidebook, not generic encyclopedic knowledge.

---

# 8. Extract hikes and walks separately

Walks and hikes should be visually easy to identify.

Use a consistent label such as:

```text
- **Hike — Coastal path to Pointe du Grouin**
```

or:

```text
- **Walk — Historic centre of Paris**
```

For every walking or hiking route, extract all quantitative information supplied by the guide.

Possible fields:

- distance;
- duration;
- elevation gain;
- elevation loss;
- highest point;
- start point;
- end point;
- route type: loop / out-and-back / point-to-point;
- terrain;
- access information.

Example:

```text
- **Hike — Cap Fréhel coastal loop**
  - A coastal route following cliffs and heathland, with viewpoints over the sea and lighthouse.
  - **Distance:** 11 km.
  - **Duration:** 3 hr 30 min.
  - **Elevation gain:** 280 m.
  - **Route type:** loop.
  - **Page 134.**
```

## If a metric is absent

Say so explicitly.

Example:

```text
- **Walk — Ramparts of Saint-Malo**
  - The guide recommends walking the walls around the old town for elevated views over the harbour, beaches, and historic centre.
  - **Distance:** not specified by the guide.
  - **Duration:** not specified by the guide.
  - **Elevation gain:** not specified by the guide.
  - **Page 128.**
```

Do not estimate missing values unless the user explicitly asks for estimates or outside research.

---

# 9. Extract road-trip and "on the way" suggestions

This step is essential when the itinerary moves between destinations.

Suppose the outline contains:

```text
Day 2 -> Paris to Mont Saint-Michel
```

Do not only research Paris and Mont Saint-Michel.

Also inspect:

- road-trip pages;
- regional maps;
- "on the way" boxes;
- nearby towns along the corridor;
- suggested detours;
- viewpoints;
- historic sites near the route.

The guide may suggest stops such as:

```text
Giverny
Rouen
Bayeux
Avranches
```

Only include stops that the guide actually suggests and that are geographically relevant to the route.

Do not add famous places merely because you know them.

---

# 10. Insert explicit route entries between different locations

Whenever two consecutive activities are not in the same city or local site, insert a route entry.

Use this exact structural principle:

```text
- **Route from Paris to Giverny**
  - Leave Paris and travel northwest toward Giverny.
  - The guide presents Giverny as a possible cultural stop in the Seine valley.
  - **Page 82.**

- **Claude Monet's House and Gardens**
  - ...
```

Then, if the next stop is somewhere else:

```text
- **Route from Giverny to Rouen**
  - Continue west along the Seine corridor toward Rouen.
  - **Pages 84-86.**
```

Do not add route entries between attractions in the same city.

For example, this is unnecessary:

```text
Route from Louvre to Sainte-Chapelle
```

if both are treated as central Paris activities.

But this is appropriate:

```text
Route from Paris to Versailles
```

because Versailles is a separate location.

## Apply the same rule to natural areas

Use route transitions such as:

```text
- **Route from Saint-Malo to Cancale**
- **Route from Cancale to Pointe du Grouin**
- **Route from Amboise to Château de Chenonceau**
```

The concept is geographic, not administrative: if the itinerary clearly changes locality, add a route line.

---

# 11. Order activities geographically

Once all activities are extracted, arrange them in a logical travel sequence.

For example, Day 3 might initially have these notes:

```text
Saint-Malo old town
Cancale
Saint-Malo ramparts
Pointe du Grouin
Saint-Malo cathedral
```

Reorder them:

```text
Saint-Malo old town
Saint-Malo cathedral
Saint-Malo ramparts
Route from Saint-Malo to Cancale
Cancale harbour
Route from Cancale to Pointe du Grouin
Pointe du Grouin walk
```

This avoids unnecessary backtracking in the written itinerary.

The goal is not to optimize driving with external mapping software. It is simply to present the guidebook activities in a geographically coherent order.

---

# 12. Preserve the user's overnight destinations

The supplied outline defines the trip structure.

If the outline says:

```text
Day 2 -> Mont Saint-Michel
Day 3 -> Saint-Malo
```

the expanded itinerary should continue to respect those overnight destinations unless the user explicitly asks for itinerary changes.

The guidebook is used to enrich the program, not silently change the trip.

---

# 13. Do not make timing judgments

Avoid editorial comments such as:

```text
This day is too ambitious.
This schedule is unrealistic.
You will not have enough time.
This should be easy.
This is a relaxed day.
This route is inefficient.
```

Instead, provide factual information.

Bad:

```text
- This is a very long driving day and the schedule is too ambitious.
```

Better:

```text
- **Route from Paris to Mont Saint-Michel**
  - The guide lists the road distance as 360 km.
  - **Driving time:** 4 hr 15 min.
  - **Page 121.**
```

Let the reader decide how to use the facts.

If the guide itself says something like "allow a full day", that statement may be included and attributed to the guide.

---

# 14. Distinguish facts from unknowns

Use only information supported by the guidebook.

If the guide provides:

```text
Distance: 14 km
Duration: 4 hours
```

include those values.

If elevation is missing:

```text
Elevation gain: not specified by the guide.
```

Do not infer:

```text
Elevation gain: approximately 450 m
```

unless outside research or estimation has explicitly been requested.

Likewise, do not invent:

- road distances;
- transfer durations;
- entrance prices;
- opening hours;
- hike statistics;
- historical dates;
- seasonal availability.

---

# 15. Use guidebook maps as source material

Maps often contain information not repeated in body text.

Inspect map labels for:

- named attractions;
- viewpoints;
- villages;
- museums;
- trailheads;
- waterfalls;
- lakes;
- transport hubs;
- scenic roads;
- suggested stops.

If a map identifies an attraction that is also described elsewhere, use the descriptive page as the main citation.

If the map itself is the only source, cite the map's printed page.

Example:

```text
- **Route from Amboise to Château de Chenonceau**
  - The regional map places Chenonceau southeast of Amboise along the suggested château circuit.
  - **Page 188.**
```

---

# 16. Use guidebook sidebars and boxed itineraries

Many guidebooks contain high-value boxed content such as:

```text
If you have one day...
If you have three days...
Road trip...
Best walks...
Don't miss...
Suggested excursions...
```

These should be treated as strong editorial recommendations.

If a box explicitly recommends a stop that lies in the user's route, include it even if the main destination paragraph is brief.

For example:

```text
- **Other activities suggested by the guide in the Loire Valley**
  - **Château de Chaumont-sur-Loire** — highlighted in the guide's suggested château circuit for its gardens and hilltop setting. **Page 194.**
  - **Château de Villandry** — recommended for its formal gardens. **Pages 198-199.**
```

---

# 17. Build each day in two layers

For clarity, distinguish:

## Layer A — Main day sequence

This is the chronological/geographic sequence that matches the supplied trip.

Example:

```text
## Day 3 — Mont Saint-Michel to Saint-Malo

- Mont Saint-Michel Abbey
- Ramparts
- Route from Mont Saint-Michel to Cancale
- Cancale harbour
- Route from Cancale to Saint-Malo
- Saint-Malo old town
- Ramparts walk
```

## Layer B — Additional guide-suggested activities

Then add:

```text
- **Other activities suggested by the guide in the area**
  - ...
```

This prevents secondary suggestions from obscuring the actual route.

---

# 18. Recommended Markdown structure

Use the following template.

```markdown
# Detailed itinerary — [destination and dates]

- Source: supplied guidebook PDF.
- All page references use the printed page numbers in the guidebook.
- Activities, descriptions, route notes, and hike statistics are taken from the guide unless explicitly stated otherwise.

## Day 1 — [main destination]

- **Activity**
  - Description line 1.
  - Description line 2.
  - Description line 3.
  - **Page X.**

- **Walk — Name**
  - Description.
  - **Distance:** X km.
  - **Duration:** X hr.
  - **Elevation gain:** X m.
  - **Page X.**

- **Other activities suggested by the guide in the area**
  - **Activity A** — short description. **Page X.**
  - **Activity B** — short description. **Page X.**

- **Night**
  - [Location]

## Day 2 — [origin to destination]

- **Route from Origin to Stop A**
  - Route description.
  - **Page X.**

- **Activity at Stop A**
  - Description.
  - **Page X.**

- **Route from Stop A to Destination**
  - Route description.
  - **Pages X-Y.**

- **Activity at Destination**
  - Description.
  - **Page X.**

- **Night**
  - [Destination]
```

---

# 19. Full fictional example

Input outline:

```text
Day 1 -> Paris
Day 2 -> Mont Saint-Michel
Day 3 -> Saint-Malo
Day 4 -> Loire Valley
Day 5 -> Paris
```

A shortened example of the expanded result could look like this:

```markdown
# Detailed itinerary — France

- Source: supplied guidebook PDF.
- All page references use the guidebook's printed page numbers.

## Day 1 — Paris

- **Île de la Cité**
  - The guide presents the island as one of the historic cores of Paris.
  - A visit can combine the riverfront, medieval monuments, and the streets surrounding Notre-Dame.
  - **Pages 46-48.**

- **Sainte-Chapelle**
  - Gothic royal chapel known for its large stained-glass windows.
  - The guide highlights the upper chapel and the Biblical scenes covering the glass panels.
  - **Page 47.**

- **Walk — Historic Paris**
  - A guidebook walking route linking several historic monuments and neighbourhoods in the centre.
  - **Distance:** 5 km.
  - **Duration:** 2 hr.
  - **Elevation gain:** not specified by the guide.
  - **Page 52.**

- **Other activities suggested by the guide in Paris**
  - **Louvre Museum** — major art and archaeology collection. **Pages 44-45.**
  - **Le Marais** — historic district with old mansions, narrow streets, museums, and shops. **Pages 50-51.**
  - **Canal Saint-Martin** — waterside neighbourhood suggested for an evening walk. **Page 56.**

- **Night**
  - Paris.

## Day 2 — Paris to Mont Saint-Michel

- **Route from Paris to Giverny**
  - Travel northwest from Paris into the Seine valley.
  - The guide includes Giverny as a cultural stop along this corridor.
  - **Page 82.**

- **Claude Monet's House and Gardens**
  - Visit the artist's house, flower garden, and water garden.
  - The guide emphasizes the relationship between the gardens and Monet's paintings.
  - **Pages 82-83.**

- **Route from Giverny to Rouen**
  - Continue west through the Seine valley toward Rouen.
  - **Pages 84-86.**

- **Rouen historic centre**
  - Explore the cathedral area and streets of timber-framed houses.
  - The guide also mentions the Gros-Horloge and the old market square.
  - **Pages 85-87.**

- **Route from Rouen to Mont Saint-Michel**
  - Continue west into Normandy toward Mont Saint-Michel.
  - **Pages 118-121.**

- **Mont Saint-Michel ramparts**
  - Walk along the fortified edge of the village for views across the bay.
  - The guide describes the walls as one of the main ways to understand the site's defensive position and surrounding landscape.
  - **Page 122.**

- **Night**
  - Mont Saint-Michel.

## Day 3 — Mont Saint-Michel to Saint-Malo

- **Mont Saint-Michel Abbey**
  - Visit the monastic complex above the village.
  - The guide describes the church, cloister, halls, and layered medieval architecture built into the rock.
  - **Pages 122-124.**

- **Route from Mont Saint-Michel to Cancale**
  - Follow the coast west toward Cancale.
  - **Pages 126-127.**

- **Cancale harbour**
  - The guide suggests the waterfront for its oyster culture and views across the bay.
  - The harbour area combines seafood stalls, boats, and coastal scenery.
  - **Page 127.**

- **Route from Cancale to Pointe du Grouin**
  - Continue north along the coast.
  - **Page 127.**

- **Walk — Pointe du Grouin**
  - Coastal walking area with open sea views and rocky headlands.
  - **Distance:** not specified by the guide.
  - **Duration:** not specified by the guide.
  - **Elevation gain:** not specified by the guide.
  - **Page 127.**

- **Route from Pointe du Grouin to Saint-Malo**
  - Continue west along the coast to Saint-Malo.
  - **Pages 127-128.**

- **Saint-Malo old town**
  - Explore the walled historic centre, its streets, squares, and reconstructed historic buildings.
  - **Pages 128-130.**

- **Walk — Saint-Malo ramparts**
  - Walk around the city walls for views of the old town, harbour, beaches, and offshore islands.
  - **Distance:** not specified by the guide.
  - **Duration:** not specified by the guide.
  - **Elevation gain:** not specified by the guide.
  - **Page 129.**

- **Night**
  - Saint-Malo.
```

The page numbers in this fictional France example are illustrative. In a real itinerary, every number must be taken from the supplied guidebook.

---

# 20. Workflow from start to finish

## Step 1 — Parse the outline

Convert the brief input into a sequence of overnight locations and major transfers.

Example:

```text
Day 1: Paris
Day 2: Paris -> Mont Saint-Michel
Day 3: Mont Saint-Michel -> Saint-Malo
Day 4: Saint-Malo -> Amboise
Day 5: Amboise -> Paris
```

## Step 2 — Locate each destination in the guide

For every location:

- find its main section;
- record the printed page range;
- identify surrounding regional pages;
- identify nearby excursions.

## Step 3 — Read all relevant pages

Capture:

- core attractions;
- secondary attractions;
- walks;
- hikes;
- scenic routes;
- cultural activities;
- road-trip suggestions;
- practical access information.

## Step 4 — Build an activity inventory

For each item, record:

```text
Name
Location
Type
Description
Printed page(s)
Distance
Duration
Elevation
Start point
End point
Notes
```

## Step 5 — Research route corridors inside the guide

For each transfer:

```text
Origin -> Destination
```

look for guide-recommended stops between them.

## Step 6 — Assign activities to days

Use:

- destination;
- overnight location;
- geographic proximity;
- route sequence.

Do not change the user's main trip structure.

## Step 7 — Order the day's locations

Arrange stops in travel order.

## Step 8 — Insert route entries

Between every pair of different localities:

```text
Route from X to Y
```

## Step 9 — Expand descriptions

Give each important activity a few lines derived from the guide.

## Step 10 — Add quantitative trail data

Copy exactly what the guide provides.

## Step 11 — Add secondary guide suggestions

Create a subsection if necessary:

```text
Other activities suggested by the guide in the area
```

## Step 12 — Add the overnight location

End each day with:

```text
- **Night**
  - Saint-Malo.
```

## Step 13 — Verify every page reference

Check that:

- it is the printed guide page;
- it actually supports the activity;
- ranges are correct.

## Step 14 — Verify source fidelity

Remove any statement that came only from general knowledge unless outside research was explicitly requested.

## Step 15 — Save as Markdown

Use UTF-8 encoding and a `.md` extension.

---

# 21. Handling ambiguous or incomplete guidebook information

The guide will sometimes be incomplete.

Use explicit wording.

## Missing duration

```text
- **Duration:** not specified by the guide.
```

## Missing distance

```text
- **Distance:** not specified by the guide.
```

## Missing elevation

```text
- **Elevation gain:** not specified by the guide.
```

## Unclear route

```text
- The guide mentions this excursion but does not provide a complete turn-by-turn route.
```

## Activity mentioned only on a map

```text
- The regional map identifies this viewpoint, but the guide does not provide a separate description.
- **Page 188.**
```

This is preferable to filling gaps with assumptions.

---

# 22. Handling contradictions inside the guide

If two guidebook sections give different numbers, preserve the contradiction.

Example:

```text
- The hiking panel gives a distance of 12 km, while the regional description gives 13 km.
- **Pages 134 and 136.**
```

Do not silently choose one unless there is a clear reason such as:

- one is one-way and one is return;
- one is an old edition note;
- one clearly refers to a different start point.

If the discrepancy cannot be resolved from the guide itself, say so.

---

# 23. Practical information: what to include

Include practical details when they directly help execute an activity.

Useful examples:

- entrance price or admission fee;
- access road;
- trailhead;
- shuttle;
- required permit;
- opening days;
- seasonal access;
- last section requiring walking;
- nearest village;
- booking requirement;
- whether an excursion can be done on foot or horseback.

When the guide provides an entrance price, include it directly in the activity entry.

Example:

```text
- **Château de Villandry**
  - Renaissance château particularly known for its formal gardens.
  - **Entrance price:** €14, as stated by the guide.
  - **Page 198.**
```

If the guide does not provide a price, do not estimate or look one up unless the user explicitly requests external research. Write:

```text
- **Entrance price:** not specified by the guide.
```

Avoid filling the itinerary with every restaurant, hotel, and phone number in the guide unless requested.

---

# 24. Naming conventions

Use names as written in the guide.

If the guide provides alternate names, preserve them when useful.

Example:

```text
- **Château de Chambord**
```

rather than inventing or anglicizing a different name.

For routes, use consistent wording:

```text
- **Route from Paris to Giverny**
- **Route from Giverny to Rouen**
- **Route from Rouen to Mont Saint-Michel**
```

For walking activities:

```text
- **Walk — Saint-Malo ramparts**
```

For hikes:

```text
- **Hike — Cap Fréhel coastal loop**
```

---

# 25. Recommended level of detail

A useful activity entry generally contains:

1. activity name;
2. two to four descriptive bullet lines;
3. hike/walk metrics when applicable;
4. printed page reference.

Example:

```text
- **Château de Chenonceau**
  - The château spans the River Cher and combines several phases of Renaissance architecture.
  - The guide highlights the galleries over the river, furnished interiors, and formal gardens.
  - The surrounding estate also includes walking paths and river views.
  - **Pages 192-193.**
```

Avoid reducing entries to one-line labels unless they are secondary options.

---

# 26. Quality-control checklist

Before delivering the Markdown file, verify every item below.

## Structure

- [ ] Every day in the input outline appears in the output.
- [ ] Days remain in chronological order.
- [ ] The user's overnight destinations are preserved.
- [ ] Each day ends with the overnight location where appropriate.

## Routes

- [ ] Every change of locality has a **Route from X to Y** entry.
- [ ] No unnecessary route entries appear between attractions in the same city.
- [ ] Route stops appear in geographic order.

## Guidebook coverage

- [ ] Main destination sections were reviewed.
- [ ] Nearby-excursion sections were reviewed.
- [ ] Road-trip panels were reviewed.
- [ ] Maps were reviewed.
- [ ] Sidebars and suggested-itinerary boxes were reviewed.
- [ ] Relevant activities suggested along transfer routes were considered.

## Activities

- [ ] Major guide-recommended sights are included.
- [ ] Each important activity has a short description.
- [ ] Secondary activities are listed separately when useful.
- [ ] Hikes and walks are clearly labelled.

## Quantitative data

- [ ] Distances are copied accurately.
- [ ] Durations are copied accurately.
- [ ] Elevation gain is copied accurately.
- [ ] Missing values are explicitly marked as not specified.
- [ ] No estimates were invented.

## Citations

- [ ] Every page reference uses the printed guidebook page number.
- [ ] Every page reference actually supports the associated statement.
- [ ] Page ranges are used when an activity spans several pages.

## Tone

- [ ] No unsupported judgments about timing or feasibility.
- [ ] No unrequested redesign of the itinerary.
- [ ] No unsupported general-knowledge additions.
- [ ] No hidden assumptions are presented as facts.

---

# 27. Compact pseudo-algorithm

```text
INPUT:
  guidebook.pdf
  brief_itinerary[]

1. Determine printed-page numbering.

2. For each itinerary day:
     identify overnight destination
     identify origin and destination
     identify broad geographic corridor

3. For each destination:
     find destination section
     find nearby-excursion section
     find maps
     find road-trip boxes
     find walking/hiking panels
     extract activities

4. For each transfer:
     search guidebook for guide-recommended stops along the corridor

5. For each activity:
     store:
       name
       location
       description
       page
       distance?
       duration?
       elevation?
       access?

6. Assign activities to itinerary days.

7. Sort each day's locations geographically.

8. Between consecutive different locations:
     insert "Route from X to Y"

9. Render each day as Markdown bullets.

10. Add "Other activities suggested by the guide" where useful.

11. Validate:
      printed page references
      source fidelity
      missing metrics
      day order
      route transitions

OUTPUT:
  detailed_itinerary.md
```

---

# 28. Final principle

The brief itinerary determines **where the traveller is going**.

The guidebook determines **what can be done there, what can be seen on the way, and what factual details can be attached to each activity**.

The final Markdown file should therefore feel like a detailed, source-grounded expansion of the original outline rather than a newly invented trip.
