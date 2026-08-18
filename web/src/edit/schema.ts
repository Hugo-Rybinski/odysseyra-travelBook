// The field registry: a data description of every editable field, driven by the
// README "JSON format" tables. Forms render from these descriptors so the schema
// lives in one place — adding/renaming a field is a change here (plus the TS type
// in types/source.ts) rather than in every form component.
//
// `placeholder` carries the format/default hint (shown as the input placeholder);
// `help` is a longer tooltip. `NEW_*` are the stubs the "Add" buttons insert.

import type {
  SrcAccommodation,
  SrcActivity,
  SrcActivityType,
  SrcCarRental,
  SrcDay,
  SrcMeal,
  SrcSecondaryCurrency,
  SrcTransport,
  SrcWaypoint,
} from "../types/source";

export type FieldKind =
  | "text"
  | "textarea"
  | "number"
  | "integer"
  | "date"
  | "time"
  | "duration"
  | "tz"
  | "enum"
  | "color"
  | "bool"
  | "paid"
  | "csv" // comma-separated string[] (e.g. inference_countries)
  | "coordinate";

export interface FieldSpec {
  key: string;
  label: string;
  kind: FieldKind;
  enum?: readonly string[];
  placeholder?: string; // default / format hint
  help?: string;
  required?: boolean;
}

// ---------------------------------------------------------------- enum tables
export const ACTIVITY_TYPES = [
  "road",
  "point_of_interest",
  "place",
  "hike",
  "meal",
  "buffer",
] as const;

// Nested activities are restricted by container; these are the ones we offer to
// add inside a place/poi (poi|hike|meal) vs a road/hike (meal only).
export const NESTED_TYPES_POI = ["point_of_interest", "hike", "meal"] as const;
export const NESTED_TYPES_MEAL_ONLY = ["meal"] as const;

export const POI_CATEGORIES = [
  "museum",
  "church",
  "building",
  "viewpoint",
  "ruins",
  "castle",
  "temple",
  "street",
  "natural park",
  "mountain",
  "lake",
  "beach",
  "waterfall",
  "other",
] as const;
export const HIKE_ROUTES = ["loop", "back_and_forth", "one_way"] as const;
export const TRANSPORT_TYPES = ["plane", "train", "bus", "taxi", "ferry", "other"] as const;
export const ACCOMMODATION_TYPES = ["hotel", "camping", "b&b", "other"] as const;
export const CAR_TYPES = ["regular", "small", "SUV", "4x4"] as const;
export const MEAL_TYPES = [
  "breakfast",
  "lunch",
  "dinner",
  "brunch",
  "snack",
  "picnic",
  "meal",
] as const;
export const STATUSES = ["booked", "confirmed"] as const;

export const ACTIVITY_TYPE_LABELS: Record<SrcActivityType, string> = {
  road: "Road / drive",
  point_of_interest: "Point of interest",
  place: "Place",
  hike: "Hike",
  meal: "Meal",
  buffer: "Buffer",
};

// ------------------------------------------------------------- field tables
export const TRAVEL_DESCRIPTION_FIELDS: FieldSpec[] = [
  { key: "title", label: "Title", kind: "text", required: true, placeholder: "Trip title (shown on the cover)" },
  { key: "subtitle", label: "Subtitle", kind: "text", placeholder: "Line under the title" },
  { key: "start_date", label: "Start date", kind: "date", placeholder: "inferred (earliest date)" },
  { key: "end_date", label: "End date", kind: "date", placeholder: "inferred (latest date)" },
  { key: "cover_color", label: "Cover color", kind: "color", placeholder: "#1f4e5f" },
  { key: "summary", label: "Summary", kind: "textarea", placeholder: "Paragraph shown on the cover" },
];

