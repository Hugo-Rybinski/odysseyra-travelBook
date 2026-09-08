// Persistent cache for the per-day maps (the whole resolved `Day` including the
// base64 map images + pin labels the Python renderer produced), so a killed and
// relaunched app doesn't have to redraw them — it hydrates instantly from here
// and only renders days that are missing or stale.
//
// Keyed by `v<schema>:<hash of the itinerary JSON>:<day index>` and kept for 30
// days, in its own IndexedDB database (so it needn't share the file-handle DB's
// version).
// Everything is best-effort: any failure resolves to a cache miss, never throws
// — except a *write*, which reports why it failed (see `putCachedDay`).
//
// ## Two stores, not one
//
// An entry is **big**: a day of the France demo is 2–4 MB of base64 PNG, and the
// whole trip is ~20 MB. So the day and its description are stored apart —
// `days` holds the payload, `meta` a few dozen bytes naming the file, the day
// and the byte count. Listing the cache (Options → Maps) then walks `meta`
// alone; reading it out of `days` would structured-clone 20 MB to print eight
// lines. The two are written in one transaction and `purgeExpired` drops any
// key that has lost its twin, so they cannot drift apart.
//
// ## Why the size matters
//
// At 20 MB a trip, an unbounded store is a real hazard rather than a tidiness
// problem: IndexedDB is *best-effort* storage by default, and a browser over
// its quota evicts the **whole origin** — the map cache, the last-file handle
// and the autosaved draft together. Three things keep it in hand, and all three
// exist because the cache is keyed on the document's *text*, so an edit is a
// brand-new 20 MB set rather than an update of the old one:
//   - `dropStaleVersions(file, keep)` — before refilling a file's days, every
//     entry for that **same filename** under a different hash is dropped. That
//     is what turns "one set per edit, forever" into "one set per file", and it
//     is the single biggest win here.
//   - `enforceBudget()` — a hard `BUDGET_BYTES` ceiling over everything, oldest
//     evicted first, for the case the per-file rule can't cover (many files).
//   - `requestPersistence()` — asks the browser to stop treating the origin as
//     evictable at all. Granted silently for an installed PWA, refused silently
//     otherwise; either way it costs one call at startup.
import { parseVersionedName } from "../file/version";
import type { Day } from "../types/resolved";

const DB_NAME = "odysseyra-maps";
const STORE = "days";
const META = "meta";
const DB_VERSION = 2;
const TTL_MS = 30 * 24 * 60 * 60 * 1000; // 30 days
// ~8 trips the size of the France demo (20 MB each). Generous enough that the
// ceiling is never the reason a map is missing, small enough to stay well inside
// a browser's quota so the origin isn't evicted wholesale.
const BUDGET_BYTES = 160 * 1024 * 1024;

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
// v26: a day map's `geo.points` gained `from_road`, marking a pin that is one of
// a drive's own points (its departure, a junction, its arrival). The 🗺️ Overview
// drops those now — a drive is a line at trip zoom, and pinning the places along
// it stacked copies of the same day number on it. A v25 entry has the flag
// nowhere, so its drives' junctions would go on being pinned there.
// v27: a day gained `show_map` and every activity gained one of its own — the
// per-object twin of the trip's map switches (the day's overview map, a place's
// zoom map, a hike's trail map). A v26 entry carries neither flag *and* was
// rendered without them, so a day that switches its map off would keep serving
// the map, its pin numbers and its area maps from the cache.
// v29: a `road` gained `hide_on_map` (drop its route line) and so did a
// transport leg (drop its dotted line). A v28 entry carries neither flag *and*
// was rendered — images, `geo.routes`, `geo.legs` — without them, so a drive or
// a leg that switches its line off would keep serving the line from the cache.
// v28: a coordinate's `show_on_map` (default true) became `hide_on_map`
// (default false) — the same question the other way round. A v27 entry
// carries the retired key, which every reader now ignores, so a hidden pin
// would come back on the day map, the trip map and in the day's geo.
// v30: a hike's `track` gained `waypoints` (the named points its GPX carries)
// and `km_marks` (the whole-kilometre scale the trail map and the elevation
// profile now share), and every trail map is drawn differently: direction
// arrowheads, numbered distance ticks, and a solid start marker with a hollow
// finish where there used to be two identical discs. A v29 entry has neither
// field *and* a `track.map` PNG rendered without any of it, so a trail would
// keep coming back as a shape with no story.
const SCHEMA_VERSION = 30;

