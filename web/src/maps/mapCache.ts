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
const SCHEMA_VERSION = 11;

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
