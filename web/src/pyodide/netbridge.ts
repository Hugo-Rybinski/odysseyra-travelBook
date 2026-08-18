// The network seam the in-browser maps rendering uses. Pyodide has no sockets,
// so the Python `travelbook.maps.http_get` seam is overridden (in bridge.py) to
// call `httpGetSync` here, exposed to Python as the `tb_js` module.
//
// It is a *synchronous* XHR on purpose: the maps code is synchronous Python
// driven from the main thread, and Pyodide can't await a JS promise from sync
// Python without stack-switching. Sync XHR blocks the main thread for the
// duration of the fetch — acceptable because (a) map tiles/routes are the only
// callers, (b) the service worker serves them from cache after the first online
// build, so repeats and offline are fast, and (c) a "Rendering…" state covers
// the first-time cost. Moving Pyodide into a Web Worker would remove even that.
//
// The three map endpoints (Carto tiles, OSRM, Nominatim) all send
// `Access-Control-Allow-Origin: *`, so this works cross-origin with no proxy —
// the app stays local-only.

export interface SyncFetchResult {
  ok: boolean;
  status: number;
  error: string;
  bytes: Uint8Array;
}

const EMPTY = new Uint8Array(0);

/** Fetch `url` synchronously and return its raw bytes (or an error result).
 * Binary is read via the classic `x-user-defined` charset trick, since a
 * synchronous XHR on the main thread cannot use `responseType`. */
export function httpGetSync(url: string): SyncFetchResult {
  const xhr = new XMLHttpRequest();
  try {
    xhr.open("GET", url, false); // synchronous
    // Preserve every byte 1:1 as a code unit we can mask back to 0x00–0xFF.
    xhr.overrideMimeType("text/plain; charset=x-user-defined");
    xhr.send();
  } catch (e) {
    return { ok: false, status: 0, error: String(e), bytes: EMPTY };
  }
  const status = xhr.status;
  if (status < 200 || status >= 300) {
    return { ok: false, status, error: xhr.statusText || `HTTP ${status}`, bytes: EMPTY };
  }
  const text = xhr.responseText;
  const bytes = new Uint8Array(text.length);
  for (let i = 0; i < text.length; i++) bytes[i] = text.charCodeAt(i) & 0xff;
  return { ok: true, status, error: "", bytes };
}
