// TypeScript types for the *input* itinerary JSON — the shape a user writes and
// the Edit tab edits. This is deliberately distinct from `resolved.ts`, which
// describes the *output* of `resolve()` (inferred times/dates, resolved meal
// categories, converted prices). Here almost everything is optional: the Python
// model fills defaults, so an input object may legitimately omit any field with
// a default. Scalars that the model parses (dates, times, durations, tz offsets)
// are plain strings in the input; prices are bare numbers.
//
// Mirrors the field tables in ../../file_format.md. Keep the two in sync when
// the schema changes.

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
  // A stop you probably won't make but want the book to carry anyway. It is
  // left off the timeline — no minutes, no buffer before it — and shows its
  // duration without a clock time, so a `start_time`/`end_time` written here is
  // dropped (their span becomes the duration). Defaults to false.
  detour?: boolean;
  // What the stop costs: an entrance fee, a guided visit, a meal. A bare number
  // with no symbol; `currency` defaults to `defaults.currency`. 0 is meaningful
  // and prints as "Free". There is no `paid` — a fee at the gate has nothing to
  // settle in advance.
  price?: number;
  currency?: string; // 3-letter ISO
  // Whether this activity draws its **own** map: a `place`'s zoomed area map,
  // a `hike`'s trail map. Those are the only two that have one, so it does
  // nothing on the other types. Defaults to true. Not `coordinate.show_on_map`,
  // which is the reverse — that hides this activity's pin on a map drawn by
  // something else.
  show_map?: boolean;
  // A phone number, email, or how to get in. Free text, never parsed.
  contact?: string;
}

// One hop of a drive. Either endpoint may be left out when the neighbouring leg
// states it (`start_*` falls back to the previous leg's `end_*` and vice versa),
// so a junction is written once; the first leg must name its departure and the
// last its arrival. `waypoints` are bare coordinates that bend this hop's route
// — a stop worth naming, or a stretch worth timing, is a leg of its own.
export interface SrcRoadLeg {
  start_location?: string;
  start_coordinate?: SrcCoordinate;
  end_location?: string;
  end_coordinate?: SrcCoordinate;
  duration?: string;
  distance_km?: number;
  off_road?: boolean; // this hop alone runs off-road
  waypoints?: SrcCoordinate[]; // in order, from the hop's start to its end
  // A recording of this hop, base64 (gzip allowed) — stored exactly like a
  // hike's `gpx`, but used differently: it becomes this leg's line on the day
  // map instead of the routed guess, and it is never drawn as a map + profile
  // of its own.
  gpx?: string;
}

export interface SrcRoad extends SrcScheduled {
  type: "road";
  distance_km?: number; // the whole drive (each leg carries its own too)
  // Which of the drive's own points get a numbered pin on the day map: its
  // departure, its final arrival, and every junction between two legs. The two
  // ends default false — they are usually the activity before/after, already
  // pinned. The junctions default **true**: splitting the drive there is what
  // says the point matters, and nothing else on the page identifies it.
  display_start_on_maps?: boolean;
  display_end_on_maps?: boolean;
  display_intermediate_point_on_maps?: boolean;
  // That end of the drive *is* the neighbouring activity's place: you drive away
  // from the museum you just visited, and on to the hotel listed next. The
  // matching leg endpoint may then be left blank (it is filled in from that
  // activity), and that end shares the activity's map pin rather than taking a
  // second number for the same place — which is worth setting even when the
  // endpoint is spelled out. Both default false.
  same_start_as_previous_activity?: boolean;
  same_end_as_next_activity?: boolean;
  description?: string;
  guidebook_pages?: string; // guidebook page(s): "14", "15-18", "16, 23, 25-30"
  // Required and non-empty: one entry per hop. A plain A → B drive has one.
  // The departure, the arrival and the route all live here, which is why a road
  // has no `start` / `coordinate` / `waypoints` / `off_road` of its own.
  legs?: SrcRoadLeg[];
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
  // The hours may also differ by weekday, as ";"-separated groups each
  // optionally prefixed with its days: "mon-sat 09:00-17:00; sun 10:00-17:00".
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

// One hop of a booking: where it goes, when, and the number of that hop. The
// reservation fields (type, reference, price, links, status) live on the parent
// booking, not here.
export interface SrcTransportLeg {
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
  distance_km?: number; // how far this hop covers
  description?: string;
  coordinate?: SrcCoordinate;
  start_coordinate?: SrcCoordinate;
  end_coordinate?: SrcCoordinate;
}

export interface SrcTransport {
  type?: string;
  // What the booking is called as a whole. Defaults to the route chain through
  // its legs ("A → B → C → D").
  name?: string;
  // A note about the whole reservation (a leg's own note is on the leg).
  description?: string;
  booking_number?: string;
  booking_source?: string;
  website?: string;
  booking_link?: string;
  status?: string;
  price?: number;
  currency?: string;
  paid?: string | boolean;
  // Required and non-empty: one entry per hop. A single-hop booking has one.
  legs?: SrcTransportLeg[];
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
  // Whether the day draws its overview map (and the numbered pins its activity
  // titles refer to), when the trip renders maps at all. Defaults to true. An
  // activity's own map has its own `show_map`, and the whole-trip map keeps the
  // day either way.
  show_map?: boolean;
  activities?: SrcActivity[];
}

// One emergency contact, and the `misc` group holding them. Both halves are
// optional and free text; an entry with neither is dropped by the model.
export interface SrcEmergencyContact {
  name?: string;
  contact?: string;
}

// Trip-wide reference data that sits nowhere on the timeline. Unlike
// `travel_description` / `defaults`, its keys are *not* also read from the top
// level — see models/misc.py.
export interface SrcMisc {
  emergency_contacts?: SrcEmergencyContact[];
}

export interface SrcItinerary {
  travel_description?: SrcTravelDescription;
  defaults?: SrcDefaults;
  misc?: SrcMisc;
  days?: SrcDay[];
  transport?: SrcTransport[];
  accommodations?: SrcAccommodation[];
  car_rentals?: SrcCarRental[];
}
