import { createContext, useContext } from "react";

// Geocoding for the Edit tab's coordinate fields (P5). Provided by EditPanel
// (bound to the draft's inference_countries) and consumed by CoordinateField.
// Null when unavailable; `ready` is false while the engine is starting or the
// device is offline (Nominatim needs the network).
export interface GeocodeApi {
  geocode: (query: string) => Promise<{ lat: number; long: number } | null>;
  ready: boolean;
}

export const EditGeocodeContext = createContext<GeocodeApi | null>(null);

export function useGeocode(): GeocodeApi | null {
  return useContext(EditGeocodeContext);
}