export const DEFAULTS_FIELDS: FieldSpec[] = [
  { key: "start_time", label: "Start time", kind: "time", placeholder: "08:00", help: "First activity's start time each day" },
  { key: "end_time", label: "End time", kind: "time", placeholder: "none (no check)", help: "Latest an activity should end (validation warns past it)" },
  { key: "buffer", label: "Buffer", kind: "duration", placeholder: "0 (no buffer)", help: "Buffer auto-inserted between consecutive activities" },
  { key: "timezone", label: "Time zone", kind: "tz", placeholder: "GMT", help: "Default UTC offset (+02:00, UTC-3, Z)" },
  { key: "breakfast_until", label: "Breakfast until", kind: "time", placeholder: "10:00", help: "A meal starting before this is inferred as breakfast" },
  { key: "lunch_until", label: "Lunch until", kind: "time", placeholder: "16:00", help: "A meal up to this (after breakfast) is lunch; later, dinner" },
  { key: "meal_duration", label: "Meal duration", kind: "duration", placeholder: "0 (instant)", help: "Default length of a meal with no duration/end time" },
  { key: "currency", label: "Currency", kind: "text", placeholder: "EUR", help: "3-letter ISO code every price is in unless it sets its own" },
  { key: "include_maps_in_render", label: "Include maps in render", kind: "bool", help: "Draw a per-day map with a pin for each located activity" },
  { key: "infer_coordinates_from_address", label: "Infer coordinates from address", kind: "bool", help: "Geocode activities lacking an explicit coordinate" },
  { key: "inference_countries", label: "Inference countries", kind: "csv", placeholder: "FR, ES", help: "Restrict geocoding to these 2-letter ISO codes" },
];

export const SECONDARY_CURRENCY_FIELDS: FieldSpec[] = [
  { key: "currency", label: "Currency", kind: "text", required: true, placeholder: "USD" },
  { key: "change_rate", label: "Rate", kind: "number", required: true, placeholder: "units per 1 default (1 € = 1.09 $ → 1.09)" },
];

export const DAY_FIELDS: FieldSpec[] = [
  { key: "title", label: "Title", kind: "text", required: true, placeholder: "The day's title" },
  { key: "city", label: "City", kind: "text", placeholder: "City/region label" },
  { key: "date", label: "Date", kind: "date", placeholder: "trip start + the day's index" },
  { key: "description", label: "Description", kind: "textarea", placeholder: "Intro paragraph for the day" },
];

// Shared scheduling fields (all activities except buffer).
export const SCHEDULED_FIELDS: FieldSpec[] = [
  { key: "start_time", label: "Start time", kind: "time", placeholder: "previous item's end / defaults.start_time" },
  { key: "end_time", label: "End time", kind: "time", placeholder: "start + duration" },
  { key: "duration", label: "Duration", kind: "duration", placeholder: "1h30 / 45 min" },
  { key: "start_tz", label: "Start tz", kind: "tz", placeholder: "defaults.timezone" },
  { key: "end_tz", label: "End tz", kind: "tz", placeholder: "defaults.timezone" },
];

// Per-activity-type fields (excluding the shared scheduling ones and nested
// `activities`/`waypoints`/`coordinate`, which the form renders specially).
export const ACTIVITY_FIELDS: Record<SrcActivityType, FieldSpec[]> = {
  road: [
    { key: "start", label: "Start (departure)", kind: "text", required: true, placeholder: "Departure address" },
    { key: "distance_km", label: "Distance (km)", kind: "number", placeholder: "driving distance" },
    { key: "off_road", label: "Off-road", kind: "bool", help: "Highlight off-road sections" },
  ],
  point_of_interest: [
    { key: "name", label: "Name", kind: "text", required: true, placeholder: "Point-of-interest name" },
    { key: "category", label: "Category", kind: "enum", enum: POI_CATEGORIES, placeholder: "other" },
    { key: "address", label: "Address", kind: "text" },
    { key: "description", label: "Description", kind: "textarea" },
    { key: "website", label: "Website", kind: "text", placeholder: "https://example.com" },
  ],
  place: [
    { key: "name", label: "Name", kind: "text", required: true, placeholder: "Place name" },
    { key: "description", label: "Description", kind: "textarea" },
  ],
  hike: [
    { key: "name", label: "Name", kind: "text", required: true, placeholder: "Hike name" },
    { key: "description", label: "Description", kind: "textarea" },
    { key: "distance_km", label: "Distance (km)", kind: "number" },
    { key: "elevation_m", label: "Elevation (m)", kind: "number" },
    { key: "start", label: "Start (trailhead)", kind: "text" },
    { key: "end", label: "End", kind: "text" },
    { key: "route", label: "Route", kind: "enum", enum: HIKE_ROUTES, placeholder: "back_and_forth" },
  ],
  meal: [
    { key: "meal_type", label: "Meal type", kind: "enum", enum: MEAL_TYPES, placeholder: "inferred from start_time" },
    { key: "restaurant", label: "Restaurant", kind: "text" },
    { key: "area", label: "Area", kind: "text", help: "Town/region to eat in (used when no restaurant named)" },
    { key: "address", label: "Address", kind: "text" },
  ],
  buffer: [{ key: "duration", label: "Duration", kind: "duration", required: true, placeholder: "Length of the free time" }],
};

