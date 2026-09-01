// The UI's handle on the Python engine. Same shape as it always had — `boot()`
// plus one async function per operation — but the work no longer happens here:
// it runs in a Web Worker (worker.ts), and this module is the RPC client.
//
// That indirection is the fix for a frozen page. Every engine call is
// synchronous Python, and rendering a map fetches its tiles over a blocking XHR
// (netbridge.ts), so on the main thread a PDF build or a day's map stopped the
// browser from painting at all — spinners included. Off-thread, the calls take
// exactly as long but cost the UI nothing, so a loader can actually spin (see
// ActivityIndicator) and the book stays scrollable while its maps arrive.
//
// If a Worker can't be created (or the worker script itself fails to start), we
// fall back to booting the engine on this thread: slower and it freezes during a
// call, as before, but the app works. The fallback is deliberately narrow — see
// `workerSpoke` below.
import type { Engine } from "./engine"; // type-only: the engine is a lazy chunk
import type {
  BootProgress,
  FromWorker,
  Op,
  OpArgs,
  OpResult,
  ToWorker,
} from "./protocol";
import type { Day, Finding, Itinerary } from "../types/resolved";

export type { BootProgress, Stage } from "./protocol";

type ProgressFn = (p: BootProgress) => void;

// Dev-only tracing (silent in production builds).
const log = (...args: unknown[]) => {
  if (import.meta.env.DEV) console.info(...args);
};

// Progress is broadcast to all subscribers and the latest stage is remembered,
// so a caller that subscribes after boot has started (or re-subscribes — React
// StrictMode double-invokes effects in dev) is replayed the current stage and
// still receives every later update.
let lastProgress: BootProgress = { stage: "idle" };
const progressSubs = new Set<ProgressFn>();

function emit(p: BootProgress) {
  lastProgress = p;
  progressSubs.forEach((fn) => fn(p));
}

interface Pending {
  resolve: (value: unknown) => void;
  reject: (error: Error) => void;
}

let worker: Worker | null = null;
let inThread: Engine | null = null; // set only on the fallback path
let bootPromise: Promise<void> | null = null;
let seq = 0;
const pending = new Map<number, Pending>();
// Whether the worker has ever answered. Until it has, a failure means the worker
// itself couldn't start (no module workers, a CSP, a blocked blob URL) and we
// retry in-thread. Once it has spoken, a failure is a real error from Python —
// re-running it here would only fail again, more slowly, and freeze the page.
let workerSpoke = false;
// Set when the worker reports an uncaught failure. Its `postMessage` queue would
// otherwise swallow every later call — a promise that never settles, i.e. a
// loader spinning for ever — so we fail fast instead.
let workerDead = false;

function onMessage(event: MessageEvent<FromWorker>) {
  const msg = event.data;
  workerSpoke = true;
  if (msg.kind === "progress") return emit(msg.progress);
  const p = pending.get(msg.id);
  if (!p) return;
  pending.delete(msg.id);
  if (msg.kind === "ok") p.resolve(msg.value);
  else p.reject(new Error(msg.error));
}

/** Ask the worker for one operation. */
function post<O extends Op>(msg: (id: number) => ToWorker): Promise<OpResult<O>> {
  const w = worker;
  if (!w || workerDead) {
    return Promise.reject(
      new Error("The engine stopped unexpectedly — reload the page to restart it."),
    );
  }
  const id = ++seq;
  return new Promise<OpResult<O>>((resolve, reject) => {
    pending.set(id, { resolve: resolve as (v: unknown) => void, reject });
    w.postMessage(msg(id));
  });
}

/** Spawn the worker and wait for its engine to be ready. Rejects if the worker
 * can't be created or its boot fails. */
async function startWorker(): Promise<void> {
  const w = new Worker(new URL("./worker.ts", import.meta.url), {
    type: "module",
    name: "odysseyra-engine",
  });
  worker = w;
  w.onmessage = onMessage;
  w.onerror = (e) => {
    // Reaches here for an uncaught worker-side error, including a failure to
    // load the worker module at all. Every op is try/caught inside the worker,
    // so this means the worker itself is gone rather than one call failing.
    if (workerSpoke) workerDead = true; // before boot: the fallback path retries
    const error = new Error(e.message || "The engine worker failed.");
    pending.forEach((p) => p.reject(error));
    pending.clear();
  };
  await post<Op>((id) => ({ kind: "boot", id }));
}