interface Entry {
  day: Day;
  ts: number; // when cached (ms epoch)
}

/** The small twin of an `Entry`, in its own store: enough to list and account
 * for a cached day without reading its megabytes back out. */
interface Meta {
  file: string; // the filename the day was rendered from ("" if unknown)
  title: string;
  date: string | null;
  dayNumber: number;
  bytes: number;
  ts: number;
}

/** One row of the Options → Maps cache listing. */
export interface CachedDay extends Meta {
  hash: string;
  index: number;
}

/** Recursively sort object keys, so a document's *formatting* stops deciding
 * whether its maps are reusable. Object key order and whitespace mean nothing
 * to the Python model that draws the maps, but the raw text was hashed
 * verbatim — so re-indenting a file, or round-tripping it through the Edit tab
 * without changing a value, threw away every map it had. Arrays keep their
 * order (there it *is* meaning: a day's activities, a road's legs). */
function sortKeys(value: unknown): unknown {
  if (Array.isArray(value)) return value.map(sortKeys);
  if (value && typeof value === "object") {
    const out: Record<string, unknown> = {};
    for (const k of Object.keys(value as object).sort()) {
      out[k] = sortKeys((value as Record<string, unknown>)[k]);
    }
    return out;
  }
  return value;
}

/** A stable key for an itinerary's *content* — changes whenever a value in the
 * JSON changes, so edits naturally miss the cache, but not when only the
 * formatting does (see `sortKeys`). SHA-256 in a secure context; a cheap djb2
 * fallback otherwise (dev over plain http, etc.). */
export async function docHash(text: string): Promise<string> {
  let canonical = text;
  try {
    canonical = JSON.stringify(sortKeys(JSON.parse(text)));
  } catch {
    /* not parseable JSON — hash it as it stands */
  }
  try {
    const buf = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(canonical));
    return [...new Uint8Array(buf)].map((b) => b.toString(16).padStart(2, "0")).join("");
  } catch {
    let h = 5381;
    for (let i = 0; i < canonical.length; i++) {
      h = (((h << 5) + h) ^ canonical.charCodeAt(i)) | 0;
    }
    return "djb2-" + (h >>> 0).toString(16);
  }
}

const keyPrefix = (hash: string) => `v${SCHEMA_VERSION}:${hash}:`;
const keyFor = (hash: string, index: number) => `${keyPrefix(hash)}${index}`;

/** Split a stored key back into its parts. The hash is a hex digest (or the
 * `djb2-…` fallback), so the day index is whatever follows the last colon. */
function parseKey(key: string): { hash: string; index: number } | null {
  const m = /^v(\d+):(.+):(\d+)$/.exec(key);
  if (!m || m[1] !== String(SCHEMA_VERSION)) return null;
  return { hash: m[2], index: Number(m[3]) };
}

function openDb(): Promise<IDBDatabase> {
  return new Promise((resolve, reject) => {
    const req = indexedDB.open(DB_NAME, DB_VERSION);
    req.onupgradeneeded = () => {
      const db = req.result;
      if (!db.objectStoreNames.contains(STORE)) db.createObjectStore(STORE);
      if (!db.objectStoreNames.contains(META)) db.createObjectStore(META);
    };
    req.onerror = () => reject(req.error);
    req.onsuccess = () => resolve(req.result);
  });
}

/** The cached day for `(hash, index)`, or null if it isn't there.
 *
 * No TTL test of its own: `purgeExpired` is the single authority on the 30-day
 * limit and runs at startup, and since `touchDoc` refreshes *last use* on the
 * `meta` row alone, an entry's own `ts` is only when it was drawn. Comparing
 * against that here would throw away a map the budget is deliberately keeping —
 * a trip you open every week, first rendered five weeks ago. The TTL is a
 * disk-space rule, not a correctness one (that is `SCHEMA_VERSION` and the
 * content hash), so the worst an app left running for a month can do is serve a
 * map it should have swept. */