export const WAYPOINT_FIELDS: FieldSpec[] = [
  { key: "location", label: "Location", kind: "text", placeholder: "The waypoint's name" },
  { key: "duration", label: "Leg duration", kind: "duration", placeholder: "1h30 / 45 min" },
  { key: "distance_km", label: "Leg distance (km)", kind: "number" },
];

export const TRANSPORT_FIELDS: FieldSpec[] = [
  { key: "type", label: "Type", kind: "enum", enum: TRANSPORT_TYPES, placeholder: "other" },
  { key: "start", label: "Start (departure)", kind: "text", required: true, placeholder: "Departure address" },
  { key: "end", label: "End (arrival)", kind: "text", required: true, placeholder: "Arrival address" },
  { key: "start_date", label: "Start date", kind: "date", required: true },
  { key: "end_date", label: "End date", kind: "date", placeholder: "inferred (+1 day if crosses midnight)" },
  { key: "start_time", label: "Start time", kind: "time", required: true },
  { key: "end_time", label: "End time", kind: "time", placeholder: "start + duration" },
  { key: "duration", label: "Duration", kind: "duration", placeholder: "inferred from the two times" },
  { key: "start_tz", label: "Start tz", kind: "tz", placeholder: "defaults.timezone" },
  { key: "end_tz", label: "End tz", kind: "tz", placeholder: "defaults.timezone" },
  { key: "flight_number", label: "Flight number", kind: "text" },
  { key: "train_number", label: "Train number", kind: "text" },
  { key: "booking_number", label: "Booking number", kind: "text" },
  { key: "booking_source", label: "Booking source", kind: "text" },
  { key: "website", label: "Website", kind: "text", placeholder: "https://example.com" },
  { key: "booking_link", label: "Booking link", kind: "text", placeholder: "https://example.com" },
  { key: "status", label: "Status", kind: "enum", enum: STATUSES, placeholder: "none (no badge)" },
  { key: "price", label: "Price", kind: "number", placeholder: "amount only, no symbol" },
  { key: "currency", label: "Currency", kind: "text", placeholder: "defaults.currency" },
  { key: "paid", label: "Paid", kind: "paid" },
];

export const ACCOMMODATION_FIELDS: FieldSpec[] = [
  { key: "name", label: "Name", kind: "text", required: true },
  { key: "arrival", label: "Arrival (check-in)", kind: "date", required: true },
  { key: "departure", label: "Departure (check-out)", kind: "date", required: true },
  { key: "city", label: "City", kind: "text", required: true },
  { key: "type", label: "Type", kind: "enum", enum: ACCOMMODATION_TYPES, placeholder: "hotel" },
  { key: "address", label: "Address", kind: "text" },
  { key: "contact", label: "Contact", kind: "text", placeholder: "phone or email" },
  { key: "booking_source", label: "Booking source", kind: "text" },
  { key: "website", label: "Website", kind: "text", placeholder: "https://example.com" },
  { key: "booking_link", label: "Booking link", kind: "text", placeholder: "https://example.com" },
  { key: "status", label: "Status", kind: "enum", enum: STATUSES, placeholder: "none (no badge)" },
  { key: "price", label: "Price", kind: "number", placeholder: "whole-stay amount, no symbol" },
  { key: "currency", label: "Currency", kind: "text", placeholder: "defaults.currency" },
  { key: "paid", label: "Paid", kind: "paid" },
  { key: "breakfast_included", label: "Breakfast included", kind: "bool" },
];

