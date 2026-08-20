# Skill: build a Google My Maps KML from a guidebook PDF

**Input:** a guidebook PDF (often a scan — do **not** assume the text is
selectable) covering the region or trip you care about. Optionally, a list of
nearby-city road distances/driving times to attach to city placemarks.

**Output:** a single importable `.kml` file
(`guidebook_places_grouped_colored.kml`) — one placemark per relevant place,
grouped into `<Folder>`s that match the guidebook's major geographic sections,
color-coded by category, each carrying its printed page reference(s), a
guidebook-based description, recommended on-site time, and (for hikes)
duration/distance/elevation. It imports straight into Google My Maps, Google
Earth, or any other KML-compatible tool. The map you build this way is exactly
the kind of custom Google Map you can later export as KML/KMZ and feed to the
**build the full itinerary JSON** skill.

**This document is self-contained.** It defines the data model, extraction
method, quality checks, KML structure, style system, and the two scripts needed
to build the file — you need no other file, no source code, and no tool beyond
Python's standard library.

---

## 1. What the final map should contain

The final map should contain one placemark per relevant place mentioned in the guidebook.

Each placemark should include:

- The place name.
- Its category.
- Its coordinates.
- The printed page number(s) where it is mentioned.
- A description written from the guidebook content.
- Recommended time on site if the guidebook provides it.
- For hikes: duration, distance, and elevation gain if available.
- For cities: approximate road distances and driving times to nearby cities, if you choose to add them.
- A color-coded icon based on the category.
- A folder matching the guidebook's major geographic section.

A good output filename is:

```text
guidebook_places_grouped_colored.kml
```

---

## 2. Recommended categories and colors

Use a small controlled category list. This prevents messy imports and inconsistent colors.

| Category | Meaning | Color | Typical examples |
|---|---|---|---|
| `city` | Towns, villages, bases, transport hubs | Purple | Capital city, regional town, travel base |
| `museum` | Museums, galleries, house-museums | Orange | History museum, art museum |
| `historical` | Monuments, ruins, religious buildings, archaeological sites | Yellow | Minaret, fortress, cathedral, mosque, memorial |
| `nature` | Natural viewpoints, lakes, canyons, waterfalls, scenic valleys | Dark green | Lake, canyon, viewpoint, national park |
| `hike` | Day hikes and short walks | Light green | Waterfall trail, lake hike, city walking route |

For the specific filtering rule used here:

- Include day hikes and short walks.
- Include natural viewpoints and scenic sites even if no formal hike is described.

---

## 3. Prepare the PDF

Guidebook PDFs are often scans or image-heavy files. Do not assume that text extraction will work.

### 3.1 Identify printed page numbers

Printed page numbers are the numbers visible at the bottom or top of the guidebook page. They are often different from the PDF page count.

Create a page mapping table:

| PDF page index | Printed page number | Section |
|---:|---:|---|
| 1 | 20 | Paris and its surroundings |
| 2 | 21 | Paris and its surroundings |
| ... | ... | ... |

This mapping is important because the KML descriptions should cite printed page numbers, not internal PDF page numbers.

### 3.2 Render pages if the PDF has no selectable text

If the PDF is scanned, render each page to an image and read the visible text from the page images.

Recommended manual process:

1. Open the PDF.
2. Go section by section.
3. Zoom enough to read place names, headings, hike boxes, tables, and captions.
4. Record only the places that match the inclusion rules.
5. Record the printed page number from the guidebook page itself.

Avoid relying only on automatic OCR. OCR is useful for discovery, but it can miss place names, accents, table values, hike stats, and map labels.

---

## 4. Define major map folders

Create one folder per major guidebook section. Folder names should match the guidebook's geographic structure.

Example structure:

```text
Paris and its surroundings
Loire Valley
Brittany Coast
Normandy
French Alps
Provence
Dordogne
Occitanie and the Pyrenees
```

In the KML, each section becomes a `<Folder>` containing the relevant `<Placemark>` elements.

---

## 5. Build the source inventory

Before generating KML, create a clean inventory table. This is the single source of truth.

A simple CSV format works well:

