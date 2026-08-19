// Autosave the edit draft to IndexedDB (P6) so unsaved edits survive a reload or
// a service-worker update. A single record is kept (the latest draft); the app
// offers to restore it on next launch and clears it once the draft is saved to a
// file or the user discards it. Everything stays on-device.

const DB_NAME = "odysseyra-edit";
const STORE = "kv";
const KEY = "autosaveDraft";

export interface AutosaveRecord {
  name: string; // the source filename this draft came from (for the restore prompt)
  text: string; // the serialized draft JSON
  at: number; // epoch ms of the last autosave
}

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
      const tx = db.transaction(STORE, mode);
      const req = fn(tx.objectStore(STORE));
      req.onerror = () => reject(req.error);
      req.onsuccess = () => resolve(req.result as T);
      tx.oncomplete = () => db.close();
    };
  });
}

export async function saveAutosave(rec: AutosaveRecord): Promise<void> {
  try {
    await withStore("readwrite", (s) => s.put(rec, KEY));
  } catch {
    /* best-effort */
  }
}

export async function loadAutosave(): Promise<AutosaveRecord | null> {
  try {
    return (await withStore<AutosaveRecord | undefined>("readonly", (s) => s.get(KEY))) ?? null;
  } catch {
    return null;
  }
}

export async function clearAutosave(): Promise<void> {
  try {
    await withStore("readwrite", (s) => s.delete(KEY));
  } catch {
    /* best-effort */
  }
}
