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