export async function getCachedDay(hash: string, index: number): Promise<Day | null> {
  let db: IDBDatabase | null = null;
  try {
    db = await openDb();
    return await new Promise<Day | null>((resolve) => {
      const t = db!.transaction(STORE, "readonly");
      const req = t.objectStore(STORE).get(keyFor(hash, index));
      req.onsuccess = () => resolve((req.result as Entry | undefined)?.day ?? null);
      req.onerror = () => resolve(null);
      t.onabort = () => resolve(null);
    });
  } catch {
    return null;
  } finally {
    db?.close();
  }
}

/** Store a freshly rendered day under `(hash, index)`, with the small `meta`
 * row that lets it be listed and accounted for.
 *
 * The one operation here that reports its failure instead of swallowing it: a
 * write is how the cache *fills*, and the way it fails in practice is
 * `QuotaExceededError` — after which every day misses for ever, silently, and
 * the app looks like it has no cache at all rather than a full disk. The caller
 * surfaces the message (Options → Maps). A miss on *read* stays silent, since
 * there the answer "not cached" is correct and acted on. */
export async function putCachedDay(
  hash: string,
  index: number,
  day: Day,
  file = "",
): Promise<{ ok: boolean; error?: string }> {
  let db: IDBDatabase | null = null;
  try {
    db = await openDb();
    const ts = Date.now();
    const meta: Meta = {
      file,
      title: day.title ?? "",
      date: day.date ?? null,
      dayNumber: day.day_number ?? index + 1,
      bytes: JSON.stringify(day).length,
      ts,
    };
    return await new Promise<{ ok: boolean; error?: string }>((resolve) => {
      const t = db!.transaction([STORE, META], "readwrite");
      t.objectStore(STORE).put({ day, ts } as Entry, keyFor(hash, index));
      t.objectStore(META).put(meta, keyFor(hash, index));
      t.oncomplete = () => resolve({ ok: true });
      // A quota failure aborts the transaction; `onerror` alone would let the
      // request's own error pass and still land here, so both are answered.
      t.onabort = () => resolve({ ok: false, error: errText(t.error) });
      t.onerror = () => resolve({ ok: false, error: errText(t.error) });
    });
  } catch (e) {
    return { ok: false, error: errText(e) };
  } finally {
    db?.close();
  }
}

function errText(e: unknown): string {
  if (e instanceof DOMException) return e.name === "QuotaExceededError" ? "quota" : e.name;
  return e ? String((e as Error).message ?? e) : "unknown";
}

/** Run `fn` against both stores in one read-write transaction, resolving when it
 * commits. Every mutating helper below shares this: a day and its `meta` twin
 * must be written and deleted together, or the pair drifts and `purgeExpired`
 * throws away a perfectly good map for having lost its label. */
async function mutate(fn: (days: IDBObjectStore, meta: IDBObjectStore) => void): Promise<void> {
  let db: IDBDatabase | null = null;
  try {
    db = await openDb();
    await new Promise<void>((resolve) => {
      const t = db!.transaction([STORE, META], "readwrite");
      fn(t.objectStore(STORE), t.objectStore(META));
      t.oncomplete = () => resolve();
      t.onabort = () => resolve();
      t.onerror = () => resolve();
    });
  } catch {
    /* best-effort */
  } finally {
    db?.close();
  }
}

/** Delete the `(hash, index)` pair from both stores. */
function deleteKey(days: IDBObjectStore, meta: IDBObjectStore, key: IDBValidKey): void {
  days.delete(key);
  meta.delete(key);
}