```csv
section,name,category,latitude,longitude,pages,time,hike_stats,description
Paris and its surroundings,Paris,city,48.8566,2.3522,20-28,"2 to 3 days","","Paris is the fictional trip's main arrival city and the starting point for the route through France. The guidebook section presents it through major museums, river walks, historic neighborhoods, and transport connections. The city is useful for orienting the traveler before day trips to Versailles, Chartres, or the Loire Valley. Most central sights cluster around the Seine, the Louvre, Île de la Cité, and the Latin Quarter. It is also a practical base for train connections and short cultural excursions."
Paris and its surroundings,Palace of Versailles,historical,48.8049,2.1204,29-31,"Half day to full day","","The Palace of Versailles is described as a major royal site near Paris, combining palace rooms, formal gardens, fountains, and estate buildings. The guidebook presents it as one of the most important historical excursions from the capital. Visitors can focus on the main palace, add the gardens, or extend the visit toward the Trianon estate. The site fits naturally after the Paris section because it explains the political and artistic world of the French monarchy. Crowds and walking distances mean that the visit should not be treated as a quick stop."
French Alps,Lac Blanc trail,hike,45.9706,6.8870,112-113,"About 4 hr return","about 6 km; about 500 m ascent","The Lac Blanc trail is one of the fictional guidebook's highlighted day hikes in the Chamonix area. The route climbs toward a high mountain lake with views of the Mont Blanc massif. It is included as a day hike because the guidebook gives a clear duration and does not require an overnight stage. The walk is more demanding than an urban stroll, with exposed alpine terrain and fast-changing weather. The placemark should represent the lake or main viewpoint, while the description keeps the practical hiking data separate."
```

### Required columns

Use these columns consistently:

| Column | Required? | Notes |
|---|---:|---|
| `section` | Yes | Must match one of your folder names. |
| `name` | Yes | The visible name of the placemark. |
| `category` | Yes | One of `city`, `museum`, `historical`, `nature`, `hike`. |
| `latitude` | Yes | Decimal latitude. |
| `longitude` | Yes | Decimal longitude. |
| `pages` | Yes | Printed page number(s), such as `20-28` or `112, 113`. |
| `time` | No | Recommended time if available. |
| `hike_stats` | No | Duration, distance, elevation gain. Mainly for hikes. |
| `description` | Yes | 5-6 sentences if enough information is available. |

---

## 6. Extract places from the guidebook

Work section by section.

For each section:

1. Read the section title and page range.
2. List all named places.
3. Classify each place.
4. Decide whether to include it.
5. Record the printed page number(s).
6. Record time recommendations if given.
7. Record hike distance, duration, and elevation gain if given.
8. Write a description based only on the guidebook content.
9. Add coordinates.
10. Mark uncertainties for later review.

### Inclusion rules

Include:

- Cities, villages, and travel bases.
- Museums and galleries.
- Monuments, historic buildings, religious buildings, ruins, archaeological sites, memorials.
- Natural sites: lakes, canyons, valleys, waterfalls, viewpoints, national parks.
- Day hikes and short walks.

Exclude:

- Winter-sport-only entries.
- Ski resorts if they are only described for winter sports.
- Multi-day treks as activities.
- Generic restaurants, hotels, transport offices, and travel agencies unless the goal of the map is practical logistics.
- Duplicate mentions of the same place unless they refer to distinct sites.

### Handling multi-day treks

If a famous lake, pass, or valley is mentioned only as part of a multi-day trek, you have two options:

1. Exclude it entirely.
2. Include the place as a natural landmark, but write clearly that the guidebook's trek route is multi-day and is not included as a recommended hike.

Example wording:

```text
This lake is a major natural landmark in the region. The guidebook mainly describes it as part of a multi-day trek, so the full route is excluded from this map under the filtering rules. The placemark is kept only to show the location of the landmark and its regional context.
```

---

## 7. Write good placemark descriptions

Descriptions should be useful inside Google My Maps, not just copied guidebook text.

Recommended structure:

1. Identify what the place is.
2. Explain why the guidebook mentions it.
3. Give cultural, historical, or natural context.
4. Mention how it fits into a route or section.
5. Add practical cautions if the guidebook implies them.
6. Include time or hike stats separately in structured fields.

Example description:

```text
Chamonix is the main mountain base in the fictional French Alps section. The guidebook presents it as a mix of alpine scenery, cable-car viewpoints, mountaineering history, museums, food, and access to day hikes. It is the practical starting point for Aiguille du Midi, Mer de Glace, Lac Blanc, and several balcony trails facing the Mont Blanc massif. The town itself is worth visiting for its pedestrian center, mountain heritage, viewpoints, and transport links into the valley. It is also a good place to arrange lifts, guides, and mountain logistics before heading into the surrounding trails.
```

