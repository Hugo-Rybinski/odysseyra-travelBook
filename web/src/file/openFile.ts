// Opening a local itinerary JSON, entirely on-device.
//
// Prefers the File System Access API (Chromium desktop) so we can keep a handle
// and re-open the same file later; falls back to a hidden <input type=file>
// where that API is missing (notably iOS Safari). No data ever leaves the
// device — we only read the file the user picks.

// --- minimal ambient typing (these aren't in the standard DOM lib yet) -------

type PermState = "granted" | "denied" | "prompt";

interface FsFileHandle {
  readonly name: string;
  getFile(): Promise<File>;
  queryPermission?(d: { mode: "read" | "readwrite" }): Promise<PermState>;
  requestPermission?(d: { mode: "read" | "readwrite" }): Promise<PermState>;
}

interface PickerWindow {
  showOpenFilePicker?: (opts?: {
    types?: { description?: string; accept: Record<string, string[]> }[];
    excludeAcceptAllOption?: boolean;
    multiple?: boolean;
  }) => Promise<FsFileHandle[]>;
}

export interface OpenedFile {
  name: string;
  text: string;
  handle: FsFileHandle | null; // null when opened via the input fallback
}

const PICKER_OPTS = {
  types: [{ description: "Itinerary JSON", accept: { "application/json": [".json"] } }],
  excludeAcceptAllOption: false,
  multiple: false,
};

export function hasFsAccess(): boolean {
  return typeof (window as PickerWindow).showOpenFilePicker === "function";
}

/** Show the OS file picker (or the input fallback) and read the chosen file. */
export async function openFile(): Promise<OpenedFile | null> {
  const picker = (window as PickerWindow).showOpenFilePicker;
  if (picker) {
    let handles: FsFileHandle[];
    try {
      handles = await picker(PICKER_OPTS);
    } catch (e) {
      if (e instanceof DOMException && e.name === "AbortError") return null; // user cancelled
      throw e;
    }
    const handle = handles[0];
    const file = await handle.getFile();
    return { name: handle.name, text: await file.text(), handle };
  }
  return openViaInput();
}

/** Fallback: a transient <input type=file> (no handle to persist). */
function openViaInput(): Promise<OpenedFile | null> {
  return new Promise((resolve, reject) => {
    const input = document.createElement("input");
    input.type = "file";
    input.accept = "application/json,.json";
    input.onchange = async () => {
      const file = input.files?.[0];
      if (!file) return resolve(null);
      try {
        resolve({ name: file.name, text: await file.text(), handle: null });
      } catch (e) {
        reject(e);
      }
    };
    // If the dialog is dismissed no change event fires; that's fine — the promise
    // simply stays pending until the next open, which is acceptable here.
    input.click();
  });
}

/** Re-read a previously kept handle, requesting read permission if needed. */
export async function reopenHandle(handle: FsFileHandle): Promise<OpenedFile | null> {
  const opts = { mode: "read" as const };
  const query = (await handle.queryPermission?.(opts)) ?? "granted";
  if (query !== "granted") {
    const req = (await handle.requestPermission?.(opts)) ?? "denied";
    if (req !== "granted") return null;
  }
  const file = await handle.getFile();
  return { name: handle.name, text: await file.text(), handle };
}

// --- tiny IndexedDB key/value store (no dependency) --------------------------
// File System Access handles are structured-cloneable, so the last one can be
// stashed to offer "reopen last file" across sessions.

const DB_NAME = "travelbook";
const STORE = "kv";
const LAST_KEY = "lastFileHandle";

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

export async function rememberHandle(handle: FsFileHandle | null): Promise<void> {
  if (!handle) return; // nothing to persist for the input fallback
  try {
    await withStore("readwrite", (s) => s.put(handle, LAST_KEY));
  } catch {
    /* persistence is best-effort */
  }
}

export async function loadLastHandle(): Promise<FsFileHandle | null> {
  try {
    return (await withStore<FsFileHandle | undefined>("readonly", (s) =>
      s.get(LAST_KEY),
    )) ?? null;
  } catch {
    return null;
  }
}