/** Drop every cached day for one itinerary (the "Redraw all maps" path). */
export async function invalidateDoc(hash: string): Promise<void> {
  // Cover every `v<schema>:<hash>:<index>` key (￿ sorts after any real suffix).
  // Older-schema entries are already unreachable; purgeExpired drops them.
  const range = IDBKeyRange.bound(keyPrefix(hash), `${keyPrefix(hash)}￿`);
  await mutate((days, meta) => {
    for (const store of [days, meta]) {
      const cur = store.openKeyCursor(range);
      cur.onsuccess = () => {
        const c = cur.result;
        if (!c) return;
        store.delete(c.key);
        c.continue();
      };
    }
  });
}

/** Drop one day's cached map (the per-day "Redraw" button). */
export async function invalidateDay(hash: string, index: number): Promise<void> {
  await mutate((days, meta) => deleteKey(days, meta, keyFor(hash, index)));
}

/** Drop every entry rendered from the same document as `file` under a hash other
 * than `keep`.
 *
 * This is the one that stops the store growing without bound. The key is the
 * document's *content*, so every applied edit starts a fresh 20 MB set and the
 * previous one becomes unreachable weight that only the 30-day TTL would ever
 * have collected — ten edit-and-redraw cycles left 200 MB of maps nobody could
 * reach. Called just *before* a file's days are refilled, when "another hash for
 * this same document" is exactly the definition of stale.
 *
 * **"Same document" is the `(vNN)`-less base name, not the filename.** Matching
 * the whole filename made this fire almost never in real use: every save route
 * that creates a file numbers it (`file/version.ts`), so the working loop is
 * `trip (v04).json` → `trip (v05).json` → …, and each save looked like a
 * brand-new document holding its own full set. A 15-day trip leaked 16 MB per
 * save that way, until the byte budget started evicting days that were still in
 * use. The `(vNN)` marker *is* this document's version history — that is the
 * whole reason it lives in the name — so two names sharing a base are two
 * revisions of one trip, and only the current one's maps are worth keeping.
 *
 * Two unrelated trips of the same base name in different folders evict each
 * other, which is the cost of having no stable file identity to key on (a File
 * System Access handle isn't one — it isn't comparable across sessions).
 * Self-healing: the loser is redrawn. */
export async function dropStaleVersions(file: string, keep: string): Promise<void> {
  // An unnamed source can't be told apart from any other, so it drops nothing.
  const base = parseVersionedName(file).base;
  if (!base) return;
  const stale = (await listCachedDays()).filter(
    (e) => e.hash !== keep && !!e.file && parseVersionedName(e.file).base === base,
  );
  if (!stale.length) return;
  await mutate((days, meta) => {
    for (const e of stale) deleteKey(days, meta, keyFor(e.hash, e.index));
  });
}

/** Every cached day, newest first — the Options → Maps listing, and the input to
 * the budget. Walks `meta` only, so it costs kilobytes rather than the tens of
 * megabytes the days themselves weigh. */
export async function listCachedDays(): Promise<CachedDay[]> {
  let db: IDBDatabase | null = null;
  try {
    db = await openDb();
    return await new Promise<CachedDay[]>((resolve) => {
      const out: CachedDay[] = [];
      const t = db!.transaction(META, "readonly");
      const cur = t.objectStore(META).openCursor();
      cur.onsuccess = () => {
        const c = cur.result;
        if (!c) return;
        const parsed = parseKey(String(c.key));
        if (parsed) out.push({ ...(c.value as Meta), ...parsed });
        c.continue();
      };
      t.oncomplete = () => resolve(out.sort((a, b) => b.ts - a.ts));
      t.onabort = () => resolve(out);
      t.onerror = () => resolve(out);
    });
  } catch {
    return [];
  } finally {
    db?.close();
  }
}

/** Mark a document's entries as used just now, so the TTL and the budget both
 * measure *last use* rather than when the maps happened to be drawn. Called
 * once per hydration, not once per day: the rows are tiny but a read-write
 * transaction per day would serialize against the reads it is interleaved with.
 * Touches `meta` alone — the payload is untouched, so this stays kilobytes. */
export async function touchDoc(hash: string): Promise<void> {
  const ts = Date.now();
  const range = IDBKeyRange.bound(keyPrefix(hash), `${keyPrefix(hash)}￿`);
  await mutate((_days, meta) => {
    const cur = meta.openCursor(range);
    cur.onsuccess = () => {
      const c = cur.result;
      if (!c) return;
      c.update({ ...(c.value as Meta), ts });
      c.continue();
    };
  });
}

