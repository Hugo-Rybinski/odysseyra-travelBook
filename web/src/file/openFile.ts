// Opening a local itinerary JSON, entirely on-device.
//
// Prefers the File System Access API (Chromium desktop) so we can keep a handle
// and re-open the same file later; falls back to a hidden <input type=file>
// where that API is missing (notably iOS Safari). No data ever leaves the
// device — we only read the file the user picks.

// --- minimal ambient typing (these aren't in the standard DOM lib yet) -------

type PermState = "granted" | "denied" | "prompt";

interface FsWritable {
  write(data: string | BufferSource | Blob): Promise<void>;
  close(): Promise<void>;
}

interface FsFileHandle {
  readonly name: string;
  getFile(): Promise<File>;
  createWritable?(): Promise<FsWritable>;
  queryPermission?(d: { mode: "read" | "readwrite" }): Promise<PermState>;
  requestPermission?(d: { mode: "read" | "readwrite" }): Promise<PermState>;
}

interface PickerWindow {
  showOpenFilePicker?: (opts?: {
    types?: { description?: string; accept: Record<string, string[]> }[];
    excludeAcceptAllOption?: boolean;
    multiple?: boolean;
  }) => Promise<FsFileHandle[]>;
  showSaveFilePicker?: (opts?: {
    suggestedName?: string;
    types?: { description?: string; accept: Record<string, string[]> }[];
    excludeAcceptAllOption?: boolean;
  }) => Promise<FsFileHandle>;
}

export interface OpenedFile {
  name: string;
  text: string;
  handle: FsFileHandle | null; // null when opened via the input fallback
}

// The OS picker greys out anything it can't match, so list every MIME spelling a
// .json file gets in the wild ("text/json" on some systems, plain text when no
// JSON type is registered at all). `excludeAcceptAllOption: false` keeps an "All
// files" entry in the dialog's type dropdown as the escape hatch.
const JSON_ACCEPT: Record<string, string[]> = {
  "application/json": [".json"],
  "text/json": [".json"],
  "text/plain": [".json"],
};

const PICKER_OPTS = {
  types: [{ description: "Itinerary JSON", accept: JSON_ACCEPT }],
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
    // Deliberately unfiltered. iOS/Safari maps `accept` to UTIs and ignores the
    // extension list, so `accept="application/json"` greys out perfectly good
    // .json files with no dropdown to escape through — a file you cannot pick is
    // worse than a picker that shows too much. The content is parsed and
    // validated on open anyway, so a wrong pick fails loudly, not silently.
    input.accept = "";
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

// --- writing back (P4: save the edited itinerary) ---------------------------

/** Whether this handle can be written in place (Chromium; not the input fallback). */
export function canWriteHandle(handle: FsFileHandle | null | undefined): handle is FsFileHandle {
  return !!handle && typeof handle.createWritable === "function";
}

/** Whether the browser can offer a "Save as…" file picker. */
export function hasSavePicker(): boolean {
  return typeof (window as PickerWindow).showSaveFilePicker === "function";
}

/** Overwrite a file in place through its handle, prompting for write access. */
export async function writeHandle(handle: FsFileHandle, text: string): Promise<void> {
  const opts = { mode: "readwrite" as const };
  const query = (await handle.queryPermission?.(opts)) ?? "granted";
  if (query !== "granted") {
    const req = (await handle.requestPermission?.(opts)) ?? "denied";
    if (req !== "granted") throw new Error("Permission to write the file was denied.");
  }
  const writable = await handle.createWritable!();
  await writable.write(text);
  await writable.close();
}

/** Show the OS "Save as…" picker, write `text`, and return the new handle. */
export async function saveAsJson(suggestedName: string, text: string): Promise<OpenedFile | null> {
  const picker = (window as PickerWindow).showSaveFilePicker;
  if (!picker) return null;
  let handle: FsFileHandle;
  try {
    handle = await picker({
      suggestedName,
      types: [{ description: "Itinerary JSON", accept: { "application/json": [".json"] } }],
    });
  } catch (e) {
    if (e instanceof DOMException && e.name === "AbortError") return null; // user cancelled
    throw e;
  }
  const writable = await handle.createWritable!();
  await writable.write(text);
  await writable.close();
  return { name: handle.name, text, handle };
}

/** Whether this handle can be read *without* asking — i.e. the permission is
 * already granted, so re-reading it needs no user gesture.
 *
 * The whole point of the distinction: `requestPermission` may only be called
 * from a user activation, so the "reopen the last file automatically on load"
 * path can query but must never request. Chromium grants persistent permission
 * to an installed PWA (and to a site the user has allowed on every visit), which
 * is when this answers true after a reload; everywhere else the stashed text is
 * the route back in (see `rememberSession`). */
export async function canReadHandle(handle: FsFileHandle): Promise<boolean> {
  try {
    return ((await handle.queryPermission?.({ mode: "read" })) ?? "granted") === "granted";
  } catch {
    return false;
  }
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

const DB_NAME = "odysseyra";
const STORE = "kv";
const LAST_KEY = "lastFileHandle";
const SESSION_KEY = "lastSession";

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
      // `fn` can throw *synchronously* — `put` does, for a value that can't be
      // structured-cloned. Inside this event handler an escaping throw would
      // leave the promise pending for ever, and `analyze` awaits
      // `rememberHandle`, so the app would sit on "Reading the itinerary…" with
      // its File buttons disabled and no error anywhere.
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

// --- the last session, so a reload comes back to the file you were reading ---

export interface LastSession {
  name: string;
  text: string;
  at: number; // epoch ms
}

/** Remember the file currently open — its name *and* its text.
 *
 * The handle alone can't reopen it on a reload: most browsers answer
 * `queryPermission` with "prompt" after a restart and `requestPermission` needs
 * a click, and there is no handle at all for a file picked through the `<input>`
 * fallback (iOS Safari), the bundled demo or a blank scaffold. So the text rides
 * along and the handle stays the preferred route — re-reading from disk when it
 * is still permitted picks up edits made outside the app, which the stash can't.
 *
 * Distinct from `edit/autosave.ts`, which stashes an *unsaved draft* and is
 * cleared the moment it's written to a file. This is "what was on screen",
 * saved or not, and outlives that. */
export async function rememberSession(name: string, text: string): Promise<void> {
  try {
    await withStore("readwrite", (s) =>
      s.put({ name, text, at: Date.now() } as LastSession, SESSION_KEY),
    );
  } catch {
    /* persistence is best-effort */
  }
}

export async function loadSession(): Promise<LastSession | null> {
  try {
    return (
      (await withStore<LastSession | undefined>("readonly", (s) => s.get(SESSION_KEY))) ?? null
    );
  } catch {
    return null;
  }
}

export async function clearSession(): Promise<void> {
  try {
    await withStore("readwrite", (s) => s.delete(SESSION_KEY));
  } catch {
    /* best-effort */
  }
}
