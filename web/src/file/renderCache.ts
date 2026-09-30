// The last book we rendered, kept so the next launch can paint it before the
// Python engine exists.
//
// Reopening the last file is otherwise gated on the whole engine: `analyze`
// boots Pyodide, installs the wheel, then validates and resolves — seconds on a
// cold cache, during which the app has nothing to show but a splash. None of
// that work depends on anything that changed while the tab was closed, so the
// *result* is cacheable: the resolved document is plain JSON (~90 KB for the
// flagship example), and the book is a pure function of it. Paint it, then let
// the engine catch up and say whether we were right.
//
// Two questions decide that, and they are asked once the runtime is up (see
// App's auto-reopen effect):
//
//  1. **Is it still the same file?** The stored `hash` is `docHash` of the text
//     this document was resolved from. The launch path re-reads the file from
//     disk where it can, so the bytes on screen may already be out of date —
//     someone edited the JSON in another editor between sessions.
//  2. **Did this build produce it?** `RENDER_BUILD` pairs the bundle's commit
//     with `SCHEMA_VERSION`. The commit covers a deploy (the wheel ships inside
//     it, so any engine change moves the hash); `SCHEMA_VERSION` covers the
//     development loop, where the commit is stable across edits and the project
//     already requires a bump whenever the resolved document changes shape or is
//     computed differently. Together they answer "would today's engine produce
//     this?" without a round-trip to ask it.
//
// Both yes → the screen is already what a recompute would produce, so nothing
// happens. Either no → recompute and swap the answer in.
//
// This is deliberately **not** the map cache (`maps/mapCache.ts`), and the two
// are stored apart: that one holds megabytes of per-day images keyed by content
// hash, and the record here holds the map-free document `resolve()` returns.
// Keeping images out is what makes it one small record with no budget, no TTL
// and no LRU — and the day images are hydrated from their own cache on top.
//
// Only a document that actually *built* is stored. A file that can't resolve has
// nothing to paint, so that launch takes the engine path and explains itself.

import type { Finding, Itinerary } from "../types/resolved";
import { SCHEMA_VERSION } from "../maps/mapCache";
import { COMMIT_HASH } from "../version";

/** The identity of the code that renders a document — see (2) above. */
export const RENDER_BUILD = `${COMMIT_HASH}:${SCHEMA_VERSION}`;

export interface RenderRecord {
  /** The file this was resolved from; a different name is a different document
   *  and never painted from here. */
  name: string;
  /** `docHash` of that file's text — the content check. */
  hash: string;
  /** `RENDER_BUILD` at the time it was produced — the build check. */
  build: string;
  /** The language `findings` were produced in. The resolved document itself is
   *  language-neutral (each renderer localizes it), but validator messages are
   *  not, so a language change has to recompute like any other staleness. */
  lang: string;
  /** The document as `resolve()` returned it: no day maps (see above). */
  itinerary: Itinerary;
  findings: Finding[];
  at: number; // epoch ms
}

const DB_NAME = "odysseyra-render";
const STORE = "kv";
const KEY = "lastRender";

function withStore<T>(
  mode: IDBTransactionMode,
  fn: (store: IDBObjectStore) => IDBRequest,
): Promise<T> {
  return new Promise((resolve, reject) => {
    const open = indexedDB.open(DB_NAME, 1);
    open.onupgradeneeded = () => open.result.createObjectStore(STORE);
    open.onerror = () => reject(open.error);
    open.onsuccess = () => {
      const db = open.result;
      try {
        const tx = db.transaction(STORE, mode);
        const req = fn(tx.objectStore(STORE));
        req.onerror = () => reject(req.error);
        req.onsuccess = () => resolve(req.result as T);
        tx.onabort = () => reject(tx.error);
        tx.oncomplete = () => db.close();
      } catch (e) {
        db.close();
        reject(e);
      }
    };
  });
}

export async function saveRender(rec: RenderRecord): Promise<void> {
  try {
    await withStore("readwrite", (s) => s.put(rec, KEY));
  } catch {
    /* best-effort: losing it costs one slow launch, nothing else */
  }
}

export async function loadRender(): Promise<RenderRecord | null> {
  try {
    const rec = (await withStore<RenderRecord | undefined>("readonly", (s) => s.get(KEY))) ?? null;
    // A record without a document is no use, and one written by an older shape
    // of this module must not be trusted into the renderer.
    return rec && rec.itinerary && rec.hash && rec.name ? rec : null;
  } catch {
    return null;
  }
}

export async function clearRender(): Promise<void> {
  try {
    await withStore("readwrite", (s) => s.delete(KEY));
  } catch {
    /* best-effort */
  }
}
