// TypeScript mirror of the resolved-model dict emitted by
// `odysseyra_travelbook.models.to_dict` (see src/odysseyra_travelbook/models/serialize.py). This is
// the single contract the UI renders from — every value here is already
// resolved by the Python model (inferred times/dates, meal categories,
// converted prices). Kept intentionally close to the Python shape.
//
// Phase 1 only needs a slice of this, but the full shape is declared up front so
// later phases (rendering, export) build against a stable type.

export interface Coordinate {
  lat: number;
  long: number;
  show_on_map: boolean;
}

export interface Money {
  amount: number;
  currency: string;
  default_currency: string;
  in_default: number | null; // converted to the trip default; null if unknown rate
  secondaries: { currency: string; amount: number }[];
  paid: boolean | null; // paid / to-pay / unset
}

// Shared timeline fields. UTC offsets are `start_tz`/`end_tz` (integer minutes,
// nullable) with a display label — never `start`/`end`, which are place names.
export interface Scheduled {
  start_time: string | null; // "HH:MM"
  end_time: string | null;
  duration_min: number | null;
  duration_display: string;
  time_range: string;
  start_tz: number | null;
  start_tz_label: string;
  end_tz: number | null;
  end_tz_label: string;
}

export interface Waypoint {
  coordinate: Coordinate | null;
  location: string;
  // duration / distance / off_road / gpx all describe the leg *reaching* this
  // waypoint
  duration_min: number | null;
  duration_display: string;
  distance_km: number | null;
  // Optional: a day cached before per-leg off-road existed has none.
  off_road?: boolean;
  // This point's map pin label, when the road asked for pins on its own points
  // (see the road's display_*_on_maps below) and maps were rendered. Null/absent
  // otherwise — which is the normal case, since all three switches default off.
  map_pin?: string | null;
  // The leg's recorded track, base64, exactly as it was attached — all the
  // browser needs it for is the "(Get GPX track)" download. There is no
  // geometry or profile here on purpose: a leg's recording is drawn as the
  // route on the day map (the map render carries it), never as a figure of its
  // own, which is what makes it unlike a hike's `track`.
  gpx?: string | null;
}

// A hike's embedded GPX, reduced by the Python model (models/gpx.py) to what
// gets drawn: the simplified trail line, the resampled elevation profile, and
// the figures measured off the *full*-resolution recording. Present only when
// the hike carries a `gpx` and `defaults.include_hike_maps` is on (it defaults
// on) — the base64 blob itself never reaches the browser.
export interface HikeTrack {
  // The original file, base64 (and possibly gzipped), exactly as the itinerary
  // carries it — this is what the "(Get GPX track)" link hands back, so the
  // download is the bytes that were attached rather than a re-export of the
  // simplified line below. Optional: a day cached before the link existed has
  // the geometry but not the file.
  gpx?: string;
  points: [number, number][]; // [lat, long] along the trail, in walking order
  profile: [number, number][]; // [km walked, elevation m]; empty without elevations
  distance_km: number;
  ascent_m: number | null; // null when the file carries no elevations
  descent_m: number | null;
  min_elevation_m: number | null;
  max_elevation_m: number | null;
  point_count: number; // points in the source file, before simplification
  bounds: [[number, number], [number, number]]; // [[minLat,minLong],[maxLat,maxLong]]
}

// A point of interest's opening days and hours (its `opening_days` /
// `opening_hours`), reduced by the Python model (models/opening.py). Either half
// may be empty: no days means every day, no hours means all day — an object that
// says neither is never emitted (the field is null instead).
export interface Opening {
  days: string[]; // canonical lowercase weekday names, week order
  // `days` already folded into consecutive [first, last] runs, so the viewer
  // only names the weekdays (see fmtWeekdayRuns) rather than re-deriving them.
  day_runs: [string, string][];
  hours: [string, string][]; // ["09:30", "12:30"] open/close pairs, in order
  hours_display: string; // "09:30–12:30, 14:00–18:00" — digits only, so shared
}

export type ActivityType =
  | "road"
  | "point_of_interest"
  | "place"
  | "hike"
  | "meal"
  | "buffer";

export interface Activity extends Scheduled {
  type: ActivityType;
  title: string;
  coordinate: Coordinate | null;
  map_pin: string | null; // pin label on the day map (number / area letter), when maps ran
  activities?: Activity[]; // one level of nesting

