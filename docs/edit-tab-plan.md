# Edit tab — structured/form editor plan

A plan for adding an **Edit** tab to the Travelbook Viewer PWA (`web/`): an
in-UI, structured/form editor for the itinerary JSON. Companion to
[`pwa-migration-plan.md`](./pwa-migration-plan.md). Scope covers a form-based
editor with live validation, live preview, save/export, schema-scoped editing
helpers, and safety/recovery.

## The one architectural fact that shapes everything

The form edits the **input** JSON — the shape you *write* (`travel_description`,
`defaults`, `days[]`, `transport[]`, `accommodations[]`, …). But
`src/types/resolved.ts` describes the **output** of `resolve()` (inferred
times, resolved meal categories, chained timelines, etc.). They are different
shapes. So:

- The editor's source of truth is a new **draft object** typed to the *input*
  schema — not `Itinerary` from `resolved.ts`.
- Preview and validation stay text-based: `serialize(draft) → resolve()/validate()`.
  We reuse the engine untouched; the form never re-implements inference or
  validation.
- We need a new TS type + a field registry mirroring the README field tables.
  This is the maintenance cost of the form approach and must be centralized so a
  schema change is a one-file edit.

## Data flow

```
draft (input JSON object)  ──serialize──►  text
   ▲          │                              │
 form edits   │                    ┌─────────┴──────────┐
   │          ▼                    ▼                    ▼
 field registry            validate(text,lang)     resolve(text) → Book preview
   (labels/types/enums/    → inline findings        (debounced)
    defaults/help)
```

Everything is debounced off `draft`. The existing text pipeline
(`runtime.ts`'s `validate` / `resolve` / `buildPdf`, all of which take raw
text) is the seam; nothing in Python changes.

## New files

- `src/types/source.ts` — TS types for the **input** schema
  (TravelDescription, Defaults, Day, Activity union of the 6 types, Transport,
  Accommodation, CarRental, Coordinate, SecondaryCurrency).
- `src/edit/schema.ts` — the **field registry**: per field →
  `{ key, label, type, enum?, default, format, help, group }`, driven by the
  README tables. Single source the form renders from and help tooltips read from.
- `src/edit/EditPanel.tsx` — the tab shell (object tree/nav + the active
  object's form).
- `src/edit/forms/` — one component per object (`DayForm`, `ActivityForm` with a
  type-switch, `TransportForm`, `AccommodationForm`, `CarRentalForm`,
  `DefaultsForm`, `TravelDescriptionForm`).
- `src/edit/fields/` — reusable primitives: `TextField`, `NumberField`,
  `DateField`, `TimeField`, `DurationField`, `EnumSelect`, `PaidTriState`,
  `CoordinateField`, `MoneyField`, `ArrayEditor` (add/remove/reorder).
- `src/edit/draftStore.ts` — draft state + IndexedDB autosave/draft persistence
  + dirty tracking (reuse the `travelbook-maps` IDB pattern from
  `src/maps/mapCache.ts`).
- `src/edit/serialize.ts` — `draftToJson` / `jsonToDraft` (prune empty/default
  keys so saved files stay clean).

## App wiring

- `type View = "options" | "viewer" | "findings" | "edit";` — add the tab
  (✏️ Edit) in the header tablist, disabled with a tooltip until a file is open
  (or "New from scratch" is used).
- App gains `draft` + `dirty` state. When a file loads,
  `jsonToDraft(source.text)` seeds the draft. `onExport` and the preview both
  read the **draft** (serialized), not the last-opened `source.text`.
- Guard tab-away / reload when `dirty`.

## Phases (each shippable)

### P1 — Form surface (§1)

- `source.ts` + `schema.ts` field registry.
- Object navigation (list of days / transports / accommodations / car-rentals +
  the two config groups) and the per-object forms with typed field primitives +
  enum pickers.
- No preview yet — just bind to draft.

### P2 — Live validation (§2) ✅ done

Implemented: `serialize.ts` `serializeWithPaths` emits the text + a 1-based
line→dot-path map; App re-validates the draft debounced (400 ms) once the engine
is ready; `edit/findings.ts` builds a `path → Finding[]` index (via
`collectFieldPaths`, which mirrors the form tree) and a rail of the rest;
`FieldRow`/`CoordinateField` read the index from context and render marks inline;
the rail reuses `FindingsPanel` (level filter). Verified end-to-end against
`examples/broken.json`: invalid-value errors anchor to their exact fields;
structural/coherence/missing findings fall to the rail.

- Debounced `validate(serialize(draft), lang)` → live finding count on the
  Edit/Findings tab.
- **Inline field anchoring (Option B).** Each finding renders *on* its field:
  the offending input is flagged (❌/⚠️/ℹ️) with the message inline beneath it.
  The validator returns findings keyed to a JSON **line number**, so we need
  line → field translation:
  - `serialize(draft)` produces the text with a **path map** (byte/line offset →
    key path) generated alongside it, so we don't depend on parsing back the
    validator's line number blindly. `jsonpos.py` already tracks line positions
    on the Python side; expose that path→line map from the validate call (or
    rebuild the inverse in TS from the same serializer).
  - Each form field knows its own key path (from the field registry + array
    index); match finding line → path → field to attach it.
  - Findings that don't resolve to a visible field (e.g. cross-object coherence
    warnings) fall back to a small rail so nothing is silently dropped.
