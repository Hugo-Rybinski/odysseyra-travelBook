---
name: Odysseyra TravelBook (viewer)
description: The travel book's PWA viewer drawn as a pocket field survey sheet, navy ink ruled on white drafting paper.
colors:
  paper: "#ffffff"
  ink: "#12294f"
  ink-2: "#3c5172"
  ink-3: "#5d6f8c"
  hair: "rgb(18 41 79 / 0.18)"
  hair-strong: "rgb(18 41 79 / 0.45)"
  field: "#f4f6f9"
  gold: "#b08d3e"
  gold-ink: "#7d6224"
  gold-wash: "rgb(176 141 62 / 0.12)"
  grid-minor: "rgb(18 41 79 / 0.045)"
  grid-major: "rgb(18 41 79 / 0.08)"
  strip: "#12294f"
  on-strip: "#ffffff"
  danger: "#9b2c22"
  danger-wash: "rgb(155 44 34 / 0.08)"
  dark-paper: "#0f1b30"
  dark-ground: "#0a1424"
  dark-ink: "#e3e9f3"
  dark-ink-2: "#b9c4d6"
  dark-ink-3: "#8f9db5"
  dark-hair: "rgb(227 233 243 / 0.16)"
  dark-hair-strong: "rgb(227 233 243 / 0.4)"
  dark-field: "#16243c"
  dark-gold: "#c9a55a"
  dark-gold-ink: "#dcbd76"
  dark-gold-wash: "rgb(201 165 90 / 0.16)"
  dark-grid-minor: "rgb(227 233 243 / 0.03)"
  dark-grid-major: "rgb(227 233 243 / 0.06)"
  dark-strip: "#22385f"
  dark-on-strip: "#eef2f8"
  dark-danger: "#f0a499"
  dark-danger-wash: "rgb(240 164 153 / 0.1)"
typography:
  display:
    fontFamily: "'Overpass Variable', 'Overpass', system-ui, sans-serif"
    fontSize: "clamp(2rem, 1.5rem + 2vw, 2.75rem)"
    fontWeight: 700
    lineHeight: 1.08
    letterSpacing: "-0.015em"
  headline:
    fontFamily: "'Overpass Variable', 'Overpass', system-ui, sans-serif"
    fontSize: "clamp(1.6rem, 1.3rem + 1.4vw, 2.25rem)"
    fontWeight: 700
    lineHeight: 1.1
    letterSpacing: "-0.015em"
  title:
    fontFamily: "'Overpass Variable', 'Overpass', system-ui, sans-serif"
    fontSize: "17px"
    fontWeight: 650
    lineHeight: 1.3
  body:
    fontFamily: "'Overpass Variable', 'Overpass', system-ui, sans-serif"
    fontSize: "1.0625rem"
    fontWeight: 400
    lineHeight: 1.6
    fontFeature: "'kern', 'liga'"
  body-sm:
    fontFamily: "'Overpass Variable', 'Overpass', system-ui, sans-serif"
    fontSize: "15px"
    fontWeight: 400
    lineHeight: 1.55
  lede:
    fontFamily: "'Overpass Variable', 'Overpass', system-ui, sans-serif"
    fontSize: "1rem"
    fontWeight: 400
    lineHeight: 1.55
  ui:
    fontFamily: "'Overpass Variable', 'Overpass', system-ui, sans-serif"
    fontSize: "14px"
    fontWeight: 600
    lineHeight: 1.5
  time:
    fontFamily: "'Overpass Variable', 'Overpass', system-ui, sans-serif"
    fontSize: "15px"
    fontWeight: 650
    letterSpacing: "0"
    fontFeature: "'tnum'"
  label:
    fontFamily: "'Overpass Variable', 'Overpass', system-ui, sans-serif"
    fontSize: "11px"
    fontWeight: 700
    letterSpacing: "0.12em"
  tag:
    fontFamily: "'Overpass Variable', 'Overpass', system-ui, sans-serif"
    fontSize: "10.5px"
    fontWeight: 700
    lineHeight: 1.2
    letterSpacing: "0.1em"
  data:
    fontFamily: "'Overpass Mono', ui-monospace, Menlo, monospace"
    fontSize: "12px"
    fontWeight: 400
    letterSpacing: "0.02em"
    fontFeature: "'tnum'"
rounded:
  none: "0"
  circle: "999px"
spacing:
  frame-in: "6px"
  frame-in-phone: "0px"
  gutter: "20px"
  gutter-phone: "12px"
  pad: "clamp(14px, 3vw, 24px)"
  block-gap: "20px"
  time-column: "72px"
  time-column-narrow: "66px"
  running-head: "56px"
  running-head-phone: "48px"
  touch: "44px"
