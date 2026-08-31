// The Pyodide host: a **module** worker (it needs a native dynamic import for
// pyodide.mjs — see engine.ts) that owns the one Python interpreter and answers
// the UI's RPCs.
//
// Why a worker at all: every engine call is synchronous Python, and the maps
// code fetches tiles over a *blocking* XHR (netbridge.ts). On the main thread
// that froze the whole page — no repaint, no spinner, no scrolling — for the
// length of a PDF build or a day's map. Here it blocks only this thread, so the
// UI stays live and can show a loader (see ActivityIndicator).
//
// The protocol is one message per call (see protocol.ts). Calls are answered in
// arrival order and never overlap: Python is single-threaded, so a `build` in
// progress simply delays the next `validate` rather than interleaving with it.
import { bootEngine, type Engine } from "./engine";
import type { FromWorker, Op, OpArgs, ToWorker } from "./protocol";

// The worker globals, typed locally. The project's tsconfig ships the DOM lib
// (it's a React app), so TypeScript sees `self` as a Window here; pulling in
// `lib: webworker` for one file would collide with DOM's globals, and this
// two-member shape is all we use.
interface WorkerScope {
  postMessage(message: FromWorker, transfer?: Transferable[]): void;
  onmessage: ((event: MessageEvent<ToWorker>) => void | Promise<void>) | null;
}
const ctx = self as unknown as WorkerScope;

const post = (msg: FromWorker, transfer: Transferable[] = []) =>
  ctx.postMessage(msg, transfer);

let engine: Engine | null = null;
let booting: Promise<Engine> | null = null;

/** Boot once; every caller shares the one in-flight boot. */
function ready(): Promise<Engine> {
  booting ??= bootEngine((progress) => post({ kind: "progress", progress })).then((e) => {
    engine = e;
    return e;
  });
  return booting;
}

ctx.onmessage = async (event: MessageEvent<ToWorker>) => {
  const msg = event.data;
  try {
    const eng = engine ?? (await ready());
    if (msg.kind === "boot") return post({ kind: "ok", id: msg.id, value: null });
    const value = eng.call(msg.op as Op, msg.args as OpArgs<Op>);
    // The PDF's bytes are handed over rather than copied — the engine already
    // copied them out of the wasm heap, so this buffer is ours to give away.
    if (value instanceof Uint8Array) {
      return post({ kind: "ok", id: msg.id, value }, [value.buffer]);
    }
    post({ kind: "ok", id: msg.id, value });
  } catch (err) {
    // A failed boot must not be cached: clear it so the next call retries.
    if (!engine) booting = null;
    post({ kind: "err", id: msg.id, error: String(err) });
  }
};