  // buffer
  auto?: boolean;
  // road: `start` is the departure place name, `destination` the arrival
  start?: string;
  destination?: string;
  off_road?: boolean;
  // Which of the drive's own points earn a numbered pin on the day map — the
  // departure (the road's own `map_pin`), the final arrival, and the junctions
  // in between (each on its waypoint). The two ends default off, the junctions
  // **on**; a day cached before v18 carries none of them.
  display_start_on_maps?: boolean;
  display_end_on_maps?: boolean;
  display_intermediate_point_on_maps?: boolean;
  waypoints?: Waypoint[];
  // road / hike
  distance_km?: number | null;
  // hike
  elevation_m?: number | null;
  end?: string;
  route?: string;
  route_label?: string;
  // The embedded GPX track (see HikeTrack). Optional/null: most hikes have no
  // `gpx`, and a day cached before the field existed has none either.
  track?: HikeTrack | null;
  // poi / place / hike
  name?: string;
  // road / poi / place / hike — free prose for whatever the other fields don't
  // carry (a road's is drawn above its VIA legs, in both renderers)
  description?: string;
  // road / poi / place / hike — the guidebook page(s) covering it ("14",
  // "15-18", "16, 23, 25-30"), drawn under the description in a light accent.
  // Optional: a day cached before the field existed has none.
  guidebook_pages?: string;
  // poi
  address?: string;
  category?: string; // poi category, or the resolved meal category
  website?: string;
  // poi — when it opens, drawn under the address. Optional/null: most sights
  // state none, and a day cached before the field existed has none either.
  opening?: Opening | null;
  // meal
  restaurant?: string;
  area?: string;
  meal_type?: string;
}

// One hop of a booking — what a day is actually moved by, and so what the day
// pages, the maps and the calendar export deal with. Everything from
// `leg_index` down is **its booking's**, copied on by the Python serializer
// (models/serialize.py's `_transport_leg`) so a leg shown away from its booking
// still has its type badge, reference and links.
export interface TransportLeg extends Scheduled {
  title: string;
  start: string; // departure place name
  end: string; // arrival place name
  start_date: string | null;
  end_date: string | null;
  overnight: boolean;
  end_day_offset: number;
  flight_number: string;
  train_number: string;
  // A short note for whatever the fields above don't carry (a seat, a terminal).
  // Per-leg — an outbound and a return rarely share one.
  description?: string;
  coordinate: Coordinate | null;
  start_coordinate: Coordinate | null;
  end_coordinate: Coordinate | null;
  // --- from the parent booking ---
  leg_index: number; // 1-based within the booking
  leg_count: number; // 1 for a single-hop booking
  type: string;
  booking_number: string;
  booking_source: string;
  website: string;
  booking_link: string;
  status: string;
  // The **whole booking's** price, every leg included — never draw it per leg
  // (a two-leg round trip would show its fare twice). The transport page draws
  // it once, on the booking.
  price: Money | null;
}

// A booking: one reservation (a PNR, a price, a link) and the legs it moves you
// over. `legs` always holds at least one entry — a single-hop booking is a
// one-leg booking, not a separate shape.
export interface Transport {
  type: string;
  // What to call the booking as a whole ("Round trip New York ↔ France").
  // Optional in the source; "" when unset — use `title`, which falls back to
  // `route_chain`.
  name: string;
  title: string; // `name` when set, else `route_chain`
  // Every place the booking touches, in travel order ("A → B → C → D"), a
  // connection named once. This is the default heading when there's no `name`.
  route_chain: string;
  // A note about the whole reservation (a baggage allowance, a fare condition)
  // — distinct from a leg's `description`, which is about that hop. Shown in
  // the transport section only, never on a day's row.
  description: string;
  start_date: string | null; // earliest departure across the legs
  end_date: string | null; // latest arrival across the legs
  booking_number: string;
  booking_source: string;
  website: string;
  booking_link: string;
  status: string;
  price: Money | null;
  legs: TransportLeg[];
}

export interface Accommodation {
  name: string;
  arrival: string | null;
  departure: string | null;
  nights: number | null;
  date_range: string;
  city: string;
  type: string;
  address: string;
  contact: string;
  booking_source: string;
  website: string;
  booking_link: string;
  status: string;
  description?: string; // short note; see TransportLeg.description
  price: Money | null;
  breakfast_included: boolean;
  coordinate: Coordinate | null;
  map_pin?: string | null; // ★ on the day map when this is the night's stay
}

// A rendered day map (a base64 PNG data URI) plus its pin-ordered legend.
export interface RenderedMap {
  image: string; // data:image/png;base64,…
  legend: string[]; // activity titles in pin order
}

// A located point for the interactive map: coordinates + its pin label + title.
export interface MapPoint {
  lat: number;
  long: number;
  label: string; // "1".."N", "★" (stay), or "A".."Z" (area)
  title: string;
}

