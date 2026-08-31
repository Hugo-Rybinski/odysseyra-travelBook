// TypeScript types for the *input* itinerary JSON — the shape a user writes and
// the Edit tab edits. This is deliberately distinct from `resolved.ts`, which
// describes the *output* of `resolve()` (inferred times/dates, resolved meal
// categories, converted prices). Here almost everything is optional: the Python
// model fills defaults, so an input object may legitimately omit any field with
// a default. Scalars that the model parses (dates, times, durations, tz offsets)
// are plain strings in the input; prices are bare numbers.
//
// Mirrors the field tables in ../../README.md → "JSON format". Keep the two in
// sync when the schema changes.

export interface SrcCoordinate {
  lat?: number;
  long?: number;
  show_on_map?: boolean;
}

export interface SrcSecondaryCurrency {
  currency?: string;
  change_rate?: number;
}

export interface SrcTravelDescription {
  title?: string;
  subtitle?: string;
  start_date?: string; // YYYY-MM-DD
  end_date?: string;
  cover_color?: string; // #RRGGBB
  summary?: string;
}

export interface SrcDefaults {
  start_time?: string; // HH:MM
  end_time?: string; // HH:MM — where the day's last activity should land (18:00)
  // Size the buffers between a day's activities so the day ends on `end_time`.
  // Defaults to **true**, and supersedes `buffer` rather than stacking with it.
  auto_sized_buffer?: boolean;
  buffer?: string; // duration — fixed buffer, ignored when auto_sized_buffer is on
  timezone?: string; // UTC offset
  breakfast_until?: string; // HH:MM
  lunch_until?: string;
  meal_duration?: string; // duration
  accommodation_start_time?: string; // HH:MM — ICS booking event start
  accommodation_end_time?: string; // HH:MM — ICS booking event end
  currency?: string; // 3-letter ISO
  secondary_currencies?: SrcSecondaryCurrency[];
  include_maps_in_render?: boolean;
  // Draw the trail map + elevation profile of a hike that embeds a `gpx`.
  // Defaults to **true** and is independent of include_maps_in_render.
  include_hike_maps?: boolean;
  infer_coordinates_from_address?: boolean;
  inference_countries?: string[]; // 2-letter ISO codes
  show_moon_phase?: boolean;
  show_sun_times?: boolean;
}

// Scheduling fields shared by every activity except `buffer`.
export interface SrcScheduled {
  start_time?: string;
  end_time?: string;
  duration?: string;
  start_tz?: string;
  end_tz?: string;
}

export interface SrcWaypoint {
  coordinate?: SrcCoordinate;
  location?: string;
  duration?: string;
  distance_km?: number;
  off_road?: boolean; // this leg alone runs off-road
}

export interface SrcRoad extends SrcScheduled {
  type: "road";
  start?: string;
  coordinate?: SrcCoordinate; // the departure point
  distance_km?: number;
  off_road?: boolean;
  description?: string;
  guidebook_pages?: string; // guidebook page(s): "14", "15-18", "16, 23, 25-30"
  waypoints?: SrcWaypoint[];
  activities?: SrcMeal[]; // nested meals only
}

export interface SrcPoi extends SrcScheduled {
  type: "point_of_interest";
  name?: string;
  category?: string;
  address?: string;
  description?: string;
  guidebook_pages?: string; // guidebook page(s): "14", "15-18", "16, 23, 25-30"
  website?: string;
  // When it opens, checked against the visit by the validator. Compact strings:
  // "tue-sun" / "mon-fri, sun", and "09:30-18:00" / "09:30-12:30, 14:00-18:00".
  opening_days?: string;
  opening_hours?: string;
  coordinate?: SrcCoordinate;
  activities?: SrcNestedActivity[]; // poi | hike | meal
}

export interface SrcPlace extends SrcScheduled {
  type: "place";
  name?: string;
  description?: string;
  guidebook_pages?: string; // guidebook page(s): "14", "15-18", "16, 23, 25-30"
  coordinate?: SrcCoordinate;
  activities?: SrcNestedActivity[]; // poi | hike | meal
}

