// Persistent cache for the per-day maps (the whole resolved `Day` including the
// base64 map images + pin labels the Python renderer produced), so a killed and
// relaunched app doesn't have to redraw them — it hydrates instantly from here
// and only renders days that are missing or stale.
//
// Keyed by `v<schema>:<hash of the itinerary JSON>:<day index>` and kept for 30
// days, in its own IndexedDB database (so it needn't share the file-handle DB's
// version).
// Everything is best-effort: any failure resolves to a cache miss, never throws.
import type { Day } from "../types/resolved";

const DB_NAME = "odysseyra-maps";
const STORE = "days";
const TTL_MS = 30 * 24 * 60 * 60 * 1000; // 30 days

// BUMP THIS whenever the resolved `Day` gains a field OR changes how one is
// computed. An entry holds the *whole* day — pin labels and all, not just the
// images — and App.tsx swaps it in wholesale on a hit, so an entry written by an
// older build masks the new value. The itinerary's hash can't catch it: the JSON
// is byte-identical, only our code moved (this is exactly how `sun` first went
// missing in the viewer, and then how its old one-reference times would have
// lingered). The version is part of the key, so a mismatch reads as a miss and
// the dead entries are swept up on the next `purgeExpired`.
// v2: `sun` added. v3: sunrise re-referenced to the previous night's stay.
// v4: each end got its own fallback chain (sunset → the day's last located stop,
// sunrise → its first). v5: `sun.display` dropped — the viewer localizes it now.
// v6: `road` activities gained a `description`. v7: road waypoints gained a
// per-leg `off_road`. v8: `show_moon_phase` now defaults on, so `day.moon` is
// populated for docs that never set it. v9: road / point_of_interest / place /
// hike activities gained `guidebook_pages`. v10: a `hike` gained the `track`
// derived from its embedded `gpx` (the trail line + elevation profile). v11:
// `track.gpx` carries the original file, for the "(Get GPX track)" download —
// without the bump a v10-cached day would draw the trail but hide the link.
// v12: transport legs, car pick-up/drop-off events and the night's stay gained
// a `description` (a short note) — a v11-cached day carries none of them.
// v13: a `place` with no duration/end_time now lasts its nested activities'
// total instead of 0, which also shifts every later item on that day's timeline.
// v14: buffers are auto-sized by default (`defaults.auto_sized_buffer`), so a
// day's timeline is spread out to `defaults.end_time` (now 18:00 when unset) —
// every activity moves and the buffers between them change length. v15: a day
// gained `bank_holiday`, which draws the holiday banner — a v14-cached day
// carries the flag nowhere, so the banner would never appear for it. v16: a
// point of interest gained `opening` (its opening days/hours), drawn under the
// address — a v15-cached day carries it nowhere. v17: transport split into a
// booking plus its `legs`, so a day's `transports` are now legs enriched with
// their booking's shared fields (`leg_index`/`leg_count` included) — a
// v16-cached day holds the old flat objects, which the new row would misread.
// v18: a road's points can now carry a **numbered pin** of their own
// (`display_start_on_maps` / `display_end_on_maps` /
// `display_intermediate_point_on_maps`), so a waypoint gained `map_pin` and the
// road's own `map_pin` became its departure's — and a leg gained the `gpx` it
// was drawn from, which the "(Get GPX track)" button hands back. A v17-cached
// day has none of them, and its numbering predates the road pins joining the
// day's 1..N sequence.
// v19: the static map images are drawn from Carto's **vector** tiles now, not
// its pre-rendered raster ones (which answer keyless requests with an "API KEY
// REQUIRED" watermark). No field changed shape — but a cached day carries the
// rendered PNGs, so a v18 entry would keep handing back watermarked maps for an
// itinerary whose JSON never moved. Exactly the case the hash can't catch.
// v20: `display_intermediate_point_on_maps` now defaults **on**, so every
// multi-leg drive that never mentioned it pins its junctions — those pins join
// the day's 1..N sequence, which renumbers everything after the drive. Same
// shape, same JSON, different `map_pin` on most days: the hash can't see it.
// v21: a day's points are folded before they're numbered — same name within a
// kilometre is one place, so it wears one pin and one number (`fold_pins`).
// Again no field changed shape, but a place named twice used to take two
// numbers and everything after it shifted, so `map_pin` moves on any day that
// repeats a place.
// v22: an activity gained `detour`, and a detour is left off the timeline — so
// it carries a duration but no `start_time`/`end_time`, no buffer is inserted
// before it, and every activity after it on that day moves earlier. A
// v21-cached day carries the flag nowhere (so the row wouldn't be marked or
// dimmed) *and* holds the old, later times.
// v23: activities gained a `price` (an entrance fee, structured like a
// booking's) and a `contact`; a point of interest's `opening` gained `per_day`
// + `rules`, so hours that differ by weekday can be drawn per day; and a
// transport leg gained `distance_km`. A v22-cached day carries none of them, so
// the fee, the phone number, the Sunday hours and the leg's distance would all
// be missing while the CLI printed them.
// v24: a hike's `track` gained `map`, the static trail PNG shown when the
// interactive-maps toggle is off (previously that toggle left a hike with its
// elevation profile and no trail at all). And every rendered image moved: a
// tile the basemap answers 404 for is empty country now, not a failure, so a
// map framed on somewhere the tiles run thin — a high lake, a desert piste —
// draws instead of being dropped whole. A v23 entry has neither: no trail PNG,
// and possibly no day map where one is now perfectly renderable.
// v25: v24's blank-square rule never reached *this* renderer. Carto sends no
// CORS header on the 404 it answers for a featureless tile, so in the browser
// that tile arrives as an unreadable network error — the fix keyed on the status
// could not fire, and a map over empty country still failed whole here while the
// CLI drew it. Judged per render now, so a v24 entry can be missing exactly the
// maps that most needed drawing (a high lake's trail, a desert piste).
const SCHEMA_VERSION = 25;