export const CAR_RENTAL_FIELDS: FieldSpec[] = [
  { key: "booking_start_date", label: "Booking start date", kind: "date", required: true },
  { key: "booking_start_time", label: "Booking start time", kind: "time", required: true },
  { key: "booking_start_tz", label: "Booking start tz", kind: "tz", placeholder: "defaults.timezone" },
  { key: "booking_end_date", label: "Booking end date", kind: "date", required: true },
  { key: "booking_end_time", label: "Booking end time", kind: "time", required: true },
  { key: "booking_end_tz", label: "Booking end tz", kind: "tz", placeholder: "defaults.timezone" },
  { key: "pickup_date", label: "Pick-up date", kind: "date", required: true },
  { key: "pickup_time", label: "Pick-up time", kind: "time", required: true },
  { key: "pickup_tz", label: "Pick-up tz", kind: "tz", placeholder: "defaults.timezone" },
  { key: "pickup_location", label: "Pick-up location", kind: "text", required: true },
  { key: "pickup_duration", label: "Pick-up duration", kind: "duration" },
  { key: "dropoff_date", label: "Drop-off date", kind: "date", required: true },
  { key: "dropoff_time", label: "Drop-off time", kind: "time", required: true },
  { key: "dropoff_tz", label: "Drop-off tz", kind: "tz", placeholder: "defaults.timezone" },
  { key: "dropoff_location", label: "Drop-off location", kind: "text", placeholder: "the pick-up location" },
  { key: "dropoff_duration", label: "Drop-off duration", kind: "duration" },
  { key: "company", label: "Company", kind: "text" },
  { key: "booking_number", label: "Booking number", kind: "text" },
  { key: "website", label: "Website", kind: "text", placeholder: "https://example.com" },
  { key: "booking_link", label: "Booking link", kind: "text", placeholder: "https://example.com" },
  { key: "status", label: "Status", kind: "enum", enum: STATUSES, placeholder: "none (no badge)" },
  { key: "price", label: "Price", kind: "number", placeholder: "amount only, no symbol" },
  { key: "currency", label: "Currency", kind: "text", placeholder: "defaults.currency" },
  { key: "paid", label: "Paid", kind: "paid" },
  { key: "car_type", label: "Car type", kind: "enum", enum: CAR_TYPES, placeholder: "regular" },
  { key: "car_model", label: "Car model", kind: "text" },
  { key: "contact", label: "Contact", kind: "text", placeholder: "phone or email" },
  { key: "additional_drivers", label: "Additional drivers", kind: "integer", placeholder: "0" },
];

// -------------------------------------------------------------- new-item stubs
// Minimal valid-ish starting points inserted by the "Add" buttons. Kept sparse
// (only the required fields) so pruning on save keeps files clean.
export function newActivity(type: SrcActivityType): SrcActivity {
  switch (type) {
    case "road":
      return { type, start: "", waypoints: [newWaypoint()] };
    case "point_of_interest":
      return { type, name: "" };
    case "place":
      return { type, name: "" };
    case "hike":
      return { type, name: "" };
    case "meal":
      return { type };
    case "buffer":
      return { type, duration: "" };
  }
}

export function newWaypoint(): SrcWaypoint {
  return { location: "" };
}

export function newMeal(): SrcMeal {
  return { type: "meal" };
}

export function newDay(): SrcDay {
  return { title: "", activities: [newActivity("point_of_interest")] };
}

export function newTransport(): SrcTransport {
  return { type: "other", start: "", end: "", start_date: "", start_time: "" };
}

export function newAccommodation(): SrcAccommodation {
  return { name: "", arrival: "", departure: "", city: "", type: "hotel" };
}

export function newCarRental(): SrcCarRental {
  return {
    booking_start_date: "",
    booking_start_time: "",
    booking_end_date: "",
    booking_end_time: "",
    pickup_date: "",
    pickup_time: "",
    dropoff_date: "",
    dropoff_time: "",
    pickup_location: "",
    car_type: "regular",
  };
}

export function newSecondaryCurrency(): SrcSecondaryCurrency {
  return { currency: "", change_rate: 1 };
}