Avoid:

- Long copied passages.
- Marketing language.
- Unsupported claims.
- Vague descriptions like "beautiful place" without context.
- Mixing multiple separate places into one placemark.

---

## 8. Coordinates

Coordinates are required for KML.

Use decimal degrees:

```text
latitude: 48.8566
longitude: 2.3522
```

KML stores coordinates in this order:

```text
longitude,latitude,altitude
```

Example:

```xml
<Point>
  <coordinates>2.3522,48.8566,0</coordinates>
</Point>
```

### Coordinate quality levels

Keep track of coordinate confidence:

| Confidence | Meaning |
|---|---|
| High | The exact site is clearly identifiable. |
| Medium | The place is a village, valley, or larger area and the coordinate is a representative center. |
| Low | The location is approximate and should be checked later. |

If you do not want to add another CSV column, write uncertainty into the description:

```text
Coordinates are approximate and refer to the central part of the valley rather than a specific trailhead.
```

---

## 9. Add driving distances for cities

For city placemarks, add a structured block listing nearby cities, road distance, and approximate driving time.

Example text inside the KML description:

```html
<br/><br/>
<b>Approximate road distances to nearby cities:</b><br/>
<i>Indicative driving estimates; they may vary with road condition, weather, roadworks, mountain-pass closures, and stops.</i>
<ul>
  <li><b>Versailles</b>: ~25 km - ~40 min to 1 hr</li>
  <li><b>Chartres</b>: ~90 km - ~1 hr 15 min to 1 hr 30 min</li>
  <li><b>Orléans</b>: ~130 km - ~1 hr 45 min to 2 hr 15 min</li>
</ul>
```

Keep these estimates conservative. Mountain roads, small rural roads, weather, construction, and seasonal closures can make actual travel much slower than the number of kilometers suggests.

For a fully self-contained workflow, create a second CSV file for city links:

```csv
city,nearby_city,road_km,driving_time
Paris,Versailles,~25 km,~40 min to 1 hr
Paris,Chartres,~90 km,~1 hr 15 min to 1 hr 30 min
Chamonix,Annecy,~105 km,~1 hr 15 min to 1 hr 45 min
Chamonix,Grenoble,~150 km,~2 hr to 2 hr 30 min
```

---

## 10. KML style system

Google My Maps can ignore some generic KML color definitions. A reliable approach is to use Google-style `StyleMap` and `Style` definitions with icon URLs.

Use this category-to-style mapping:

| Category | Style URL |
|---|---|
| `hike` | `#icon-1596-7CB342-nodesc` |
| `nature` | `#icon-1720-0F9D58-nodesc` |
| `historical` | `#icon-1706-FBC02D-nodesc` |
| `museum` | `#icon-1834-F57C00-nodesc` |
| `city` | `#icon-1899-673AB7-nodesc` |

Include these style definitions near the top of the KML document:

