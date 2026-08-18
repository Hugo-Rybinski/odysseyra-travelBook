// TypeScript mirror of the resolved-model dict emitted by
// `travelbook.models.to_dict` (see src/travelbook/models/serialize.py). This is
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
  duration_min: number | null;
  duration_display: string;
  distance_km: number | null;
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
  waypoints?: Waypoint[];
  // road / hike
  distance_km?: number | null;
  // hike
  elevation_m?: number | null;
  end?: string;
  route?: string;
  route_label?: string;
  // poi / place / hike
  name?: string;
  description?: string;
  // poi
  address?: string;
  category?: string; // poi category, or the resolved meal category
  website?: string;
  // meal
  restaurant?: string;
  area?: string;
  meal_type?: string;
}

export interface Transport extends Scheduled {
  type: string;
  title: string;
  start: string; // departure place name
  end: string; // arrival place name
  start_date: string | null;
  end_date: string | null;
  overnight: boolean;
  end_day_offset: number;
  flight_number: string;
  train_number: string;
  booking_number: string;
  booking_source: string;
  website: string;
  booking_link: string;
  status: string;
  price: Money | null;
  coordinate: Coordinate | null;
  start_coordinate: Coordinate | null;
  end_coordinate: Coordinate | null;
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
  price: Money | null;
  breakfast_included: boolean;
  coordinate: Coordinate | null;
  map_pin?: string | null; // "*" on the day map when this is the night's stay
}

// A rendered day map (a base64 PNG data URI) plus its pin-ordered legend.
export interface RenderedMap {
  image: string; // data:image/png;base64,…
  legend: string[]; // activity titles in pin order
}

// Per-day maps inlined by the bridge when the itinerary opts into maps: the main
// overview map and, per area with nested points, a zoomed detail map.
export interface DayMap {
  main: RenderedMap | null;
  areas: (RenderedMap & { title: string })[];
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
  activities: Activity[];
  transports: Transport[];
  car_events: CarEvent[];
  stay: Accommodation | null;
  stay_night: number | null; // 1-based night index within the stay
  night_transport: Transport | null;
  sleep_city: string;
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
    infer_from_address: boolean;
    inference_countries: string[];
  };
  days: Day[];
  transports: Transport[];
  accommodations: Accommodation[];
  car_rentals: CarRental[];
}

export type FindingLevel = "error" | "warning" | "info";

export interface Finding {
  level: FindingLevel;
  line: number | null;
  message: string;
}