// Structured geo for the interactive (MapLibre) day map — the same points,
// routes and areas the static PNG is drawn from, as data the browser can render.
export interface MapGeo {
  points: MapPoint[];
  routes: [number, number][][]; // [lat, long] polylines (drives)
  route_nodes: [number, number][]; // [lat, long] named stops on the routes
  // [origin, destination] pairs for transport legs, drawn as dotted straight
  // lines. Optional: a day map cached in IndexedDB before legs existed has none.
  legs?: [number, number][][];
  areas: {
    title: string;
    points: MapPoint[];
    bounds: [[number, number], [number, number]]; // area's own extent
  }[];
  accent: string; // "#rrggbb"
  bounds: [[number, number], [number, number]]; // [[minLat,minLong],[maxLat,maxLong]]
}

// Per-day maps inlined by the bridge when the itinerary opts into maps: the main
// overview map and, per area with nested points, a zoomed detail map; plus the
// structured `geo` the interactive map renders from.
export interface DayMap {
  main: RenderedMap | null;
  areas: (RenderedMap & { title: string })[];
  geo?: MapGeo | null;
}

export interface Stamp {
  date: string | null;
  time: string | null;
  tz: number | null;
  tz_label: string;
}

export interface CarEvent extends Scheduled {
  kind: "car_pickup" | "car_dropoff";
  date: string | null;
  location: string;
  rental_title: string;
  company: string;
  car_model: string;
  car_type_label: string;
  booking_number: string;
  // The owning rental's note, carried onto the event (which has no way back to
  // its rental). See CarRental.description.
  description?: string;
  coordinate: Coordinate | null;
}

export interface CarRental {
  title: string;
  company: string;
  booking_start: Stamp;
  booking_end: Stamp;
  pickup: Stamp;
  dropoff: Stamp;
  pickup_location: string;
  dropoff_location: string;
  booking_number: string;
  website: string;
  booking_link: string;
  status: string;
  description?: string; // short note; see TransportLeg.description
  price: Money | null;
  car_type: string;
  car_type_label: string;
  car_model: string;
  contact: string;
  additional_drivers: number;
  pickup_duration_min: number | null;
  pickup_duration_display: string;
  dropoff_duration_min: number | null;
  dropoff_duration_display: string;
  coordinate: Coordinate | null;
  pickup_coordinate: Coordinate | null;
  dropoff_coordinate: Coordinate | null;
}

export interface Day {
  day_number: number;
  title: string;
  date: string | null;
  city: string;
  description: string;
  // A public holiday where you are that day: the day opens with a call-out
  // banner. Optional — a doc resolved before the flag existed carries none.
  bank_holiday?: boolean;
  activities: Activity[];
  // The legs departing that day (not the bookings), each enriched with its
  // booking's shared fields.
  transports: TransportLeg[];
  car_events: CarEvent[];
  stay: Accommodation | null;
  stay_night: number | null; // 1-based night index within the stay
  night_transport: TransportLeg | null;
  sleep_city: string;
  // The night's moon phase, present unless defaults.show_moon_phase is off (it
  // defaults on).
  // `key` is a format.ts label key; `name` is the English fallback.
  moon: { key: string; emoji: string; name: string } | null;
  // The day's sunrise/sunset, present unless defaults.show_sun_times is off (it
  // defaults on) or there's no coordinate to compute them for. Just the clock
  // times: the display string is built from the localized `sunTimes` template
  // (render/format.ts), mirroring the PDF's. The sunrise is computed where you
  // woke, the sunset where you'll sleep — see the README.
  // Optional: a doc resolved before sun times existed has none.
  sun?: { sunrise: string; sunset: string } | null;
  map?: DayMap; // inlined when the itinerary opts into maps
}

export interface Itinerary {
  title: string;
  subtitle: string;
  summary: string;
  cover_color: string;
  start_date: string | null;
  end_date: string | null;
  date_range: string;
  day_count: number;
  default_currency: string;
  secondary_currencies: { currency: string; change_rate: number }[];
  timezone: number;
  timezone_label: string;
  maps: {
    include_in_render: boolean;
    // Draw a hike's trail map + elevation profile from its `gpx`. Defaults on
    // and independent of `include_in_render`. Optional: a doc resolved before
    // the switch existed has none (treat a missing value as on).
    include_hike_maps?: boolean;
    infer_from_address: boolean;
    inference_countries: string[];
  };
  // The `misc` group, flattened by serialize.py the same way `defaults` is.
  // Optional: a doc resolved before the group existed carries none.
  emergency_contacts?: EmergencyContact[];
  days: Day[];
  transports: Transport[];
  accommodations: Accommodation[];
  car_rentals: CarRental[];
}

// One of `misc.emergency_contacts`. Both halves are optional and free text —
// see models/misc.py; a renderer draws whichever half it is given.
export interface EmergencyContact {
  name: string;
  contact: string;
}

export type FindingLevel = "error" | "warning" | "info";

export interface Finding {
  level: FindingLevel;
  line: number | null;
  message: string;
}