```xml
<Style id="icon-1596-7CB342-nodesc-normal">
  <IconStyle>
    <color>ff42b37c</color>
    <scale>1</scale>
    <Icon>
      <href>https://www.gstatic.com/mapspro/images/stock/503-wht-blank_maps.png</href>
    </Icon>
  </IconStyle>
  <LabelStyle><scale>0</scale></LabelStyle>
</Style>
<Style id="icon-1596-7CB342-nodesc-highlight">
  <IconStyle>
    <color>ff42b37c</color>
    <scale>1</scale>
    <Icon>
      <href>https://www.gstatic.com/mapspro/images/stock/503-wht-blank_maps.png</href>
    </Icon>
  </IconStyle>
  <LabelStyle><scale>1</scale></LabelStyle>
</Style>
<StyleMap id="icon-1596-7CB342-nodesc">
  <Pair><key>normal</key><styleUrl>#icon-1596-7CB342-nodesc-normal</styleUrl></Pair>
  <Pair><key>highlight</key><styleUrl>#icon-1596-7CB342-nodesc-highlight</styleUrl></Pair>
</StyleMap>

<Style id="icon-1720-0F9D58-nodesc-normal">
  <IconStyle>
    <color>ff589d0f</color>
    <scale>1</scale>
    <Icon>
      <href>https://www.gstatic.com/mapspro/images/stock/503-wht-blank_maps.png</href>
    </Icon>
  </IconStyle>
  <LabelStyle><scale>0</scale></LabelStyle>
</Style>
<Style id="icon-1720-0F9D58-nodesc-highlight">
  <IconStyle>
    <color>ff589d0f</color>
    <scale>1</scale>
    <Icon>
      <href>https://www.gstatic.com/mapspro/images/stock/503-wht-blank_maps.png</href>
    </Icon>
  </IconStyle>
  <LabelStyle><scale>1</scale></LabelStyle>
</Style>
<StyleMap id="icon-1720-0F9D58-nodesc">
  <Pair><key>normal</key><styleUrl>#icon-1720-0F9D58-nodesc-normal</styleUrl></Pair>
  <Pair><key>highlight</key><styleUrl>#icon-1720-0F9D58-nodesc-highlight</styleUrl></Pair>
</StyleMap>

<Style id="icon-1706-FBC02D-nodesc-normal">
  <IconStyle>
    <color>ff2dc0fb</color>
    <scale>1</scale>
    <Icon>
      <href>https://www.gstatic.com/mapspro/images/stock/503-wht-blank_maps.png</href>
    </Icon>
  </IconStyle>
  <LabelStyle><scale>0</scale></LabelStyle>
</Style>
<Style id="icon-1706-FBC02D-nodesc-highlight">
  <IconStyle>
    <color>ff2dc0fb</color>
    <scale>1</scale>
    <Icon>
      <href>https://www.gstatic.com/mapspro/images/stock/503-wht-blank_maps.png</href>
    </Icon>
  </IconStyle>
  <LabelStyle><scale>1</scale></LabelStyle>
</Style>
<StyleMap id="icon-1706-FBC02D-nodesc">
  <Pair><key>normal</key><styleUrl>#icon-1706-FBC02D-nodesc-normal</styleUrl></Pair>
  <Pair><key>highlight</key><styleUrl>#icon-1706-FBC02D-nodesc-highlight</styleUrl></Pair>
</StyleMap>

<Style id="icon-1834-F57C00-nodesc-normal">
  <IconStyle>
    <color>ff007cf5</color>
    <scale>1</scale>
    <Icon>
      <href>https://www.gstatic.com/mapspro/images/stock/503-wht-blank_maps.png</href>
    </Icon>
  </IconStyle>
  <LabelStyle><scale>0</scale></LabelStyle>
</Style>
<Style id="icon-1834-F57C00-nodesc-highlight">
  <IconStyle>
    <color>ff007cf5</color>
    <scale>1</scale>
    <Icon>
      <href>https://www.gstatic.com/mapspro/images/stock/503-wht-blank_maps.png</href>
    </Icon>
  </IconStyle>
  <LabelStyle><scale>1</scale></LabelStyle>
</Style>
<StyleMap id="icon-1834-F57C00-nodesc">
  <Pair><key>normal</key><styleUrl>#icon-1834-F57C00-nodesc-normal</styleUrl></Pair>
  <Pair><key>highlight</key><styleUrl>#icon-1834-F57C00-nodesc-highlight</styleUrl></Pair>
</StyleMap>

<Style id="icon-1899-673AB7-nodesc-normal">
  <IconStyle>
    <color>ffb73a67</color>
    <scale>1</scale>
    <Icon>
      <href>https://www.gstatic.com/mapspro/images/stock/503-wht-blank_maps.png</href>
    </Icon>
  </IconStyle>
  <LabelStyle><scale>0</scale></LabelStyle>
</Style>
<Style id="icon-1899-673AB7-nodesc-highlight">
  <IconStyle>
    <color>ffb73a67</color>
    <scale>1</scale>
    <Icon>
      <href>https://www.gstatic.com/mapspro/images/stock/503-wht-blank_maps.png</href>
    </Icon>
  </IconStyle>
  <LabelStyle><scale>1</scale></LabelStyle>
</Style>
<StyleMap id="icon-1899-673AB7-nodesc">
  <Pair><key>normal</key><styleUrl>#icon-1899-673AB7-nodesc-normal</styleUrl></Pair>
  <Pair><key>highlight</key><styleUrl>#icon-1899-673AB7-nodesc-highlight</styleUrl></Pair>
</StyleMap>
```

Note on KML colors: KML uses `aabbggrr`, not normal `rrggbb`. That means the byte order is alpha, blue, green, red.

---

## 11. Minimal KML structure