components:
  button:
    backgroundColor: "{colors.paper}"
    textColor: "{colors.ink}"
    typography: "{typography.ui}"
    rounded: "{rounded.none}"
    padding: "7px 14px"
    height: "36px"
  button-hover:
    backgroundColor: "{colors.strip}"
    textColor: "{colors.on-strip}"
  button-filled:
    backgroundColor: "{colors.strip}"
    textColor: "{colors.on-strip}"
    typography: "{typography.ui}"
    rounded: "{rounded.none}"
    padding: "7px 14px"
    height: "36px"
  button-touch:
    height: "{spacing.touch}"
  day-strip:
    backgroundColor: "{colors.strip}"
    textColor: "{colors.on-strip}"
    typography: "{typography.title}"
    rounded: "{rounded.none}"
    padding: "12px clamp(14px, 3vw, 24px)"
    height: "56px"
  type-badge:
    backgroundColor: "{colors.strip}"
    textColor: "{colors.on-strip}"
    rounded: "{rounded.none}"
    padding: "3px 5px 2px"
    width: "95% of the time column"
  tag-filled:
    backgroundColor: "{colors.strip}"
    textColor: "{colors.on-strip}"
    typography: "{typography.tag}"
    rounded: "{rounded.none}"
    padding: "2px 7px 1px"
    height: "20px"
  tag-outline:
    backgroundColor: "{colors.paper}"
    textColor: "{colors.ink}"
    typography: "{typography.tag}"
    rounded: "{rounded.none}"
    padding: "2px 7px 1px"
    height: "20px"
  tag-to-pay:
    backgroundColor: "{colors.gold-wash}"
    textColor: "{colors.gold-ink}"
    typography: "{typography.tag}"
    rounded: "{rounded.none}"
    padding: "2px 7px 1px"
  stop-disc:
    backgroundColor: "{colors.strip}"
    textColor: "{colors.on-strip}"
    rounded: "{rounded.circle}"
    size: "22px"
  stay-bar:
    backgroundColor: "{colors.field}"
    textColor: "{colors.ink}"
    rounded: "{rounded.none}"
    padding: "14px clamp(14px, 3vw, 24px) 16px"
  input:
    backgroundColor: "{colors.paper}"
    textColor: "{colors.ink}"
    rounded: "{rounded.none}"
    height: "36px"
  menu-item:
    backgroundColor: "{colors.paper}"
    textColor: "{colors.ink}"
    rounded: "{rounded.none}"
    padding: "10px 16px"
    height: "44px"
  menu-item-active:
    backgroundColor: "{colors.strip}"
    textColor: "{colors.on-strip}"
---

# Design System: Odysseyra TravelBook (viewer)

## Overview

**Creative North Star: "The Pocket Survey Sheet"**

The viewer is the Odysseyra blog's Survey Sheet folded into a pocket. The whole app is one sheet: white drafting paper with light 10px squares and a stronger line every 50px, held in a ruled double frame (2px ink, a gap, 1px ink), and every box laid on it keeps a solid paper fill so the squares only show between boxes. Navy ink draws every rule, word and fill; gold marks only where the traveller is, what has focus and what needs attention. Corners are square because printed sheets are square.

It is built for a phone held in one hand outdoors (390px is the design width; desktop is the expansion up to a 980px sheet). Each day is a numbered sheet strip in solid ink ("DAY 03 / 08"), its timeline ruled into a time column and a body column on hairlines, tonight's stay closing the sheet on a field fill. Density is a map margin's: small tracked capitals that name fields, tabular figures for every time, distance and price, Overpass Mono for bare index numbers and copyable references.

The dark theme is the same drawing printed in vellum ink on deep navy, not a separate design. Maps stay light in both themes.

**Key Characteristics:**
- One sheet: drafting squares inside a ruled double frame (2px + 1px ink, 6px apart). On phones the sheet is the screen: no frame at all (neither rule) and no paper margin; the squares run to every edge, the boxes keep the width they had inside the frame, and the running head spans the screen edge to edge with only its bottom rule.
- Ink in three strengths plus two hairline alphas; gold only for a live position, focus, warnings and the unsaved/offline state.
- Square corners everywhere; the circle belongs to map stop symbols and their in-text twin.
- Cells separated by 1px ink rules and 0.18-alpha hairlines, never by shadows or tinted cards.
- Overpass for words, tabular Overpass for clock times and figures, Overpass Mono for index numbers and refs.
- 24-unit line icons, 1.75 stroke, in currentColor, for every glyph the chrome draws.
- 44px targets on any coarse pointer.