export interface SrcHike extends SrcScheduled {
  type: "hike";
  name?: string;
  description?: string;
  guidebook_pages?: string; // guidebook page(s): "14", "15-18", "16, 23, 25-30"
  distance_km?: number;
  elevation_m?: number;
  start?: string;
  end?: string;
  route?: string;
  // The trail's GPX file, base64-encoded (gzip allowed). Drawn as a trail map
  // plus an elevation profile, and it fills in a missing distance/elevation.
  gpx?: string;
  coordinate?: SrcCoordinate;
  activities?: SrcMeal[]; // nested meals only
}

export interface SrcMeal extends SrcScheduled {
  type: "meal";
  meal_type?: string;
  restaurant?: string;
  area?: string;
  address?: string;
  coordinate?: SrcCoordinate;
}

export interface SrcBuffer {
  type: "buffer";
  duration?: string;
}

// A top-level activity may be any of the six kinds; a *nested* one is restricted
// to poi/hike/meal (the model rejects nested road/place/buffer and deeper
// nesting), but we keep the TS type permissive and let the validator enforce it.
export type SrcActivity = SrcRoad | SrcPoi | SrcPlace | SrcHike | SrcMeal | SrcBuffer;
export type SrcNestedActivity = SrcPoi | SrcHike | SrcMeal;
export type SrcActivityType = SrcActivity["type"];

export interface SrcTransport {
  type?: string;
  start?: string;
  end?: string;
  start_date?: string;
  end_date?: string;
  start_time?: string;
  end_time?: string;
  start_tz?: string;
  end_tz?: string;
  duration?: string;
  flight_number?: string;
  train_number?: string;
  booking_number?: string;
  booking_source?: string;
  website?: string;
  booking_link?: string;
  status?: string;
  description?: string;
  price?: number;
  currency?: string;
  paid?: string | boolean;
  coordinate?: SrcCoordinate;
  start_coordinate?: SrcCoordinate;
  end_coordinate?: SrcCoordinate;
}

export interface SrcAccommodation {
  name?: string;
  arrival?: string;
  departure?: string;
  city?: string;
  type?: string;
  address?: string;
  contact?: string;
  booking_source?: string;
  website?: string;
  booking_link?: string;
  status?: string;
  description?: string;
  price?: number;
  currency?: string;
  paid?: string | boolean;
  breakfast_included?: boolean;
  coordinate?: SrcCoordinate;
}

export interface SrcCarRental {
  booking_start_date?: string;
  booking_start_time?: string;
  booking_end_date?: string;
  booking_end_time?: string;
  pickup_date?: string;
  pickup_time?: string;
  dropoff_date?: string;
  dropoff_time?: string;
  pickup_location?: string;
  dropoff_location?: string;
  booking_start_tz?: string;
  booking_end_tz?: string;
  pickup_tz?: string;
  dropoff_tz?: string;
  company?: string;
  booking_number?: string;
  website?: string;
  booking_link?: string;
  status?: string;
  description?: string;
  price?: number;
  currency?: string;
  paid?: string | boolean;
  car_type?: string;
  car_model?: string;
  contact?: string;
  additional_drivers?: number;
  pickup_duration?: string;
  dropoff_duration?: string;
  pickup_coordinate?: SrcCoordinate;
  dropoff_coordinate?: SrcCoordinate;
}

export interface SrcDay {
  title?: string;
  city?: string;
  date?: string;
  description?: string;
  bank_holiday?: boolean;
  activities?: SrcActivity[];
}

export interface SrcItinerary {
  travel_description?: SrcTravelDescription;
  defaults?: SrcDefaults;
  days?: SrcDay[];
  transport?: SrcTransport[];
  accommodations?: SrcAccommodation[];
  car_rentals?: SrcCarRental[];
}