A grouped KML file should look like this:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
  <Document>
    <name>Guidebook places</name>

    <!-- Style definitions go here -->

    <Folder>
      <name>Paris and its surroundings</name>

      <Placemark>
        <name>Paris</name>
        <styleUrl>#icon-1899-673AB7-nodesc</styleUrl>
        <description><![CDATA[
          <b>Category:</b> City<br/>
          <b>Guidebook pages:</b> 20-28<br/>
          <b>Recommended time:</b> 2 to 3 days<br/>
          <br/>
          Paris is the fictional trip's main arrival city and the starting point for the route through France.
        ]]></description>
        <Point>
          <coordinates>2.3522,48.8566,0</coordinates>
        </Point>
      </Placemark>

    </Folder>
  </Document>
</kml>
```

---

## 12. Script to generate the KML from CSV

Save this as:

```text
make_kml.py
```

It uses only Python standard library modules.

```python
import csv
from pathlib import Path
from xml.sax.saxutils import escape
from collections import defaultdict

INPUT_CSV = Path("places.csv")
OUTPUT_KML = Path("guidebook_places_grouped_colored.kml")

CATEGORY_LABELS = {
    "hike": "Hike / short walk",
    "nature": "Natural viewpoint or landscape",
    "historical": "Historical or religious site",
    "museum": "Museum",
    "city": "City / village / base",
}

CATEGORY_STYLES = {
    "hike": "#icon-1596-7CB342-nodesc",
    "nature": "#icon-1720-0F9D58-nodesc",
    "historical": "#icon-1706-FBC02D-nodesc",
    "museum": "#icon-1834-F57C00-nodesc",
    "city": "#icon-1899-673AB7-nodesc",
}

STYLE_BLOCK = r'''
<Style id="icon-1596-7CB342-nodesc-normal"><IconStyle><color>ff42b37c</color><scale>1</scale><Icon><href>https://www.gstatic.com/mapspro/images/stock/503-wht-blank_maps.png</href></Icon></IconStyle><LabelStyle><scale>0</scale></LabelStyle></Style>
<Style id="icon-1596-7CB342-nodesc-highlight"><IconStyle><color>ff42b37c</color><scale>1</scale><Icon><href>https://www.gstatic.com/mapspro/images/stock/503-wht-blank_maps.png</href></Icon></IconStyle><LabelStyle><scale>1</scale></LabelStyle></Style>
<StyleMap id="icon-1596-7CB342-nodesc"><Pair><key>normal</key><styleUrl>#icon-1596-7CB342-nodesc-normal</styleUrl></Pair><Pair><key>highlight</key><styleUrl>#icon-1596-7CB342-nodesc-highlight</styleUrl></Pair></StyleMap>

<Style id="icon-1720-0F9D58-nodesc-normal"><IconStyle><color>ff589d0f</color><scale>1</scale><Icon><href>https://www.gstatic.com/mapspro/images/stock/503-wht-blank_maps.png</href></Icon></IconStyle><LabelStyle><scale>0</scale></LabelStyle></Style>
<Style id="icon-1720-0F9D58-nodesc-highlight"><IconStyle><color>ff589d0f</color><scale>1</scale><Icon><href>https://www.gstatic.com/mapspro/images/stock/503-wht-blank_maps.png</href></Icon></IconStyle><LabelStyle><scale>1</scale></LabelStyle></Style>
<StyleMap id="icon-1720-0F9D58-nodesc"><Pair><key>normal</key><styleUrl>#icon-1720-0F9D58-nodesc-normal</styleUrl></Pair><Pair><key>highlight</key><styleUrl>#icon-1720-0F9D58-nodesc-highlight</styleUrl></Pair></StyleMap>

<Style id="icon-1706-FBC02D-nodesc-normal"><IconStyle><color>ff2dc0fb</color><scale>1</scale><Icon><href>https://www.gstatic.com/mapspro/images/stock/503-wht-blank_maps.png</href></Icon></IconStyle><LabelStyle><scale>0</scale></LabelStyle></Style>
<Style id="icon-1706-FBC02D-nodesc-highlight"><IconStyle><color>ff2dc0fb</color><scale>1</scale><Icon><href>https://www.gstatic.com/mapspro/images/stock/503-wht-blank_maps.png</href></Icon></IconStyle><LabelStyle><scale>1</scale></LabelStyle></Style>
<StyleMap id="icon-1706-FBC02D-nodesc"><Pair><key>normal</key><styleUrl>#icon-1706-FBC02D-nodesc-normal</styleUrl></Pair><Pair><key>highlight</key><styleUrl>#icon-1706-FBC02D-nodesc-highlight</styleUrl></Pair></StyleMap>

<Style id="icon-1834-F57C00-nodesc-normal"><IconStyle><color>ff007cf5</color><scale>1</scale><Icon><href>https://www.gstatic.com/mapspro/images/stock/503-wht-blank_maps.png</href></Icon></IconStyle><LabelStyle><scale>0</scale></LabelStyle></Style>
<Style id="icon-1834-F57C00-nodesc-highlight"><IconStyle><color>ff007cf5</color><scale>1</scale><Icon><href>https://www.gstatic.com/mapspro/images/stock/503-wht-blank_maps.png</href></Icon></IconStyle><LabelStyle><scale>1</scale></LabelStyle></Style>
<StyleMap id="icon-1834-F57C00-nodesc"><Pair><key>normal</key><styleUrl>#icon-1834-F57C00-nodesc-normal</styleUrl></Pair><Pair><key>highlight</key><styleUrl>#icon-1834-F57C00-nodesc-highlight</styleUrl></Pair></StyleMap>

<Style id="icon-1899-673AB7-nodesc-normal"><IconStyle><color>ffb73a67</color><scale>1</scale><Icon><href>https://www.gstatic.com/mapspro/images/stock/503-wht-blank_maps.png</href></Icon></IconStyle><LabelStyle><scale>0</scale></LabelStyle></Style>
<Style id="icon-1899-673AB7-nodesc-highlight"><IconStyle><color>ffb73a67</color><scale>1</scale><Icon><href>https://www.gstatic.com/mapspro/images/stock/503-wht-blank_maps.png</href></Icon></IconStyle><LabelStyle><scale>1</scale></LabelStyle></Style>
<StyleMap id="icon-1899-673AB7-nodesc"><Pair><key>normal</key><styleUrl>#icon-1899-673AB7-nodesc-normal</styleUrl></Pair><Pair><key>highlight</key><styleUrl>#icon-1899-673AB7-nodesc-highlight</styleUrl></Pair></StyleMap>
'''


