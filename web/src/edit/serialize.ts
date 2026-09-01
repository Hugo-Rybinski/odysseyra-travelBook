import type { SrcItinerary } from "../types/source";

// Draft (input JSON object) <-> text. Field-level editing already prunes empty
// keys as they're cleared (FieldRow emits `undefined` → the key is deleted), so
// `draftToJson` is a plain pretty-print for now. P4/P6 will add a dedicated prune
// + stable-key-order pass on save; keeping the seam here means callers don't
// change when that lands.

export function jsonToDraft(text: string): SrcItinerary {
  const data = JSON.parse(text);
  if (data === null || typeof data !== "object" || Array.isArray(data)) {
    throw new Error("Itinerary JSON must be an object at the top level.");
  }
  return data as SrcItinerary;
}

export function draftToJson(draft: SrcItinerary): string {
  return serializeWithPaths(draft).text;
}

// Keys whose value, when equal to the schema default, is identical to omitting
// the key — safe to drop on save regardless of the containing object. Only
// unambiguous ones (same default everywhere); enum defaults like `type` are
// context-dependent and deliberately left in place.
const SAFE_DEFAULTS: Record<string, unknown> = {
  show_on_map: true,
  show_sun_times: true,
  show_moon_phase: true,
  include_hike_maps: true,
  auto_sized_buffer: true,
  off_road: false,
  display_start_on_maps: false,
  display_end_on_maps: false,
  display_intermediate_point_on_maps: true, // the one pin switch that defaults on
  same_start_as_previous_activity: false,
  same_end_as_next_activity: false,
  bank_holiday: false,
  breakfast_included: false,
  additional_drivers: 0,
};

// Recursively drop redundant content: empty strings, null, empty arrays/objects,
// and safe-default values. Returns `undefined` when the whole value collapses.
function pruneValue(value: unknown, key?: string): unknown {
  if (key !== undefined && key in SAFE_DEFAULTS && value === SAFE_DEFAULTS[key]) return undefined;
  if (value === null || value === undefined) return undefined;
  if (typeof value === "string") return value === "" ? undefined : value;
  if (Array.isArray(value)) {
    const arr = value.map((v) => pruneValue(v)).filter((v) => v !== undefined);
    return arr.length ? arr : undefined;
  }
  if (typeof value === "object") {
    const obj = value as Record<string, unknown>;
    const out: Record<string, unknown> = {};
    for (const k of Object.keys(obj)) {
      const pv = pruneValue(obj[k], k);
      if (pv !== undefined) out[k] = pv;
    }
    return Object.keys(out).length ? out : undefined;
  }
  return value; // numbers, non-default booleans
}

// Serialize the draft for writing to a file (P6): prune empties + safe defaults
// so a round-tripped file stays diff-clean, then pretty-print. Kept separate
// from `serializeWithPaths` (used for validation/apply), which must reflect the
// draft exactly as edited so findings anchor to the visible fields.
export function serializeForSave(draft: SrcItinerary): string {
  const pruned = (pruneValue(draft) as SrcItinerary | undefined) ?? {};
  return serializeWithPaths(pruned).text;
}

// A path into the draft (object keys + array indices), formatted as a stable
// dot-joined string used as a map key throughout the Edit tab (e.g.
// "days.0.activities.1.duration").
export type Path = (string | number)[];
export const pathKey = (p: Path): string => p.join(".");

export interface SerializedWithPaths {
  text: string;
  // 1-based line number → the dot-path of the node that starts on that line.
  // The validator (fed exactly this `text`) reports findings by line, so this is
  // how a finding is translated back to the field it belongs to (Option B).
  pathByLine: Map<number, string>;
}

// Pretty-print the draft as 2-space JSON while recording, for every emitted
// line, the path of the node whose token begins that line. We drive both the
// text and the map from this one printer so they can't drift — the validator
// always sees the exact text this produced.
export function serializeWithPaths(root: unknown): SerializedWithPaths {
  const lines: string[] = [];
  const pathByLine = new Map<number, string>();

  const push = (text: string, path: Path) => {
    lines.push(text);
    pathByLine.set(lines.length, pathKey(path)); // lines.length is the 1-based line just pushed
  };

  // `prefix` is the indent (+ optional `"key": `) the opening token sits behind;
  // `indent` is this node's own indentation, used to align its closing bracket.
  const emit = (prefix: string, value: unknown, path: Path, comma: boolean, indent: string) => {
    const tail = comma ? "," : "";

    if (value === null || typeof value !== "object") {
      push(prefix + JSON.stringify(value ?? null) + tail, path);
      return;
    }

    if (Array.isArray(value)) {
      if (value.length === 0) {
        push(prefix + "[]" + tail, path);
        return;
      }
      push(prefix + "[", path);
      const childIndent = indent + "  ";
      value.forEach((el, i) =>
        emit(childIndent, el, [...path, i], i < value.length - 1, childIndent),
      );
      push(indent + "]" + tail, path);
      return;
    }

    const obj = value as Record<string, unknown>;
    const keys = Object.keys(obj);
    if (keys.length === 0) {
      push(prefix + "{}" + tail, path);
      return;
    }
    push(prefix + "{", path);
    const childIndent = indent + "  ";
    keys.forEach((k, i) =>
      emit(
        childIndent + JSON.stringify(k) + ": ",
        obj[k],
        [...path, k],
        i < keys.length - 1,
        childIndent,
      ),
    );
    push(indent + "}" + tail, path);
  };

  emit("", root, [], false, "");
  return { text: lines.join("\n") + "\n", pathByLine };
}
