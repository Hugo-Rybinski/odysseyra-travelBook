// The `(vNN)` marker an itinerary's file name carries — the whole of its version
// history, and deliberately the only place that history is kept.
//
// An itinerary is edited dozens of times before the trip, and every save route
// the Edit tab offers used to reuse one name: the two that *create* a file
// (**Save as…**, **Download JSON**) both re-suggested `<slug>.json`, so a folder
// filled up with the browser's own `trip (1).json`, `trip (2).json` — names
// whose order says nothing about which is newest, and which the OS renumbers
// again the moment one is deleted. Numbering the file ourselves means a listing
// sorts in the order it was written and the name says which draft it is.
//
// The version lives in the **name**, never in the JSON. A
// `travel_description.version` field would change the document's bytes on every
// save, and the viewer's day cache is keyed by the itinerary's hash
// (`maps/mapCache.ts`), so each save would miss the entire cache and redraw
// every map for a trip whose content hadn't moved.

/** A trailing `(v03)` / `(V3)`, with whatever separator led up to it. Anchored to
 *  the end so a trip genuinely called "Alps (v2) redux" keeps its own name, and
 *  case/separator tolerant so a file renamed by hand still parses. */
const MARKER = /[ _-]*\((?:v)(\d{1,4})\)$/i;

/** A trailing `.json` — the only extension this module writes. */
const EXT = /\.json$/i;

export interface VersionedName {
  /** The name with the marker and the `.json` removed. */
  base: string;
  /** The version the name stated, or null when it carried no marker. */
  version: number | null;
}

/** Split `trip (v03).json` into `{ base: "trip", version: 3 }`. A name with no
 *  marker comes back with `version: null` — the caller decides what follows it,
 *  which is not the same question as "which version is this". */
export function parseVersionedName(filename: string): VersionedName {
  const stem = filename.replace(EXT, "").trim();
  const m = MARKER.exec(stem);
  if (!m) return { base: stem, version: null };
  const version = Number(m[1]);
  // `(v0)` states a version nothing can be counted from. Read it as unversioned:
  // the next file is then `(v01)`, which doesn't collide with it either.
  return { base: stem.slice(0, m.index), version: version || null };
}

/** `trip` + 3 → `trip (v03).json`. Two digits minimum so a directory listing
 *  sorts in version order; wider past 99, where a fixed width would have to
 *  break anyway. The space before the marker is the convention the browser's own
 *  `trip (1).json` set — it reads as a suffix rather than part of the name. */
export function formatVersionedName(base: string, version: number, ext = ".json"): string {
  const stem = base.replace(EXT, "").trim() || "odysseyra";
  const n = Math.max(1, Math.trunc(version));
  return `${stem} (v${String(n).padStart(2, "0")})${ext}`;
}

/** The version a newly created file should take, given the last one written —
 *  or null when nothing carried a marker yet, which starts the count at 1. */
export function nextVersion(version: number | null): number {
  return (version ?? 0) + 1;
}