/** Boot the engine on this thread (fallback only). Imported dynamically so the
 * engine + the bridge source ship as a chunk nobody normally downloads — the
 * worker bundle has its own copy. */
async function startInThread(): Promise<void> {
  worker = null;
  const { bootEngine } = await import("./engine");
  inThread = await bootEngine(emit);
}

/** Boot the engine once (idempotent); resolves when it's ready to call. Safe to
 * call repeatedly — later callers subscribe to progress and share the one
 * in-flight (or completed) boot. */
export function boot(onProgress: ProgressFn = () => {}): Promise<void> {
  progressSubs.add(onProgress);
  onProgress(lastProgress); // replay the current stage to a late subscriber
  if (bootPromise) return bootPromise;
  bootPromise = (async () => {
    if (typeof Worker !== "undefined") {
      try {
        await startWorker();
        log("[boot] engine running in a worker");
        return;
      } catch (err) {
        if (workerSpoke) throw err; // a genuine Python/boot failure — don't retry
        log("[boot] worker unavailable, falling back to the main thread:", err);
        worker?.terminate();
        worker = null;
      }
    }
    await startInThread();
    log("[boot] engine running on the main thread (calls will block the UI)");
  })().catch((err) => {
    bootPromise = null; // allow a retry
    emit({ stage: "error", detail: String(err) });
    throw err;
  });
  return bootPromise;
}

/** Run one operation, wherever the engine happens to live. */
function call<O extends Op>(op: O, args: OpArgs<O>): Promise<OpResult<O>> {
  if (inThread) {
    // Synchronous — wrapped in a promise so both paths have one signature.
    return Promise.resolve().then(() => (inThread as Engine).call(op, args));
  }
  return post<O>((id) => ({ kind: "call", id, op, args }));
}

/** Validate raw itinerary JSON; returns findings (throws on a bridge error). */
export function validate(text: string, lang = "en"): Promise<Finding[]> {
  return call("validate", [text, lang]);
}

/** Resolve raw itinerary JSON into the render-ready model (throws on error).
 * Maps are NOT included here — the book renders immediately; each day's map is
 * fetched separately via `renderDayMap` (see App). */
export function resolve(text: string): Promise<Itinerary> {
  return call("resolve", [text]);
}

/** Render one day's maps and return that day with `day.map` (+ pin labels)
 * merged in, for the UI to swap in place. Fetches tiles with a blocking XHR, so
 * it occupies the engine (not the UI) for as long as it runs. */
export function renderDayMap(text: string, index: number): Promise<Day> {
  return call("renderDay", [text, index]);
}

/** Geocode a free-text address/name to a coordinate via Nominatim (needs the
 * network). `countries` are 2-letter ISO codes narrowing the search. Returns
 * null on no match; throws on a bridge error. */
export function geocode(
  query: string,
  countries: string[] = [],
): Promise<{ lat: number; long: number } | null> {
  return call("geocode", [query, countries.join(",")]);
}

/** Export the itinerary to iCalendar (.ics) text (no network / no maps).
 * Throws on a bridge error. */
export function buildIcs(text: string, lang = "en"): Promise<string> {
  return call("ics", [text, lang]);
}

/** Build a GPX route file for one road leg — the `legIndex`-th hop of the
 * `roadIndex`-th drive of day `dayIndex` (all 0-based) — from the geometry the
 * map draws for it. For a leg with no recording of its own; a leg that has one
 * hands back that file instead (no engine call needed).
 *
 * Throws when there is no route to give: the bridge refuses to pass off a
 * straight line between two towns as a route. Usually served from the routing
 * cache the day's map render filled, so it needs no network in that case. */
export function buildLegGpx(
  text: string,
  dayIndex: number,
  roadIndex: number,
  legIndex: number,
): Promise<{ gpx: string; name: string }> {
  return call("legGpx", [text, dayIndex, roadIndex, legIndex]);
}

/** Build the PDF. `maps` overrides the file's `include_maps_in_render` for this
 * export (undefined leaves the file's own setting in force). Address inference
 * and its country scope have no override — they come from the file's `defaults`.
 * Returns the bytes for download. */
export function buildPdf(
  text: string,
  opts: {
    lang?: string;
    inkSaver?: boolean;
    maps?: boolean;
    mapProvider?: string;
  } = {},
): Promise<Uint8Array> {
  return call("build", [
    text,
    opts.lang ?? "en",
    opts.inkSaver ?? false,
    opts.maps ?? null,
    opts.mapProvider ?? "google",
  ]);
}