def required(row, field):
    value = (row.get(field) or "").strip()
    if not value:
        raise ValueError(f"Missing required field '{field}' for row: {row}")
    return value


def build_description(row):
    category = required(row, "category")
    pages = required(row, "pages")
    description = required(row, "description")
    time = (row.get("time") or "").strip()
    hike_stats = (row.get("hike_stats") or "").strip()

    html = []
    html.append(f"<b>Category:</b> {escape(CATEGORY_LABELS.get(category, category))}<br/>")
    html.append(f"<b>Guidebook pages:</b> {escape(pages)}<br/>")
    if time:
        html.append(f"<b>Recommended / indicated time:</b> {escape(time)}<br/>")
    if hike_stats:
        html.append(f"<b>Hike data:</b> {escape(hike_stats)}<br/>")
    html.append("<br/>")
    html.append(escape(description))
    return "".join(html)


def load_places(path):
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        places = list(reader)
    for row in places:
        required(row, "section")
        required(row, "name")
        category = required(row, "category")
        if category not in CATEGORY_STYLES:
            raise ValueError(f"Unknown category '{category}' for {row.get('name')}")
        float(required(row, "latitude"))
        float(required(row, "longitude"))
        required(row, "pages")
        required(row, "description")
    return places


def make_kml(places):
    by_section = defaultdict(list)
    section_order = []
    for row in places:
        section = row["section"].strip()
        if section not in by_section:
            section_order.append(section)
        by_section[section].append(row)

    lines = []
    lines.append('<?xml version="1.0" encoding="UTF-8"?>')
    lines.append('<kml xmlns="http://www.opengis.net/kml/2.2">')
    lines.append('<Document>')
    lines.append('<name>Guidebook places</name>')
    lines.append(STYLE_BLOCK)

    for section in section_order:
        lines.append('<Folder>')
        lines.append(f'<name>{escape(section)}</name>')

        for row in by_section[section]:
            name = required(row, "name")
            category = required(row, "category")
            lat = required(row, "latitude")
            lon = required(row, "longitude")
            style_url = CATEGORY_STYLES[category]
            desc = build_description(row)

            lines.append('<Placemark>')
            lines.append(f'<name>{escape(name)}</name>')
            lines.append(f'<styleUrl>{style_url}</styleUrl>')
            lines.append(f'<description><![CDATA[{desc}]]></description>')
            lines.append(f'<Point><coordinates>{lon},{lat},0</coordinates></Point>')
            lines.append('</Placemark>')

        lines.append('</Folder>')

    lines.append('</Document>')
    lines.append('</kml>')
    return "\n".join(lines)