/** Total bytes held, from the `meta` rows. */
export function cachedBytes(entries: CachedDay[]): number {
  return entries.reduce((n, e) => n + (e.bytes || 0), 0);
}

/** How much room the origin has, when the browser will say (Chromium/Firefox).
 * Null where `navigator.storage` isn't available. */
export async function storageEstimate(): Promise<{ usage: number; quota: number } | null> {
  try {
    const e = await navigator.storage?.estimate?.();
    return e ? { usage: e.usage ?? 0, quota: e.quota ?? 0 } : null;
  } catch {
    return null;
  }
}

/** Ask the browser to treat this origin's storage as persistent, so it isn't
 * evicted when the device runs short — which for us would take the map cache,
 * the last-file handle and the autosaved draft all at once. Granted silently for
 * an installed PWA (and on high engagement), refused just as silently
 * otherwise; either way it costs one call at startup and never prompts in
 * Chromium. Returns whether the origin is persistent now. */
export async function requestPersistence(): Promise<boolean> {
  try {
    if (!navigator.storage?.persist) return false;
    if (await navigator.storage.persisted?.()) return true;
    return await navigator.storage.persist();
  } catch {
    return false;
  }
}

/** Evict oldest-first until the store is under `BUDGET_BYTES`. The backstop for
 * what `dropStaleVersions` can't cover — many *different* files, each with its
 * own legitimate set. */
export async function enforceBudget(): Promise<void> {
  const entries = await listCachedDays(); // newest first
  let total = cachedBytes(entries);
  if (total <= BUDGET_BYTES) return;
  const doomed: CachedDay[] = [];
  for (const e of [...entries].reverse()) {
    if (total <= BUDGET_BYTES) break;
    doomed.push(e);
    total -= e.bytes || 0;
  }
  await mutate((days, meta) => {
    for (const e of doomed) deleteKey(days, meta, keyFor(e.hash, e.index));
  });
}

/** Evict entries older than the 30-day TTL, plus any left over from an earlier
 * `SCHEMA_VERSION` (unreachable, so pure dead weight) and any half of a pair
 * whose twin has gone. Then apply the byte budget. Called once at startup.
 *
 * Driven from the `meta` store, never by reading the days back: this runs on
 * every launch, and cursoring the payload store cloned the whole 20 MB cache
 * into the main thread just to look at a timestamp.
 *
 * Two transactions, and the decision is taken *inside* them rather than from a
 * list read beforehand — this runs concurrently with the map loop that fills the
 * cache (both start at launch), and a keep-set gathered up front doesn't know
 * about the day written a moment later, so the first launch after an upgrade
 * would delete the very maps it had just drawn. IndexedDB serializes overlapping
 * read-write transactions on the same stores, so as written a `putCachedDay`
 * either lands entirely before a sweep or entirely after it. */
export async function purgeExpired(): Promise<void> {
  const cutoff = Date.now() - TTL_MS;
  // 1. Expired or superseded-schema pairs, judged from the meta row itself.
  await mutate((days, meta) => {
    const cur = meta.openCursor();
    cur.onsuccess = () => {
      const c = cur.result;
      if (!c) return;
      const stale = !parseKey(String(c.key)) || (c.value as Meta).ts < cutoff;
      if (stale) {
        c.delete(); // the meta row the cursor is on…
        days.delete(c.key); // …and the payload it labels
      }
      c.continue();
    };
  });
  // 2. Days with no meta row: written before the two stores were split, or the
  // remains of a write that tore. Unlistable, so unaccountable — they would sit
  // in the store for ever without appearing in the budget or the listing.
  await mutate((days, meta) => {
    const cur = days.openKeyCursor();
    cur.onsuccess = () => {
      const c = cur.result;
      if (!c) return;
      const probe = meta.getKey(c.key);
      probe.onsuccess = () => {
        if (probe.result === undefined) days.delete(c.key);
      };
      c.continue();
    };
  });
  await enforceBudget();
}
