// The network seam the in-browser maps rendering uses. Pyodide has no sockets,
// so the Python `odysseyra_travelbook.maps.http_get` seam is overridden (in bridge.py) to
// call `httpGetSync` here, exposed to Python as the `tb_js` module.
//
// It is a *synchronous* XHR on purpose: the maps code is synchronous Python, and
// Pyodide can't await a JS promise from sync Python without stack-switching. The
// engine runs in a Web Worker (see worker.ts), so blocking here blocks that
// worker and not the page — the UI keeps painting its loader while tiles come
// in. On the main-thread fallback it does freeze the page, as it always did.
//
// The three map endpoints (Carto tiles, OSRM, Nominatim) send
// `Access-Control-Allow-Origin: *` on a response they have, so this works
// cross-origin with no proxy — the app stays local-only. They do **not** send it
// on an error response: Carto answers 404 for a vector tile holding no features
// (empty country, which is exactly where a trail map is most wanted) with no
// CORS header at all, so the browser blocks it and a sync XHR throws a bare
// NetworkError. `status` then reads 0 and there is no way to tell that 404 from
// being offline — which is why the "one blank square isn't a failure" rule lives
// in `maps/basemap.py`'s `render_basemap` (per render) and not in the status
// check here or in `tile_bytes` (per tile).

export interface SyncFetchResult {
  ok: boolean;
  status: number;
  error: string;
  bytes: Uint8Array;
}

const EMPTY = new Uint8Array(0);

// A synchronous XHR may only set `responseType` off the main thread — the setter
// throws on a Window. In the worker (the normal path) that lets us take the
// bytes straight as an ArrayBuffer instead of decoding a text response
// character by character; a tile is ~50–150 KB, and the loop is pure overhead.
const CAN_SET_RESPONSE_TYPE = typeof document === "undefined";

/** Fetch `url` synchronously and return its raw bytes (or an error result). */
export function httpGetSync(url: string): SyncFetchResult {
  const xhr = new XMLHttpRequest();
  let binary = false;
  try {
    xhr.open("GET", url, false); // synchronous
    if (CAN_SET_RESPONSE_TYPE) {
      try {
        xhr.responseType = "arraybuffer";
        binary = true;
      } catch {
        binary = false; // fall back to the text trick below
      }
    }
    if (!binary) {
      // Preserve every byte 1:1 as a code unit we can mask back to 0x00–0xFF.
      xhr.overrideMimeType("text/plain; charset=x-user-defined");
    }
    xhr.send();
  } catch (e) {
    return { ok: false, status: 0, error: String(e), bytes: EMPTY };
  }
  const status = xhr.status;
  if (status < 200 || status >= 300) {
    return { ok: false, status, error: xhr.statusText || `HTTP ${status}`, bytes: EMPTY };
  }
  if (binary) {
    const buf = xhr.response as ArrayBuffer | null;
    return { ok: true, status, error: "", bytes: buf ? new Uint8Array(buf) : EMPTY };
  }
  const text = xhr.responseText;
  const bytes = new Uint8Array(text.length);
  for (let i = 0; i < text.length; i++) bytes[i] = text.charCodeAt(i) & 0xff;
  return { ok: true, status, error: "", bytes };
}