if __name__ == "__main__":
    places = load_places(INPUT_CSV)
    OUTPUT_KML.write_text(make_kml(places), encoding="utf-8")
    print(f"Wrote {OUTPUT_KML} with {len(places)} placemarks.")
```

Run it with:

```bash
python3 make_kml.py
```

---

## 13. Optional script to add city driving-distance blocks

If you keep driving distances in a separate CSV, use this script after generating the main KML.

Save as:

```text
add_city_distances.py
```

Expected `city_links.csv`:

```csv
city,nearby_city,road_km,driving_time
Paris,Versailles,~25 km,~40 min to 1 hr
Paris,Chartres,~90 km,~1 hr 15 min to 1 hr 30 min
Chamonix,Annecy,~105 km,~1 hr 15 min to 1 hr 45 min
Chamonix,Grenoble,~150 km,~2 hr to 2 hr 30 min
```

Script:

```python
import csv
from pathlib import Path
import xml.etree.ElementTree as ET

INPUT_KML = Path("guidebook_places_grouped_colored.kml")
CITY_LINKS = Path("city_links.csv")
OUTPUT_KML = Path("guidebook_places_grouped_colored_distances.kml")

NS = {"k": "http://www.opengis.net/kml/2.2"}
ET.register_namespace("", "http://www.opengis.net/kml/2.2")


def load_links(path):
    links = {}
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            city = row["city"].strip()
            links.setdefault(city, []).append(row)
    return links


def build_block(rows):
    items = []
    for row in rows:
        nearby = row["nearby_city"].strip()
        km = row["road_km"].strip()
        time = row["driving_time"].strip()
        items.append(f"<li><b>{nearby}</b>: {km} - {time}</li>")

    return (
        "<br/><br/>"
        "<b>Approximate road distances to nearby cities:</b><br/>"
        "<i>Indicative driving estimates; they may vary with road condition, "
        "weather, roadworks, mountain-pass closures, and stops.</i>"
        "<ul>" + "".join(items) + "</ul>"
    )


def main():
    links = load_links(CITY_LINKS)
    tree = ET.parse(INPUT_KML)
    root = tree.getroot()

    for placemark in root.findall(".//k:Placemark", NS):
        name_el = placemark.find("k:name", NS)
        desc_el = placemark.find("k:description", NS)
        if name_el is None or desc_el is None:
            continue
        city_name = name_el.text or ""
        if city_name not in links:
            continue
        desc_el.text = (desc_el.text or "") + build_block(links[city_name])

    tree.write(OUTPUT_KML, encoding="utf-8", xml_declaration=True)
    print(f"Wrote {OUTPUT_KML}")


if __name__ == "__main__":
    main()
