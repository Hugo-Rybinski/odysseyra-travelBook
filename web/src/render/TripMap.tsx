import { lazy, Suspense, useCallback, useEffect, useMemo, useState } from "react";
import type { Itinerary } from "../types/resolved";
import { fill, tr, type Lang, type LabelKey } from "./format";
import { MapErrorBoundary } from "./MapErrorBoundary";
import { tripGeo } from "./tripGeo";

// Same lazy chunk as the day maps (MapLibre is heavy and precached separately).
const DayMapGL = lazy(() => import("./DayMapGL").then((m) => ({ default: m.DayMapGL })));

// One map of the whole trip (Overview tab): every day's located points, pinned
// with their day number, plus the real drive geometry of the days whose map has
// been rendered — see tripGeo.ts.
//
// Interactive-only: unlike a day map there's no pre-rendered PNG to fall back
// to, so a failure (offline & uncached, tiles blocked) shows a note instead. The
// geo is rebuilt as the per-day maps stream in, which remounts the map; that
// only happens while the initial map build is running.
export function TripMap({ itinerary, lang }: { itinerary: Itinerary; lang: Lang }) {
  const trip = useMemo(() => tripGeo(itinerary, lang), [itinerary, lang]);
  const [failed, setFailed] = useState(false);
  const [mapKey, setMapKey] = useState(0);
  const onFail = useCallback(() => setFailed(true), []);
  // Fresh geo (a day's map landed) is worth a retry after a failure; the key
  // remounts the error boundary, which latches its own caught-error state.
  useEffect(() => {
    setFailed(false);
    setMapKey((k) => k + 1);
  }, [trip]);

  const note = (key: LabelKey) => <p className="section-empty">{tr(lang, key)}</p>;

  if (!trip) return note("noTripMap");
  if (failed) return note("tripMapUnavailable");

  // Far-off pins and drives are still on the map but outside its initial view;
  // name the farthest so they're discoverable rather than silently off-screen.
  const { outliers } = trip;

  return (
    <div className="trip-map">
      <MapErrorBoundary key={mapKey} onError={onFail} fallback={note("tripMapUnavailable")}>
        <Suspense
          fallback={
            <div className="day-map-loading" role="status" aria-live="polite">
              <span className="spin" aria-hidden />
              {tr(lang, "buildingMap")}
            </div>
          }
        >
          <DayMapGL geo={trip.geo} caption={tr(lang, "tripMapCaption")} onFail={onFail} />
        </Suspense>
      </MapErrorBoundary>
      {outliers.length > 0 && (
        <p className="trip-map-note">
          {fill(tr(lang, outliers.length > 1 ? "tripMapOutliers" : "tripMapOutlier"), {
            example: outliers[0],
            n: outliers.length - 1,
          })}
        </p>
      )}
    </div>
  );
}