- Hard-block only on unparseable serialization (shouldn't happen from a form, but
  guard anyway).

### P3 — Preview (§3) ✅ done

Implemented: the Edit tab has an **Apply changes** button (disabled unless the
draft is dirty) that serializes the draft, `resolve()`s + `validate()`s it, and
pushes the result into the viewer (`Book`), the Findings tab, and the export
source — the preview refreshes only here, never on keystroke. A dirty dot marks
the ✏️ tab. Maps: a plain Apply carries the previously-rendered day maps over
untouched (a `mapsStale` flag suppresses per-day loaders for days without one),
and a separate **Apply & redraw maps** rebuilds them via `buildDayMaps(force)`.
Round-trip verified: serialize→resolve of `pyrenees.json` validates and builds
identically to the original.

- **Explicit "Apply" button** (decided — not live-on-keystroke). Clicking Apply
  serializes the draft, runs `resolve(serialize(draft))` and feeds the existing
  `Book`; validation (P2) can still run live/debounced, but the rendered preview
  only refreshes on Apply. Apply is disabled while the draft is clean (nothing to
  apply) and shows when the preview is stale relative to the draft.
- **Maps:** Apply refreshes the text preview only; maps are *not* re-fetched
  automatically (editing changes the doc hash → cache miss). A separate "Apply &
  redraw maps" reuses `buildDayMaps(..., force)`.

### P4 — Save / export (§4)

- Save back via the FS Access `handle` (write) when present; **Download JSON**
  fallback via `downloadBytes` / `slugify`.
- Dirty indicator; Save As / rename; Export PDF already uses the draft after App
  wiring.

### P5 — Schema-scoped helpers (§5)

- `ArrayEditor` add/remove/**reorder** (order is meaningful for days/activities).
- Insert scaffolds ("Add day", "Add activity → road/POI/place/hike/meal/buffer",
  transport, accommodation, car rental) — stubs from the registry defaults,
  mirroring `create-skeleton`.
- Enum pickers already from P1; add `CoordinateField` with paste `lat,long` and
  an optional "geocode from address" action (reuse the maps geocode seam, gated
  on network).

### P6 — Safety & recovery (§6)

- Undo/redo (draft history stack).
- Revert to opened file.
- Autosave draft to IndexedDB (survives reload / SW update); offer to restore on
  next open.
- Prettify/normalize on save via `serialize` (prune empties, stable key order).

## Decisions

1. **Preview mode — DECIDED: explicit "Apply" button.** The rendered Book
   preview refreshes only when the user clicks Apply (not live-on-keystroke).
   Validation may still run live; maps refresh only via "Apply & redraw maps."
   See P3.
2. **Findings→field mapping — DECIDED: inline anchoring (Option B).** The
   validator returns findings keyed to a JSON **line number**; a form has
   fields, not lines. Each finding renders *on* its field (flagged input +
   inline message) by translating line → key path → field via a position map
   (`jsonpos.py` already tracks line positions; the serializer emits the inverse
   path map). Findings that don't resolve to a visible field fall back to a small
   rail so nothing is dropped. See P2.
3. **Draft pruning on save — DECIDED: yes.** `serialize` keeps only non-default
   keys so round-tripped files stay diff-clean against hand-written ones.