```

---

## 14. Quality checks before importing

Before importing into Google My Maps, check the file carefully.

### 14.1 CSV checks

Check that:

- Every row has a section.
- Every section name is spelled consistently.
- Every category is one of the allowed category names.
- Every placemark has coordinates.
- Latitude and longitude are not reversed.
- Page references are printed page references.
- Hikes longer than one day are excluded or clearly marked as excluded.
- Descriptions are not copied verbatim from the guidebook.
- Duplicates are merged.

### 14.2 KML checks

Open the KML in a text editor and confirm:

- It starts with `<?xml version="1.0" encoding="UTF-8"?>`.
- It has a single `<kml>` root element.
- It has a single `<Document>` element.
- Style definitions appear before folders.
- Each folder contains placemarks.
- Each placemark has a `<name>`, `<styleUrl>`, `<description>`, and `<Point>`.
- Coordinates are in `longitude,latitude,0` order.
- Descriptions are wrapped in `<![CDATA[ ... ]]>`.

### 14.3 Visual checks after import

After importing into Google My Maps:

- Confirm folders match the guidebook sections.
- Confirm city icons are purple.
- Confirm museum icons are orange.
- Confirm historical sites are yellow.
- Confirm natural sites are dark green.
- Confirm hikes are light green.
- Open a few placemarks from each section and check descriptions.
- Verify that the most important points appear in the right country or region.
- Check that no multi-day trek was accidentally included as a recommended day hike.

---

## 15. Importing into Google My Maps

Use this workflow:

1. Open Google My Maps.
2. Create a new map.
3. Click `Import` on a layer.
4. Upload the generated `.kml` file.
5. Wait for the import to finish.
6. Check the layer list. The KML folders should become grouped layers or grouped sections depending on the import behavior.
7. Click several markers and verify that the HTML descriptions render correctly.
8. If colors are wrong, export a small manually styled test map from Google My Maps and copy its style definitions into your generated KML, then map your categories to those style IDs.

---

## 16. Common problems and fixes

### Problem: Icons import but colors are wrong

Cause: Google My Maps may ignore simple KML colors or generic icon styling.

Fix: Use Google-style `StyleMap` definitions and style URLs such as:

```xml
<styleUrl>#icon-1899-673AB7-nodesc</styleUrl>
```

### Problem: Points appear in the wrong place

Cause: Latitude and longitude were reversed.

Fix: CSV should store `latitude,longitude`, but KML must write `longitude,latitude,0`.

### Problem: Descriptions display as raw HTML

Cause: The description was escaped too aggressively or CDATA was not used.

Fix: Wrap formatted descriptions like this:

```xml
<description><![CDATA[
<b>Category:</b> City<br/>
Text here.
]]></description>
```

### Problem: Google My Maps merges or flattens folders

Cause: My Maps may simplify complex KML structures.

Fix: Keep a simple hierarchy: one `<Document>`, several `<Folder>` elements, then placemarks directly inside each folder.

### Problem: The guidebook page numbers do not match PDF pages

Cause: Guidebooks usually include covers, front matter, or extracts before the printed page sequence.

Fix: Build a page mapping table and always cite the printed number visible on the page.

### Problem: A hike has duration but no distance or elevation

Fix: Include what the guidebook provides and explicitly say what is missing:

```text
Hike data: about 3 hr; distance and elevation gain not stated in the guidebook.
```

### Problem: A landmark is part of a multi-day trek

Fix: Either exclude it or include it only as a landmark with a note that the multi-day route itself is excluded.

---

## 17. Recommended final file package

A clean project folder should contain:

```text
guidebook-map-project/
  guidebook.pdf
  page_mapping.csv
  places.csv
  city_links.csv
  make_kml.py
  add_city_distances.py
  guidebook_places_grouped_colored.kml
  guidebook_places_grouped_colored_distances.kml
  qa_notes.md
```

Where:

- `page_mapping.csv` records PDF page numbers vs printed page numbers.
- `places.csv` is the source inventory.
- `city_links.csv` stores city driving estimates.
- `make_kml.py` generates the map.
- `add_city_distances.py` optionally adds nearby-city driving blocks.
- `qa_notes.md` records uncertain coordinates, excluded treks, and places to verify.

---

## 18. Suggested QA checklist

Use this before delivering the final KML.

- [ ] Every included place is mentioned in the guidebook.
- [ ] Every placemark has printed page numbers.
- [ ] Every placemark is in the correct section folder.
- [ ] Winter-sport-only entries are excluded.
- [ ] Multi-day treks are excluded as activities.
- [ ] Day hikes include duration, distance, and elevation gain when available.
- [ ] Missing hike stats are clearly marked as not stated.
- [ ] City placemarks include nearby road distances if that feature is requested.
- [ ] Coordinates are in the correct country and region.
- [ ] KML coordinates use longitude first, latitude second.
- [ ] Colors display correctly after import.
- [ ] Descriptions display as formatted HTML, not raw tags.
- [ ] No duplicate placemarks exist unless they represent distinct sites.
- [ ] File opens without XML errors.
- [ ] File imports successfully into Google My Maps.

---

## 19. End-to-end summary

The reproducible process is:

1. Render or read the guidebook PDF.
2. Map PDF pages to printed page numbers.
3. Define major geographic folders.
4. Extract all relevant places section by section.
5. Filter out winter sports and multi-day treks.
6. Classify each place into a controlled category.
7. Record coordinates, printed pages, time recommendations, and hike stats.
8. Write concise guidebook-based descriptions.
9. Store everything in `places.csv`.
10. Generate a grouped, styled KML with `make_kml.py`.
11. Optionally add city driving-distance blocks with `add_city_distances.py`.
12. Import into Google My Maps.
13. Visually verify folders, colors, coordinates, descriptions, and exclusions.
14. Deliver the final `.kml` file and the source CSV files if future editing is needed.
