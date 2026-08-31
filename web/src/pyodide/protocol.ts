// The contract between the UI thread and the Pyodide engine, shared by
// `runtime.ts` (the client), `worker.ts` (the host) and `engine.ts` (the
// implementation). Kept in its own module so the worker bundle doesn't pull in
// anything React-side, and so the operation names/arguments/results are typed
// once for both ends of the postMessage boundary.
import type { Day, Finding, Itinerary } from "../types/resolved";

export type Stage =
  | "idle"
  | "loading-runtime"
  | "installing-packages"
  | "installing-odysseyra"
  | "ready"
  | "error";

export interface BootProgress {
  stage: Stage;
  detail?: string;
}

/** Every call the UI can make into Python, with its arguments and result. The
 * arguments are positional (they cross postMessage as a plain array) and must
 * stay structured-cloneable — no functions, no class instances. */
export interface OpMap {
  validate: { args: [text: string, lang: string]; result: Finding[] };
  resolve: { args: [text: string]; result: Itinerary };
  renderDay: { args: [text: string, index: number]; result: Day };
  geocode: {
    args: [query: string, countries: string];
    result: { lat: number; long: number } | null;
  };
  ics: { args: [text: string, lang: string]; result: string };
  build: {
    args: [
      text: string,
      lang: string,
      inkSaver: boolean,
      maps: boolean | null,
      mapProvider: string,
    ];
    result: Uint8Array;
  };
}

export type Op = keyof OpMap;
export type OpArgs<O extends Op> = OpMap[O]["args"];
export type OpResult<O extends Op> = OpMap[O]["result"];

/** The engine's one entry point, implemented in `engine.ts` and reached either
 * directly (fallback) or over postMessage (normal path). */
export type EngineCall = <O extends Op>(op: O, args: OpArgs<O>) => OpResult<O>;

export type ToWorker =
  | { kind: "boot"; id: number }
  | { kind: "call"; id: number; op: Op; args: unknown[] };

export type FromWorker =
  | { kind: "progress"; progress: BootProgress }
  | { kind: "ok"; id: number; value: unknown }
  | { kind: "err"; id: number; error: string };
