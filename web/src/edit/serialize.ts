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
  return JSON.stringify(draft, null, 2) + "\n";
}
