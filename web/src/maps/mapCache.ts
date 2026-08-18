// Persistent cache for the per-day maps (the whole resolved `Day` including the
// base64 map images + pin labels the Python renderer produced), so a killed and
// relaunched app doesn't have to redraw them — it hydrates instantly from here
// and only renders days that are missing or stale.
//
// Keyed by `<hash of the itinerary JSON>:<day index>` and kept for 30 days, in
// its own IndexedDB database (so it needn't share the file-handle DB's version).
// Everything is best-effort: any failure resolves to a cache miss, never throws.
import type { Day } from "../types/resolved";

const DB_NAME = "travelbook-maps";
const STORE = "days";
const TTL_MS = 30 * 24 * 60 * 60 * 1000; // 30 days

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

const keyFor = (hash: string, index: number) => `${hash}:${index}`;

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
      // Cover every `<hash>:<index>` key (￿ sorts after any real suffix).
      const range = IDBKeyRange.bound(`${hash}:`, `${hash}:￿`);
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

/** Evict entries older than the 30-day TTL. Called once at startup. */
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
        if (!e || e.ts < cutoff) c.delete();
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