### Divergences from the pinned blog world
The blog (`odysseyra-blog/DESIGN.md`) is the source world; the build departs from it where an app on a phone differs from a long read:
- **Fixed palette.** The viewer is always navy and gold (`SHEET_INK` in `Book.tsx` feeds `paletteVars`, and `.book` re-points every `--accent*` at the ink). The trip's `cover_color` no longer tints the viewer; it still drives the PDF.
- **A dark sheet.** The blog has no dark variant; here every token has a vellum-on-navy twin in one `:root[data-theme="dark"]` block.
- **No progress bar.** The blog's sticky section progress bar is not carried over: the running head is the only sticky row, so a phone keeps its height for the day itself.
- **No grid-snap walk.** The blog's JS that moves every ruled edge onto a grid line is not ported; rules land where layout puts them.
- **Map lines stay ink.** The user declined the map restyle: routes, stop discs, trail ticks and markers take the ink, never gold, and tiles are not filtered (the blog's Tinted Tiles Rule does not apply).
- **Clock times in tabular Overpass, not mono.** Overpass Mono's wide colon set gutter times as "08 : 30"; proportional Overpass with tabular figures aligns and reads faster.
- **44px touch targets** on every control under `(pointer: coarse)`.
- **Shadow on floating chrome.** The popup shadow, which the blog keeps for map popups, also lifts what floats over the sheet here (menu, tooltips, engine activity card, Edit tab's Apply bar).

## Colors

A two-ink print palette: navy in three strengths with hairline alphas, one gold with a text-safe sibling, on white drafting paper; the dark theme reprints it in vellum on navy.

### Primary
- **Survey Navy** (ink): every border, rule, heading, body text and link; also the solid fill of strips (`strip`: day strips, type badges, filled tags, stop discs, active menu item, inverted button hover). In dark the ink becomes **Vellum** (dark-ink) and strips become **Deep Strip Navy** (dark-strip) with **Strip Vellum** text (dark-on-strip).

### Secondary
- **Route Gold** (gold): non-text gold only. The focus ring (2px, 3px offset), the spinner arc, the hike profile's "you are here" dot, the unsaved dot, a warning field's border, the bank-holiday band fill.
- **Gold Ink** (gold-ink): gold that must be read: link hover, a to-pay tag, the offline status, the hike's position readout, warning findings' icons and pills.
- **Gold Wash** (gold-wash): text selection, warning finding rows, to-pay tag fill.

### Tertiary
- **Survey Red** (danger) with **Red Wash** (danger-wash): errors only (error findings and banners, required marks, invalid fields, destructive icon-button hover). Never decoration.

### Neutral
- **Sheet White** (paper): the sheet and the fill of every box, button, input, menu and tag at rest. In dark: **Night Sheet** (dark-paper) on a **Night Ground** (dark-ground) outside the frame.
- **Secondary Ink** (ink-2): lede, meta lines, notes, sun/moon line, secondary values.
- **Margin Ink** (ink-3): field labels, end times, buffer labels, mono line numbers.
- **Hairline** (hair): rules inside a cell (timeline rows, ledger rows, menu items, bookings).
- **Strong Hairline** (hair-strong): link underlines at rest, indented VIA and nested rules, input borders, dashed placeholders.
- **Field Grey** (field): the stay bar, hover fill on rows and menu items, map loading slot.
- **Graph Lines** (grid-minor, grid-major): the 10px and 50px drafting squares on the sheet.

### Named Rules
**The Two-Ink Rule.** Navy draws; gold marks the reader's place. If a gold element is not a live position, a focus, a warning or an unsaved/offline state, it is wrong. Gold never appears on a map line.

**The Gold-Ink Split Rule.** Raw gold (#b08d3e, dark #c9a55a) never carries text. Gold at text size uses gold-ink. The one exception is the bank-holiday band, where ink capitals sit on a solid gold fill.

**The One Ink Rule.** The viewer has one palette. Nothing in the viewer derives colour from the trip file; `cover_color` belongs to the PDF.

## Typography

**Display Font:** Overpass Variable (with Overpass, system-ui)
**Body Font:** Overpass Variable
**Label/Mono Font:** Overpass Mono 400 (with ui-monospace, Menlo)

**Character:** Overpass descends from Highway Gothic, the signage face, so the sheet reads cartographic and technical without turning cold; the mono cut is held back for the numbers a reader indexes or copies.

### Hierarchy
- **Display** (700, clamp(2rem → 2.75rem), 1.08, -0.015em): the trip title in the cartouche; the Options and empty-state titles use the same weight at clamp(1.75rem → 2.5rem).
- **Headline** (700, clamp(1.6rem → 2.25rem), 1.1): Transport and Accommodation section heads, ruled off beneath in ink; Findings and Emergency use 1.5rem.
- **Title** (650, 16.5–17px, 1.25–1.3): day strip title, activity title, booking title.
- **Body** (400, 1.0625rem, 1.6): cover summary and day intro, 68ch max.
- **Body small** (400, 15px, 1.55): activity descriptions; details, notes and meta lines at 14px/1.5.
- **Lede** (400, 1rem, 1.55, ink-2): the cartouche's subtitle, 52ch max.
- **UI** (600, 14px): buttons, menu items (15px, 16px on phones), the sun line (13px).
- **Time** (650, 15px, tabular figures): start times in the timeline's time column; end times 13px ink-3; the facts ledger values at 600/16px; prices 700/18px.
- **Label** (700, 11px, 0.12em, uppercase, ink-3): field names (ledger, table heads, Tonight, Open, Contact, VIA, map captions, Options group heads).
- **Tag** (700, 10.5px, 0.1em): status, payment, leg and off-road tags; type badges at 9px, 0.07em.
- **Data** (Overpass Mono 400, 11–12px, 0.02em, tabular): the strip's "03 / 08", the day-by-day table's day column, guidebook pages, finding line numbers, file names, engine/version/cache readouts, emergency numbers (16px).

### Named Rules
**The Tabular-Time Rule.** Every clock time, distance, duration and price is set in Overpass with tabular figures, never in mono. Mono is for bare index numbers and copyable references.

**The Two-Digit Index Rule.** An index number shows two digits (`idx()`): 03, "03 / 08". Counts stay plain numbers (8 days, 4 stays).

**The Label-Carries-Data Rule.** Tracked capitals name a field or carry data ("DAY 03 / 08", DATES, TONIGHT). A label that names nothing is not set.

## Layout

Mobile-first at 390px. The sheet (`.shell`, max 980px) sits in a ground margin of clamp(6px, 3vw, 40px) on wider screens; at ≤640px the margin and both frame rules go and the drafting squares are drawn on the page itself, edge to edge, with a 20px inner gutter (12px at ≤640px). Inner cells pad with one token, clamp(14px, 3vw, 24px). Blocks on the sheet stack 20px apart.

The sticky chrome is one row inside the frame: the running head (56px, 48px at ≤640px); `--sticky-h` is its height and every day anchor scrolls to 10px below it. The timeline is a two-column grid: a 72px time column (66px at ≤480px) and the body, 14px apart (12px narrow). The day-by-day ledger stacks into labelled rows at ≤640px. Breakpoints in use: 480, 640, 900px, plus `(pointer: coarse)` and `(hover: none)`.

## Elevation & Depth

Flat. Depth is rule weight: 2px ink for the frame, 1px ink around every box and between major cells, 0.18-alpha hairlines inside cells, dashed strong hairlines for placeholders. Only things that float over the sheet cast a shadow.

### Shadow Vocabulary
- **Popup** (`box-shadow: 0 6px 18px rgb(18 41 79 / 0.14)`; dark `0 8px 24px rgb(0 0 0 / 0.45)`): the menu list, tooltips, the engine activity card, the Edit tab's floating Apply bar.
- **Pin lift** (`box-shadow: 0 1px 3px rgb(18 41 79 / 0.35)`): MapLibre DOM markers, to lift them off the tiles.

### Named Rules
**The Ruled-Not-Raised Rule.** Page surfaces never cast shadows; separate them with a rule of the right weight. A shadow means the thing floats.

## Shapes

Square corners (0) on everything: boxes, buttons, inputs, tags, badges, menu, tooltips, map controls (forced square with a 1px ink border). The circle is a map symbol: stop discs on the map and their 22px in-text twins beside an activity title (18px in VIA rows), plus the 8px gold state dot. A disc's label sits on its centre, not on the font's line box: a number or letter is trimmed to its cap height (`text-box: trim-both cap alphabetic`, `.pin-n`) and the stay's ★ is a drawn polygon (`PinLabel` / `fillPinLabel` in `Icon.tsx`, shared by the text and the map markers), its disc kept round with no side padding. Icons are 24-unit line drawings, 1.75 stroke, round caps and joins, in currentColor; the moon is drawn as its lit disc. Chevrons point right and rotate 90° open (200ms).

## Components

### Buttons
Printed-form boxes, inverted under the pointer.
- **Shape:** square, 1px ink border, 36px tall (44px on coarse pointers).
- **Default:** paper fill, ink text, UI type, 7px 14px. An icon sits 8px left of the label.
- **Hover:** fills strip ink with on-strip text, 160ms `cubic-bezier(0.16, 1, 0.3, 1)` on background and colour. Disabled under `(hover: none)` so a tap does not stick inverted.
- **Filled (Options, restore banner):** strip fill at rest, lightened 18% toward on-strip on hover; `subtle` reverts to the default box.
- **Focus:** global 2px gold outline, 3px offset.
- **Empty state:** the four ways in as a 2×2 grid of 48px ruled cells, 9px apart.

### Links
Ink, weight 600, a 1px strong-hairline underline 3px below; hover turns gold-ink with the underline in currentColor. Prose links keep the prose colour and the same underline.

### Chips / Tags
- **Filled:** strip with on-strip text; **outline:** paper with 1px ink; **paid:** field on a strong hairline; **to-pay:** gold-wash, gold-ink, 1px gold. All Tag type, 20px tall, square.
- **Filter chips** (Findings, Edit): 32px, 1px ink; active = strip fill.
- **Forecast tag:** 22px, strong hairline, 12.5px/600 tabular, an icon in ink-2.
- **Guidebook pages:** mono 11px on a strong hairline.

### Cards / Containers
- **Boxes on the sheet** (cover, day, section, findings, option group, edit section): paper fill, 1px ink border, no radius, no shadow.
- **Bookings are ledger rows, not cards:** 16px vertical padding on hairlines; a 36px square type badge in 1px ink; multi-leg bookings indent each leg 14px under a strong hairline after a 1px ink rule.

### Inputs / Fields
- **Style:** paper, 1px strong hairline, square, 36px (44px coarse), 14px.
- **Hover:** border to ink. **Focus:** 2px gold outline, 1px offset, ink border.
- **Error / Warning:** border danger / gold. Segmented control: 1px ink box, ink-ruled cells, active = strip. Toggle: square track in ink, square thumb.

### Navigation
- **Running head:** a ruled row (1px ink above and below): the mark, ODYSSEYRA (800, 14px, 0.16em) and TRAVELBOOK (700, 13px, 0.12em, ink-3), and a square menu cell ruled off on the left (no rule on phones, where the bar is one strip), inverted when open.
- **Menu:** a ruled list, 44px items (48px/16px on phones, full width under the head), hairline separated, an 18px ink-3 line icon per view; active = strip.

### Day Strip (signature)
Solid strip ink, one height (at least 56px) whether the day is open or folded, so toggling it never moves what follows: a chevron, "DAY" in tracked label caps then "03 / 08" in mono (total at 70%), the date at 75%, the title in Title type, the city in label caps at 80%. Hover lightens 12% toward on-strip.

### Timeline
A ruled ledger: 14px rows on hairlines, the time column holding a square type badge (9px strip, centred, one fixed width: 95% of the column, so every label reads as one column) over the tabular start and end times; a detour row swaps the badge for an outlined one, drops to ink-3 and carries a dashed DETOUR tag of the same width. Drives and nested stops indent 12–14px under a strong hairline.

### Stay Bar
Tonight's stay closes the day: field fill under a 1px ink rule, TONIGHT in label caps, the name at 650, sub line in ink-2.

### Notice (bank holiday)
The blog's warning box: a 1px gold border with a 55% gold outline 2px out, a solid gold head band in ink capitals (800, 12px, 0.12em), the advice on paper.

## Do's and Don'ts

### Do:
- **Do** frame the app in the ruled double border (2px ink, 6px gap, 1px ink) over 10px/50px drafting squares; on phones drop both rules and the margin and let the squares fill the screen, keeping the boxes' width.
- **Do** give every box on the sheet a solid paper fill and a 1px ink border, and rule cells inside it with 0.18-alpha hairlines.
- **Do** set clock times, distances and prices in Overpass with tabular figures, and index numbers and refs in Overpass Mono, always two digits for an index.
- **Do** keep gold for a live position, focus and warnings; use gold-ink (#7d6224, dark #dcbd76) for any gold text.
- **Do** draw every chrome glyph as a 24-unit, 1.75-stroke line icon in currentColor.
- **Do** give every control a 44px target under `(pointer: coarse)`.
- **Do** add a dark twin for any new colour in the single `:root[data-theme="dark"]` token block.

### Don't:
- **Don't** round corners on boxes, buttons, inputs, tags or map controls; the circle belongs to stop symbols and the state dot.
- **Don't** put shadows on page surfaces; only floating chrome and map markers carry one.
- **Don't** use gold for decoration, headings, body links or map lines.
- **Don't** tint the viewer from the trip's `cover_color`.
- **Don't** set clock times in mono.
- **Don't** set a tracked-capital label that names no field and carries no data.
