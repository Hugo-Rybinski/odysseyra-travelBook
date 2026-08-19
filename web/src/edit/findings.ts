import { createContext, useContext } from "react";
import type { Finding, FindingLevel } from "../types/resolved";
import type {
  SrcActivity,
  SrcActivityType,
  SrcItinerary,
} from "../types/source";
import {
  ACCOMMODATION_FIELDS,
  ACTIVITY_FIELDS,
  CAR_RENTAL_FIELDS,
  DAY_FIELDS,
  DEFAULTS_FIELDS,
  SCHEDULED_FIELDS,
  SECONDARY_CURRENCY_FIELDS,
  TRANSPORT_FIELDS,
  TRAVEL_DESCRIPTION_FIELDS,
  WAYPOINT_FIELDS,
} from "./schema";

export const FINDING_ICON: Record<FindingLevel, string> = {
  error: "❌",
  warning: "⚠️",
  info: "ℹ️",
};

// A stable identity for a finding (so the same finding anchored to several
// fields can be de-duplicated / recognised as "shared").
export const findingKey = (f: Finding): string => `${f.level}|${f.line}|${f.message}`;

// The finding index: `byPath` maps a field/container dot-path → its findings
// (a finding anchored to N fields appears under all N paths so each highlights);
// `shared` holds the keys of findings anchored to more than one field, so their
// message can be shown once as a group instead of repeated under every field.
export interface FindingIndex {
  byPath: Map<string, Finding[]>;
  shared: Set<string>;
}

export const EMPTY_FINDING_INDEX: FindingIndex = { byPath: new Map(), shared: new Set() };

// Provided by EditPanel (from a validate() pass over the draft), read by each
// FieldRow / FieldList / CoordinateField / ArrayEditor.
export const EditFindingsContext = createContext<FindingIndex>(EMPTY_FINDING_INDEX);

export function useFindingIndex(): FindingIndex {
  return useContext(EditFindingsContext);
}

export function useFieldFindings(path: string): Finding[] {
  return useContext(EditFindingsContext).byPath.get(path) ?? [];
}

// The highest-severity level in a set of findings (for styling the field).
export function worstLevel(findings: Finding[]): FindingLevel | null {
  if (findings.some((f) => f.level === "error")) return "error";
  if (findings.some((f) => f.level === "warning")) return "warning";
  if (findings.some((f) => f.level === "info")) return "info";
  return null;
}

// Count the errors and warnings anchored anywhere under `prefix` (the path
// itself or a descendant) — used to badge a collapsed array item that hides
// fields with findings. Info is ignored (only errors/warnings badge).
export function countLevelsUnder(
  map: Map<string, Finding[]>,
  prefix: string,
): { error: number; warning: number } {
  let error = 0;
  let warning = 0;
  // A finding anchored to several fields appears under multiple paths; dedupe by
  // line+message so it counts once on the tile's pill.
  const seen = new Set<string>();
  for (const [key, list] of map) {
    if (key !== prefix && !key.startsWith(prefix + ".")) continue;
    for (const f of list) {
      const id = `${f.line}|${f.message}`;
      if (seen.has(id)) continue;
      seen.add(id);
      if (f.level === "error") error++;
      else if (f.level === "warning") warning++;
    }
  }
  return { error, warning };
}

// Split findings into those anchored to a rendered field (by exact path) and
// the rest (container-level coherence warnings, findings with no line, or paths
// that don't correspond to a form field) — the "rail" so nothing is dropped.
export function buildFindingIndex(
  findings: Finding[],
  pathByLine: Map<number, string>,
  fieldPaths: Set<string>,
  containerPaths: Set<string>,
): { byPath: Map<string, Finding[]>; rail: Finding[]; shared: Set<string> } {
  const byPath = new Map<string, Finding[]>();
  const rail: Finding[] = [];
  const shared = new Set<string>();

  for (const f of findings) {
    // Info-level notes (mostly "optional field missing → default") are never
    // inlined onto fields/boxes — they'd bury the real issues. They go to the
    // rail (hidden by default there and toggleable), and stay in the Findings tab.
    if (f.level === "info") {
      rail.push(f);
      continue;
    }
    const path = f.line == null ? undefined : pathByLine.get(f.line);
    const targets =
      path === undefined ? [] : resolveAnchor(path, f.message, fieldPaths, containerPaths);
    if (targets.length > 0) {
      for (const t of targets) {
        const list = byPath.get(t);
        if (list) list.push(f);
        else byPath.set(t, [f]);
      }
      // Anchored to several fields → highlight each, but show the message once.
      if (targets.length > 1) shared.add(findingKey(f));
    } else {
      rail.push(f);
    }
  }
  return { byPath, rail, shared };
}