interface Entry {
  day: Day;
  ts: number; // when cached (ms epoch)
}

/** A stable key for an itinerary's content — changes whenever the JSON changes,
 * so edits naturally miss the cache. SHA-256 in a secure context; a cheap djb2
 * fallback otherwise (dev over plain http, etc.). */
export async function docHash(text: string): Promise<string> {
  try {
    const buf = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(text));
    return [...new Uint8Array(buf)].map((b) => b.toString(16).padStart(2, "0")).join("");
  } catch {
    let h = 5381;
    for (let i = 0; i < text.length; i++) h = (((h << 5) + h) ^ text.charCodeAt(i)) | 0;
    return "djb2-" + (h >>> 0).toString(16);
  }
}

const keyPrefix = (hash: string) => `v${SCHEMA_VERSION}:${hash}:`;
const keyFor = (hash: string, index: number) => `${keyPrefix(hash)}${index}`;

function openDb(): Promise<IDBDatabase> {
  return new Promise((resolve, reject) => {
    const req = indexedDB.open(DB_NAME, 1);
    req.onupgradeneeded = () => req.result.createObjectStore(STORE);
    req.onerror = () => reject(req.error);
    req.onsuccess = () => resolve(req.result);
  });
}

/** The cached day for `(hash, index)`, or null if absent or older than 30 days. */
export async function getCachedDay(hash: string, index: number): Promise<Day | null> {
  try {
    const db = await openDb();
    return await new Promise<Day | null>((resolve) => {
      const t = db.transaction(STORE, "readonly");
      const req = t.objectStore(STORE).get(keyFor(hash, index));
      req.onsuccess = () => {
        const e = req.result as Entry | undefined;
        resolve(e && Date.now() - e.ts <= TTL_MS ? e.day : null);
      };
      req.onerror = () => resolve(null);
      t.oncomplete = () => db.close();
    });
  } catch {
    return null;
  }
}

/** Store a freshly rendered day under `(hash, index)`. */
export async function putCachedDay(hash: string, index: number, day: Day): Promise<void> {
  try {
    const db = await openDb();
    await new Promise<void>((resolve) => {
      const t = db.transaction(STORE, "readwrite");
      t.objectStore(STORE).put({ day, ts: Date.now() } as Entry, keyFor(hash, index));
      t.oncomplete = () => {
        db.close();
        resolve();
      };
      t.onerror = () => resolve();
    });
  } catch {
    /* best-effort */
  }
}

/** Drop every cached day for one itinerary (the "redraw this file's maps" path). */
export async function invalidateDoc(hash: string): Promise<void> {
  try {
    const db = await openDb();
    await new Promise<void>((resolve) => {
      const t = db.transaction(STORE, "readwrite");
      // Cover every `v<schema>:<hash>:<index>` key (￿ sorts after any real
      // suffix). Older-schema entries are already unreachable; purgeExpired
      // drops them.
      const range = IDBKeyRange.bound(keyPrefix(hash), `${keyPrefix(hash)}￿`);
      const cur = t.objectStore(STORE).openCursor(range);
      cur.onsuccess = () => {
        const c = cur.result;
        if (c) {
          c.delete();
          c.continue();
        }
      };
      t.oncomplete = () => {
        db.close();
        resolve();
      };
      t.onerror = () => resolve();
    });
  } catch {
    /* best-effort */
  }
}

/** Evict entries older than the 30-day TTL, plus any left over from an earlier
 * `SCHEMA_VERSION` (unreachable, so pure dead weight). Called once at startup. */
export async function purgeExpired(): Promise<void> {
  try {
    const db = await openDb();
    await new Promise<void>((resolve) => {
      const cutoff = Date.now() - TTL_MS;
      const t = db.transaction(STORE, "readwrite");
      const cur = t.objectStore(STORE).openCursor();
      cur.onsuccess = () => {
        const c = cur.result;
        if (!c) return;
        const e = c.value as Entry | undefined;
        const current = String(c.key).startsWith(`v${SCHEMA_VERSION}:`);
        if (!e || e.ts < cutoff || !current) c.delete();
        c.continue();
      };
      t.oncomplete = () => {
        db.close();
        resolve();
      };
      t.onerror = () => resolve();
    });
  } catch {
    /* best-effort */
  }
}
