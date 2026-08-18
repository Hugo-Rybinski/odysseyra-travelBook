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

// Findings anchored to fields, keyed by the field's dot-path. Provided by the
// EditPanel (built from a validate() pass over the draft) and read by each
// FieldRow / CoordinateField for its own path. Empty map = no findings / not yet
// validated.
export const EditFindingsContext = createContext<Map<string, Finding[]>>(new Map());

export function useFieldFindings(path: string): Finding[] {
  return useContext(EditFindingsContext).get(path) ?? [];
}

// The highest-severity level in a set of findings (for styling the field).
export function worstLevel(findings: Finding[]): FindingLevel | null {
  if (findings.some((f) => f.level === "error")) return "error";
  if (findings.some((f) => f.level === "warning")) return "warning";
  if (findings.some((f) => f.level === "info")) return "info";
  return null;
}

// Split findings into those anchored to a rendered field (by exact path) and
// the rest (container-level coherence warnings, findings with no line, or paths
// that don't correspond to a form field) — the "rail" so nothing is dropped.
export function buildFindingIndex(
  findings: Finding[],
  pathByLine: Map<number, string>,
  fieldPaths: Set<string>,
): { byPath: Map<string, Finding[]>; rail: Finding[] } {
  const byPath = new Map<string, Finding[]>();
  const rail: Finding[] = [];

  for (const f of findings) {
    const path = f.line == null ? undefined : pathByLine.get(f.line);
    if (path !== undefined && fieldPaths.has(path)) {
      const list = byPath.get(path);
      if (list) list.push(f);
      else byPath.set(path, [f]);
    } else {
      rail.push(f);
    }
  }
  return { byPath, rail };
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
    (day.activities ?? []).forEach((act, j) => walkActivity(`days.${i}.activities.${j}`, act, addCoord, addFields));
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
  addCoord: (base: string) => void,
  addFields: (base: string, keys: readonly { key: string }[]) => void,
) {
  const type = act.type;
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
    acts.forEach((a, i) => walkActivity(`${base}.activities.${i}`, a, addCoord, addFields));
  }
}