// Map a finding's raw line-path to the field(s) or container it should attach to
// (empty → rail). Order of preference:
//   1. the exact path is a field → that field.
//   2. the message names fields (a "missing: a, b" suffix, else quoted 'field'
//      tokens) that belong to this container → each of them, so e.g. "add a
//      'duration', or a 'start_time' and 'end_time'" flags all three, and
//      "required field 'name' is missing" flags the name field.
//   3. an array-of-scalar element (e.g. `defaults.inference_countries.0`) → the
//      parent array field.
//   4. the path is a rendered container (a day / activity / transport / … box)
//      → the container itself, so box-level findings ("this activity ends after
//      the day's end_time", overlaps, incoherent times) show inside that box.
function resolveAnchor(
  path: string,
  message: string,
  fieldPaths: Set<string>,
  containerPaths: Set<string>,
): string[] {
  if (fieldPaths.has(path)) return [path];

  const named = fieldNamesFrom(message)
    .map((name) => `${path}.${name}`)
    .filter((p) => fieldPaths.has(p));
  if (named.length > 0) return named;

  const parent = path.replace(/\.\d+$/, "");
  if (parent !== path && fieldPaths.has(parent)) return [parent];

  if (containerPaths.has(path)) return [path];

  // Last resort: attach to the nearest ancestor container (e.g. a road's
  // `….waypoints` array line → the road's box) rather than the rail.
  const ancestor = path.replace(/\.[^.]+$/, "");
  if (ancestor !== path && containerPaths.has(ancestor)) return [ancestor];

  return [];
}

// Field names a finding message refers to: the precise `missing: a, b` subset
// when present, otherwise every quoted snake_case token (values like 'Lyon' or
// 'bus' simply won't match a field and get filtered out by the caller).
function fieldNamesFrom(message: string): string[] {
  const missing = /\bmissing:\s*([a-z0-9_,\s]+)/i.exec(message);
  if (missing) {
    return missing[1].split(",").map((s) => s.trim()).filter(Boolean);
  }
  const names: string[] = [];
  for (const m of message.matchAll(/'([a-z_][a-z0-9_]*)'/gi)) names.push(m[1]);
  return names;
}

// The set of rendered container boxes (config groups + every array item, incl.
// nested activities and waypoints), so a finding that names no field can still
// anchor to the box it concerns. Mirrors the form tree like collectFieldPaths.
export function collectContainerPaths(draft: SrcItinerary): Set<string> {
  const out = new Set<string>(["travel_description", "defaults"]);
  const walk = (base: string, act: SrcActivity) => {
    out.add(base);
    if (act.type === "road") {
      out.add(`${base}.waypoints`); // the array itself (e.g. "needs at least one waypoint")
      (act.waypoints ?? []).forEach((_w, i) => out.add(`${base}.waypoints.${i}`));
    }
    const canNest =
      act.type === "point_of_interest" ||
      act.type === "place" ||
      act.type === "road" ||
      act.type === "hike";
    const nested = (act as { activities?: SrcActivity[] }).activities;
    if (canNest && nested) nested.forEach((a, i) => walk(`${base}.activities.${i}`, a));
  };
  (draft.days ?? []).forEach((day, i) => {
    out.add(`days.${i}`);
    (day.activities ?? []).forEach((a, j) => walk(`days.${i}.activities.${j}`, a));
  });
  (draft.transport ?? []).forEach((_t, i) => out.add(`transport.${i}`));
  (draft.accommodations ?? []).forEach((_a, i) => out.add(`accommodations.${i}`));
  (draft.car_rentals ?? []).forEach((_c, i) => out.add(`car_rentals.${i}`));
  return out;
}

