import { createContext, useContext } from "react";

// Building a GPX file for a road leg that carries no recording of its own, out
// of the geometry the map draws for it. Provided by App.tsx (bound to the text
// the current preview was resolved from) and consumed by DayCard's leg rows —
// the same shape as the Edit tab's geocode context, and for the same reason: the
// render tree has no business knowing about the Python worker.
//
// Null when unavailable (no file open, or a standalone render of the components
// with no engine behind them), in which case the leg simply offers no link. A
// leg that *does* carry a `gpx` never comes here: that file is already in the
// resolved document, and handing it back needs nothing but the browser.
export interface RouteGpxApi {
  // Resolves to the file text plus a suggested name; rejects when there is no
  // route to give (the bridge refuses to pass a straight line off as one).
  build: (
    dayIndex: number,
    roadIndex: number,
    legIndex: number,
  ) => Promise<{ gpx: string; name: string }>;
  ready: boolean;
}

export const RouteGpxContext = createContext<RouteGpxApi | null>(null);

export function useRouteGpx(): RouteGpxApi | null {
  return useContext(RouteGpxContext);
}
