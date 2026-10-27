# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

Self-planning travelers building a multi-day trip themselves, often from guidebooks, bookings and an LLM's help. They author or generate one JSON itinerary, print the PDF book, and read the installable PWA viewer on a phone while on the road, sometimes with poor connectivity, in daylight, on trails or in the car.

## Product Purpose

Turn a JSON travel itinerary into a polished, print-ready PDF and an interactive viewer, and validate the JSON with precise, localized, line-numbered diagnostics. Success: the traveler trusts the book enough to leave the house with it, and a malformed file is told exactly where and why it is wrong.

## Positioning

The itinerary is a plain JSON file the user owns. There is no account and no server, and it works offline. It is validated, and rendered by the same engine to a PDF (pure Python, no system dependencies) and to an in-browser viewer. A hosted trip-planning app cannot truthfully offer a file that stays the user's.

## Operating Context

- CLI (`odysseyra-travelBook`) for build, validate, geocode, route, ics, gpx, stitch.
- PWA viewer (web/) running the same Python engine in a Pyodide Web Worker, with an Edit tab, Overview map, interactive MapLibre maps, dark theme, and exports (PDF, .ics, GPX zip).
- The printed PDF is the primary review artifact and is also used in ink-saver mode.
- Used outdoors and on the move: phone screens, trails, live GPS position on hike profiles.
- Maps come from Carto vector tiles, rasterized by us for print.

## Capabilities and Constraints

- Days, transport bookings with legs, accommodations, car rentals, hikes with embedded GPX, maps and coordinates, bank holidays, emergency contacts, sunrise/sunset and moon phase, multi-currency prices.
- Pure Python with the bundled DejaVu font; no Cairo/Pango. Text must render any Unicode.
- Two independent renderers (PDF and viewer) must stay in step for every user-facing field.
- The whole palette derives from a single `cover_color`.
- Python 3.13; the viewer runs a built wheel, so Python changes need a rebuild.

## Brand Commitments

- Name: Odysseyra TravelBook.
- Icon/favicon identity: the navy rose (restored in the recent favicon and PWA icon commits).

## Evidence on Hand

- Example trips: `examples/france.json` (flagship, maps on, also the viewer's Demo), `france_fr.json`, `pyrenees.json`, `broken.json`.
- `file_format.md` documents the schema; `skills/` holds the LLM guides.
- No customer testimonials, usage numbers, or pricing exist; none may be invented.

## Product Principles

1. The file belongs to the user: offline-capable, no lock-in, no account.
2. Tell the truth about the data: validate precisely, and never draw or invent what the file doesn't say.
3. Paper is a first-class output: the printed book is reviewed first, and the viewer must not diverge from it silently.
4. Legible away from a desk: designed for glanceable reading on the road and in print.
5. Fewer, clearer marks: accent means emphasis, so structure uses grey.

## Accessibility & Inclusion

- English and French parity: every user-facing label exists in both languages, in both renderers.