// ---------------------------------------------------------------------------
// The set of every field path the forms render, so buildFindingIndex can tell a
// field-anchored finding from a rail one. This deliberately mirrors the form
// tree (EditPanel → forms → FieldList/CoordinateField); keep the two in step.
export function collectFieldPaths(draft: SrcItinerary): Set<string> {
  const out = new Set<string>();
  const add = (p: string) => out.add(p);
  const addCoord = (base: string) => {
    add(base); // the coordinate object itself (validator flags bad coords here)
    add(`${base}.lat`);
    add(`${base}.long`);
    add(`${base}.show_on_map`);
  };
  const addFields = (base: string, keys: readonly { key: string }[]) => {
    for (const f of keys) add(base ? `${base}.${f.key}` : f.key);
  };

  addFields("travel_description", TRAVEL_DESCRIPTION_FIELDS);

  addFields("defaults", DEFAULTS_FIELDS);
  (draft.defaults?.secondary_currencies ?? []).forEach((_c, i) =>
    addFields(`defaults.secondary_currencies.${i}`, SECONDARY_CURRENCY_FIELDS),
  );

  (draft.days ?? []).forEach((day, i) => {
    addFields(`days.${i}`, DAY_FIELDS);
    (day.activities ?? []).forEach((act, j) =>
      walkActivity(`days.${i}.activities.${j}`, act, add, addCoord, addFields),
    );
  });

  (draft.transport ?? []).forEach((_t, i) => {
    addFields(`transport.${i}`, TRANSPORT_FIELDS);
    addCoord(`transport.${i}.start_coordinate`);
    addCoord(`transport.${i}.end_coordinate`);
  });

  (draft.accommodations ?? []).forEach((_a, i) => {
    addFields(`accommodations.${i}`, ACCOMMODATION_FIELDS);
    addCoord(`accommodations.${i}.coordinate`);
  });

  (draft.car_rentals ?? []).forEach((_c, i) => {
    addFields(`car_rentals.${i}`, CAR_RENTAL_FIELDS);
    addCoord(`car_rentals.${i}.pickup_coordinate`);
    addCoord(`car_rentals.${i}.dropoff_coordinate`);
  });

  return out;
}

function walkActivity(
  base: string,
  act: SrcActivity,
  add: (p: string) => void,
  addCoord: (base: string) => void,
  addFields: (base: string, keys: readonly { key: string }[]) => void,
) {
  const type = act.type;
  add(`${base}.type`); // the type <select> can carry an "invalid/disallowed type" finding
  if (type === "buffer") {
    addFields(base, ACTIVITY_FIELDS.buffer);
    return;
  }
  addFields(base, SCHEDULED_FIELDS);
  // A hand-edited draft may carry an unknown type; skip its (absent) field table.
  const typeFields = ACTIVITY_FIELDS[type];
  if (typeFields) addFields(base, typeFields);
  addCoord(`${base}.coordinate`);

  if (type === "road") {
    (act.waypoints ?? []).forEach((_w, i) => {
      addFields(`${base}.waypoints.${i}`, WAYPOINT_FIELDS);
      addCoord(`${base}.waypoints.${i}.coordinate`);
    });
  }

  const nested: readonly SrcActivityType[] =
    type === "point_of_interest" || type === "place"
      ? ["point_of_interest", "hike", "meal"]
      : type === "road" || type === "hike"
        ? ["meal"]
        : [];
  if (nested.length) {
    const acts = (act as { activities?: SrcActivity[] }).activities ?? [];
    acts.forEach((a, i) => walkActivity(`${base}.activities.${i}`, a, add, addCoord, addFields));
  }
}
