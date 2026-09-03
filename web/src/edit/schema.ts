// The field registry: a data description of every editable field, driven by the
// field tables in ../../../file_format.md. Forms render from these descriptors so
// the schema lives in one place — adding/renaming a field is a change here (plus
// the TS type in types/source.ts) rather than in every form component.
//
// `placeholder` carries the format/default hint (shown as the input placeholder);
// `help` is a longer tooltip. `NEW_*` are the stubs the "Add" buttons insert.

import type {
  SrcAccommodation,
  SrcActivity,
  SrcActivityType,
  SrcCarRental,
  SrcDay,
  SrcEmergencyContact,
  SrcMeal,
  SrcRoadLeg,
  SrcSecondaryCurrency,
  SrcTransport,
  SrcTransportLeg,
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
  | "gpx" // a .gpx file picker, stored base64 (hike.gpx)
  | "coordinate";

export interface FieldSpec {
  key: string;
  label: string;
  kind: FieldKind;
  enum?: readonly string[];
  placeholder?: string; // default / format hint
  help?: string; // the (?) tooltip: what the field is + how it defaults
  // When the field inherits an unset value from a `defaults.<key>`, the empty
  // placeholder is rendered as "<effective value> (from defaults.<key>)" using
  // the live draft defaults (see EditDefaultsContext).
  inheritsFrom?: string;
  required?: boolean;
  // `bool` only: this flag is ON when the key is absent (e.g. show_sun_times).
  // The switch then starts on and switching it off writes an explicit `false`
  // — whereas a default-off switch writes `true` and clears the key when off.
  defaultOn?: boolean;
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
  { key: "title", label: "Title", kind: "text", required: true, placeholder: "Trip title (shown on the cover)", help: "The trip title shown on the cover. Required." },
  { key: "subtitle", label: "Subtitle", kind: "text", placeholder: "Line under the title", help: "A line shown under the title on the cover. Optional — hidden when empty." },
  { key: "start_date", label: "Start date", kind: "date", placeholder: "inferred (earliest date)", help: "Trip start date. Defaults to the earliest date across days, transport and accommodation." },
  { key: "end_date", label: "End date", kind: "date", placeholder: "inferred (latest date)", help: "Trip end date. Defaults to the latest date across days, transport and accommodation." },
  { key: "cover_color", label: "Cover color", kind: "color", placeholder: "#1f4e5f", help: "Accent colour driving the whole palette. Defaults to #1f4e5f." },
  { key: "summary", label: "Summary", kind: "textarea", placeholder: "Paragraph shown on the cover", help: "A paragraph shown on the cover. Optional — hidden when empty." },
];

// A run of fields shown under one small section title. `defaults` is a grab-bag
// of seventeen unrelated switches, so the form renders it in groups rather than
// as one wall of inputs (the titles look like "Secondary currencies").
export interface FieldGroup {
  title: string;
  fields: FieldSpec[];
}

export const DEFAULTS_GROUPS: FieldGroup[] = [
  {
    title: "Day timing",
    fields: [
      { key: "start_time", label: "Start time", kind: "time", placeholder: "08:00", help: "The first activity's start time each day. Defaults to 08:00." },
      { key: "end_time", label: "End time", kind: "time", placeholder: "18:00", help: "Where each day's last activity should land: auto-sized buffers spread the day out to it, and validation warns past it. Defaults to 18:00." },
      { key: "auto_sized_buffer", label: "Auto-sized buffer", kind: "bool", defaultOn: true, help: "Size the buffers between a day's activities so the day spreads out and ends on “End time”, in steps of 5 min. Defaults to on — switch it off to fall back to the fixed “Buffer” below." },
      { key: "buffer", label: "Buffer", kind: "duration", placeholder: "0 (no fixed buffer)", help: "A fixed buffer inserted between consecutive activities. Ignored while “Auto-sized buffer” is on. Defaults to 0 (none)." },
      { key: "timezone", label: "Time zone", kind: "tz", placeholder: "GMT", help: "Default UTC offset for all times (e.g. +02:00, UTC-3, Z). Defaults to GMT (UTC+0)." },
    ],
  },
  {
    title: "Meals",
    fields: [
      { key: "breakfast_until", label: "Breakfast until", kind: "time", placeholder: "10:00", help: "A meal starting before this is inferred as breakfast. Defaults to 10:00." },
      { key: "lunch_until", label: "Lunch until", kind: "time", placeholder: "16:00", help: "A meal up to this (after breakfast) is lunch; later is dinner. Defaults to 16:00." },
      { key: "meal_duration", label: "Meal duration", kind: "duration", placeholder: "0 (instant)", help: "Default length of a meal with no duration/end time. Defaults to 0 (instant)." },
    ],
  },
  {
    title: "Accommodation nights",
    fields: [
      { key: "accommodation_start_time", label: "Accommodation start time", kind: "time", placeholder: "22:00", help: "Clock time an accommodation booking starts on the calendar (ICS export). Defaults to 22:00." },
      { key: "accommodation_end_time", label: "Accommodation end time", kind: "time", placeholder: "00:00", help: "Clock time each accommodation night ends on the calendar (ICS export). Defaults to 00:00 (midnight)." },
    ],
  },
  {
    title: "Money",
    fields: [
      { key: "currency", label: "Currency", kind: "text", placeholder: "EUR", help: "The currency every price is in unless it sets its own. 3-letter ISO code. Defaults to EUR." },
    ],
  },
  {
    title: "Maps",
    fields: [
      { key: "include_maps_in_render", label: "Include maps in render", kind: "bool", help: "Draw a per-day map with a pin for each located activity. Defaults to off." },
      { key: "include_hike_maps", label: "Include hike maps", kind: "bool", defaultOn: true, help: "Draw the trail map and elevation profile of any hike that attaches a GPX file. Independent of “Include maps in render”, since the track comes with the hike. Defaults to on — switch it off to hide them." },
      { key: "infer_coordinates_from_address", label: "Infer coordinates from address", kind: "bool", help: "Geocode activities that lack an explicit coordinate. Defaults to off (only explicit coordinates are mapped)." },
      { key: "inference_countries", label: "Inference countries", kind: "csv", placeholder: "FR, ES", help: "Restrict geocoding to these 2-letter ISO codes (e.g. FR, ES). Defaults to any country." },
    ],
  },
  {
    title: "Sun & moon",
    fields: [
      { key: "show_sun_times", label: "Show sunrise/sunset", kind: "bool", defaultOn: true, help: "Show each day's sunrise and sunset in its header, computed at that night's accommodation. Defaults to on — switch it off to hide them." },
      { key: "show_moon_phase", label: "Show moon phase", kind: "bool", defaultOn: true, help: "Show the night's moon phase — closing the sunrise/sunset line when that is shown too, otherwise in the day's “tonight” section. Defaults to on — switch it off to hide it." },
    ],
  },
];

// Every `defaults` field, flattened. The finding index walks this rather than the
// groups, so regrouping the form can never change which paths it knows about.
export const DEFAULTS_FIELDS: FieldSpec[] = DEFAULTS_GROUPS.flatMap((g) => g.fields);

// One entry of `misc.emergency_contacts`. Both halves are optional — the model
// renders whichever it is given, and leaving an unknown number out beats
// inventing one — so neither is marked required here either.
export const EMERGENCY_CONTACT_FIELDS: FieldSpec[] = [
  { key: "name", label: "Name", kind: "text", placeholder: "e.g. SAMU (medical emergencies)", help: "Who this contact reaches — the service, the embassy, the person. Optional: a number on its own is still listed." },
  { key: "contact", label: "Contact", kind: "text", placeholder: "e.g. 112, +33 1 43 12 22 22", help: "How to reach them: a phone number, an email or an address. Free text, so a country's own conventions survive. Optional — but an entry with neither half is dropped." },
];

export const SECONDARY_CURRENCY_FIELDS: FieldSpec[] = [
  { key: "currency", label: "Currency", kind: "text", required: true, placeholder: "USD", help: "The secondary currency's 3-letter ISO code. Required." },
  { key: "change_rate", label: "Rate", kind: "number", required: true, placeholder: "units per 1 default (1 € = 1.09 $ → 1.09)", help: "Units of this currency per one unit of the default currency (e.g. 1 € = 1.09 $ → 1.09). Required." },
];

export const DAY_FIELDS: FieldSpec[] = [
  { key: "title", label: "Title", kind: "text", required: true, placeholder: "The day's title", help: "The day's title. Required." },
  { key: "city", label: "City", kind: "text", placeholder: "City/region label", help: "City/region label for the day. Optional." },
  { key: "date", label: "Date", kind: "date", placeholder: "trip start + the day's index", help: "The day's date, matched to stays & transport. Defaults to the trip start date plus the day's index." },
  { key: "description", label: "Description", kind: "textarea", placeholder: "Intro paragraph for the day", help: "Intro paragraph for the day. Optional." },
  { key: "bank_holiday", label: "Bank holiday", kind: "bool", help: "Switch on if the day is a public holiday where you are — the day then opens with a banner warning about closures and reduced hours. Defaults to off." },
];

// Shared scheduling fields (all activities except buffer).
export const SCHEDULED_FIELDS: FieldSpec[] = [
  { key: "start_time", label: "Start time", kind: "time", placeholder: "previous item's end / defaults.start_time", help: "Clock time this activity starts. Defaults to the previous item's end (or defaults.start_time for the first)." },
  { key: "end_time", label: "End time", kind: "time", placeholder: "start + duration", help: "Clock time this activity ends. Inferred from start + duration when unset." },
  { key: "duration", label: "Duration", kind: "duration", placeholder: "1h30 / 45 min", help: "How long it lasts (e.g. 1h30, 45 min). Inferred from start/end when unset, else 0." },
  { key: "start_tz", label: "Start tz", kind: "tz", inheritsFrom: "timezone", help: "Start time zone (UTC offset). Defaults to defaults.timezone (GMT)." },
  { key: "end_tz", label: "End tz", kind: "tz", inheritsFrom: "timezone", help: "End time zone (UTC offset). Defaults to defaults.timezone (GMT)." },
  { key: "detour", label: "Detour", kind: "bool", help: "A stop you probably won't make but want the book to carry anyway. It's left off the day's timeline — it takes no time and gets no buffer before it — and it's shown a step down in emphasis, with its duration but no start/end time (a time written here is dropped). Defaults to off." },
];

// `place` is the one activity whose duration falls back to what it *contains*,
// so its Duration field reads differently from every other activity's (mirrors
// validate/specs.py's PLACE_SCHEDULE). Same fields otherwise.
export const PLACE_SCHEDULED_FIELDS: FieldSpec[] = SCHEDULED_FIELDS.map((f) =>
  f.key === "duration"
    ? {
        ...f,
        placeholder: "the nested activities' total",
        help: "How long it lasts (e.g. 1h30, 45 min). Defaults to the nested activities' total — a place is what you do there. Inferred from start/end when those are given.",
      }
    : f,
);

// The guidebook page reference, offered on every activity type that has a
// `description` (road / point_of_interest / place / hike) with one wording.
const GUIDEBOOK_FIELD: FieldSpec = {
  key: "guidebook_pages",
  label: "Guidebook pages",
  kind: "text",
  placeholder: "14 / 15-18 / 16, 23, 25-30",
  help: "The guidebook page(s) covering this activity — a single page, a range, or a comma-separated list (e.g. 14, 15-18, 16, 23, 25-30). Shown as a light-accent pill at the end of the description. Optional.",
};

// Per-activity-type fields (excluding the shared scheduling ones and nested
// `activities`/`legs`/`coordinate`, which the form renders specially).
export const ACTIVITY_FIELDS: Record<SrcActivityType, FieldSpec[]> = {
  road: [
    { key: "distance_km", label: "Distance (km)", kind: "number", placeholder: "driving distance", help: "Total driving distance in km for the whole drive (each leg carries its own too). Optional." },
    { key: "display_start_on_maps", label: "Pin the departure", kind: "bool", help: "Give the drive's departure a numbered pin on the day map. Defaults to off — a drive is drawn as a route, and its pins are opt-in." },
    { key: "display_end_on_maps", label: "Pin the arrival", kind: "bool", help: "Give the drive's final arrival a numbered pin on the day map. Defaults to off." },
    { key: "display_intermediate_point_on_maps", label: "Pin the junctions", kind: "bool", defaultOn: true, help: "Give every junction between two legs a numbered pin on the day map — splitting the drive there is what says the junction matters. Defaults to on, unlike the two ends: switch it off to leave the junctions marked only by the route's own small disc." },
    { key: "same_start_as_previous_activity", label: "Starts at the previous activity", kind: "bool", help: "The drive departs from wherever the previous activity is. You can then leave the first leg's From and its coordinate blank — they're filled in from that activity — and the departure shares its map pin instead of taking a second number for the same place. Errors if there is no previous activity. Defaults to off." },
    { key: "same_end_as_next_activity", label: "Ends at the next activity", kind: "bool", help: "The drive arrives at wherever the next activity is. You can then leave the last leg's To and its coordinate blank — they're filled in from that activity, which must have a coordinate — and the arrival shares its map pin instead of taking a second number for the same place. Errors if there is no next activity. Defaults to off." },
    { key: "description", label: "Description", kind: "textarea", help: "Anything about the drive the other fields don't cover — road conditions, a scenic stretch, a toll or ferry. Optional." },
    GUIDEBOOK_FIELD,
  ],
  point_of_interest: [
    { key: "name", label: "Name", kind: "text", required: true, placeholder: "Point-of-interest name", help: "Point-of-interest name. Required." },
    { key: "category", label: "Category", kind: "enum", enum: POI_CATEGORIES, placeholder: "other", help: "The kind of place, shown as a badge. Defaults to 'other'." },
    { key: "address", label: "Address", kind: "text", help: "Street address. Optional." },
    { key: "description", label: "Description", kind: "textarea", help: "A description. Optional." },
    GUIDEBOOK_FIELD,
    { key: "website", label: "Website", kind: "text", placeholder: "https://example.com", help: "Link to the venue's website, shown as a clickable link. Optional." },
    { key: "opening_days", label: "Opening days", kind: "text", placeholder: "tue-sun / mon-fri, sun", help: "The days it opens — weekday names, single days and/or ranges (e.g. tue-sun, mon-fri, sun). Shown under the address, and you get a warning if the visit falls on another day. Defaults to every day." },
    { key: "opening_hours", label: "Opening hours", kind: "text", placeholder: "09:30-18:00 / 09:30-12:30, 14:00-18:00", help: "The hours it opens — one or more HH:MM-HH:MM ranges, so a midday closure stays two ranges (e.g. 09:30-12:30, 14:00-18:00). Shown under the address, and you get a warning if the visit falls outside them. Defaults to all day." },
  ],
  place: [
    { key: "name", label: "Name", kind: "text", required: true, placeholder: "Place name", help: "Place name (e.g. a town) grouping the nested activities. Required." },
    { key: "description", label: "Description", kind: "textarea", help: "A description. Optional." },
    GUIDEBOOK_FIELD,
  ],
  hike: [
    { key: "name", label: "Name", kind: "text", required: true, placeholder: "Hike name", help: "Hike name. Required." },
    { key: "description", label: "Description", kind: "textarea", help: "A description. Optional." },
    GUIDEBOOK_FIELD,
    { key: "distance_km", label: "Distance (km)", kind: "number", help: "Distance in km. Optional." },
    { key: "elevation_m", label: "Elevation (m)", kind: "number", help: "Elevation gain in m. Optional." },
    { key: "start", label: "Start (trailhead)", kind: "text", help: "Trailhead address. Optional." },
    { key: "end", label: "End", kind: "text", help: "End address. For a loop/back-and-forth it should equal (or omit) start; for one-way it should differ. Optional." },
    { key: "route", label: "Route", kind: "enum", enum: HIKE_ROUTES, placeholder: "back_and_forth", help: "Route shape. Defaults to back_and_forth." },
    { key: "gpx", label: "GPX track", kind: "gpx", help: "A .gpx file of the trail, stored in the itinerary itself. Drawn as a trail map plus an elevation profile, and it fills in the distance and elevation gain when you leave those blank. Optional." },
  ],
  meal: [
    { key: "meal_type", label: "Meal type", kind: "enum", enum: MEAL_TYPES, placeholder: "inferred from start_time", help: "Which meal it is. Inferred from the start time when unset (breakfast/lunch/dinner); the others are explicit-only." },
    { key: "restaurant", label: "Restaurant", kind: "text", help: "Restaurant name; shown in the head and the cover highlights. Optional." },
    { key: "area", label: "Area", kind: "text", help: "Town/region to eat in, used when no restaurant is named. Optional." },
    { key: "address", label: "Address", kind: "text", help: "Street address. Optional." },
  ],
  buffer: [{ key: "duration", label: "Duration", kind: "duration", required: true, placeholder: "Length of the free time", help: "Length of the free time (e.g. 30 min). A 0 min buffer just suppresses the default buffer here. Required." }],
};

// One hop of a road. The endpoint names sit here (their coordinates are the two
// CoordinateFields the leg's form adds), and either may be left blank when the
// neighbouring leg names the junction — the first leg needs its own departure
// and the last its own arrival. The route-shaping `waypoints` are a sub-array of
// bare coordinates, so they have no field spec of their own.
export const ROAD_LEG_FIELDS: FieldSpec[] = [
  { key: "start_location", label: "From", kind: "text", placeholder: "the previous leg's arrival", help: "Where this hop departs from. Leave it blank on any leg but the first: it then reuses the previous leg's arrival. The first leg may leave it blank too when the drive starts at the previous activity." },
  { key: "end_location", label: "To", kind: "text", placeholder: "the next leg's departure", help: "Where this hop arrives. Required on the last leg — unless the drive ends at the next activity; on an earlier one the next leg's departure can name it instead." },
  { key: "duration", label: "Driving time", kind: "duration", placeholder: "1h30 / 45 min", help: "Driving time for this hop. Optional, but validation warns when it's missing." },
  { key: "distance_km", label: "Distance (km)", kind: "number", help: "Driving distance for this hop. Optional, but validation warns when it's missing." },
  { key: "off_road", label: "Off-road", kind: "bool", help: "Mark just this hop as off-road. The drive as a whole counts as off-road only when every leg is. Defaults to off." },
  { key: "gpx", label: "GPX recording", kind: "gpx", help: "A .gpx recording of this hop, stored in the itinerary itself. It becomes this leg's line on the day map instead of the routed guess — there's no separate trail map or elevation profile, unlike a hike's. Optional." },
];

// A booking: what is reserved once. Its hops live in `legs` (TRANSPORT_LEG_FIELDS),
// rendered by TransportForm as a sub-array — the same shape as a road's legs.
export const TRANSPORT_FIELDS: FieldSpec[] = [
  { key: "type", label: "Type", kind: "enum", enum: TRANSPORT_TYPES, placeholder: "other", help: "Transport kind, shown as a badge on the booking and on each of its legs. Defaults to 'other'." },
  { key: "name", label: "Name", kind: "text", placeholder: "the route through its legs", help: "What to call the whole booking (“Round trip New York ↔ France”), shown as the card's heading. Defaults to the route through its legs (A → B → C)." },
  { key: "booking_number", label: "Booking number", kind: "text", help: "Reservation reference / PNR, covering every leg. Optional." },
  { key: "booking_source", label: "Booking source", kind: "text", help: "Where it was booked. Optional." },
  { key: "website", label: "Website", kind: "text", placeholder: "https://example.com", help: "Link to the carrier's website. Optional." },
  { key: "booking_link", label: "Booking link", kind: "text", placeholder: "https://example.com", help: "Direct link to this reservation. Optional." },
  { key: "status", label: "Status", kind: "enum", enum: STATUSES, placeholder: "none (no badge)", help: "Reservation status, shown as a badge. No badge when unset." },
  { key: "description", label: "Description", kind: "textarea", placeholder: "Short note about the whole booking", help: "A short note about the whole reservation — a baggage allowance, a fare condition, a check-in window. A note about one hop goes on that leg instead. Optional." },
  { key: "price", label: "Price", kind: "number", placeholder: "amount only, no symbol", help: "Price of the whole booking, every leg included (amount only, no symbol). Optional." },
  { key: "currency", label: "Currency", kind: "text", inheritsFrom: "currency", help: "Currency this price is in (3-letter ISO). Defaults to defaults.currency." },
  { key: "paid", label: "Paid", kind: "paid", help: "Payment state, shown as a badge. No badge when unset." },
];

// One hop of a booking. A single-hop booking has exactly one leg — the array is
// required and must not be empty.
export const TRANSPORT_LEG_FIELDS: FieldSpec[] = [
  { key: "start", label: "Start (departure)", kind: "text", required: true, placeholder: "Departure address", help: "Departure address. Required." },
  { key: "end", label: "End (arrival)", kind: "text", required: true, placeholder: "Arrival address", help: "Arrival address. Required." },
  { key: "start_date", label: "Start date", kind: "date", required: true, help: "Departure date; slots the leg into that day. Required." },
  { key: "end_date", label: "End date", kind: "date", placeholder: "inferred (+1 day if crosses midnight)", help: "Arrival date. Inferred (+1 day if the leg crosses midnight)." },
  { key: "start_time", label: "Start time", kind: "time", required: true, help: "Departure time. Required." },
  { key: "end_time", label: "End time", kind: "time", placeholder: "start + duration", help: "Arrival time. Inferred from start + duration when unset." },
  { key: "duration", label: "Duration", kind: "duration", placeholder: "inferred from the two times", help: "Travel time. Inferred from the two times when unset." },
  { key: "start_tz", label: "Start tz", kind: "tz", inheritsFrom: "timezone", help: "Departure time zone (UTC offset). Defaults to defaults.timezone (GMT)." },
  { key: "end_tz", label: "End tz", kind: "tz", inheritsFrom: "timezone", help: "Arrival time zone (UTC offset). Defaults to defaults.timezone (GMT)." },
  { key: "flight_number", label: "Flight number", kind: "text", help: "Flight number of this leg (planes only), shown under its route. Optional." },
  { key: "train_number", label: "Train number", kind: "text", help: "Train number of this leg (trains only), shown under its route. Optional." },
  { key: "description", label: "Description", kind: "textarea", placeholder: "Short note", help: "A short note about this leg — a seat, a terminal, a coach number. A note about the whole reservation goes on the booking instead. Optional." },
];

export const ACCOMMODATION_FIELDS: FieldSpec[] = [
  { key: "name", label: "Name", kind: "text", required: true, help: "Accommodation name. Required." },
  { key: "arrival", label: "Arrival (check-in)", kind: "date", required: true, help: "Check-in date; the stay covers nights from here up to (not including) departure. Required." },
  { key: "departure", label: "Departure (check-out)", kind: "date", required: true, help: "Check-out date; the checkout day shows no stay bar. Required." },
  { key: "city", label: "City", kind: "text", required: true, help: "Town shown in the cover overview. Required." },
  { key: "type", label: "Type", kind: "enum", enum: ACCOMMODATION_TYPES, placeholder: "hotel", help: "Kind of accommodation, shown as a badge. Defaults to 'hotel'." },
  { key: "address", label: "Address", kind: "text", help: "Street address. Optional." },
  { key: "contact", label: "Contact", kind: "text", placeholder: "phone or email", help: "Phone or email. Optional." },
  { key: "booking_source", label: "Booking source", kind: "text", help: "Where it was booked. Optional." },
  { key: "website", label: "Website", kind: "text", placeholder: "https://example.com", help: "Link to the property's website. Optional." },
  { key: "booking_link", label: "Booking link", kind: "text", placeholder: "https://example.com", help: "Direct link to this reservation. Optional." },
  { key: "status", label: "Status", kind: "enum", enum: STATUSES, placeholder: "none (no badge)", help: "Reservation status, shown as a badge. No badge when unset." },
  { key: "description", label: "Description", kind: "textarea", placeholder: "Short note", help: "A short note for whatever the other fields don't cover — a door code, where to park, which bell to ring. Optional." },
  { key: "price", label: "Price", kind: "number", placeholder: "whole-stay amount, no symbol", help: "Price for the whole stay (amount only, no symbol). Optional." },
  { key: "currency", label: "Currency", kind: "text", inheritsFrom: "currency", help: "Currency this price is in (3-letter ISO). Defaults to defaults.currency." },
  { key: "paid", label: "Paid", kind: "paid", help: "Payment state, shown as a badge. No badge when unset." },
  { key: "breakfast_included", label: "Breakfast included", kind: "bool", help: "Show a 'Breakfast included' line. Defaults to off." },
];

export const CAR_RENTAL_FIELDS: FieldSpec[] = [
  { key: "booking_start_date", label: "Booking start date", kind: "date", required: true, help: "Start of the booking window. The pick-up/drop-off must fall inside it. Required." },
  { key: "booking_start_time", label: "Booking start time", kind: "time", required: true, help: "Booking-window start time. Required." },
  { key: "booking_start_tz", label: "Booking start tz", kind: "tz", inheritsFrom: "timezone", help: "Booking-start time zone (UTC offset). Defaults to defaults.timezone (GMT)." },
  { key: "booking_end_date", label: "Booking end date", kind: "date", required: true, help: "End of the booking window. Required." },
  { key: "booking_end_time", label: "Booking end time", kind: "time", required: true, help: "Booking-window end time. Required." },
  { key: "booking_end_tz", label: "Booking end tz", kind: "tz", inheritsFrom: "timezone", help: "Booking-end time zone (UTC offset). Defaults to defaults.timezone (GMT)." },
  { key: "pickup_date", label: "Pick-up date", kind: "date", required: true, help: "Pick-up date; must be within the booking window. Woven into that day. Required." },
  { key: "pickup_time", label: "Pick-up time", kind: "time", required: true, help: "Pick-up time. Required." },
  { key: "pickup_tz", label: "Pick-up tz", kind: "tz", inheritsFrom: "timezone", help: "Pick-up time zone (UTC offset). Defaults to defaults.timezone (GMT)." },
  { key: "pickup_location", label: "Pick-up location", kind: "text", required: true, help: "Where you pick up the car. Required." },
  { key: "pickup_duration", label: "Pick-up duration", kind: "duration", help: "How long the pick-up takes. Optional (not shown when unset)." },
  { key: "dropoff_date", label: "Drop-off date", kind: "date", required: true, help: "Drop-off date; must be within the booking window and not before pick-up. Required." },
  { key: "dropoff_time", label: "Drop-off time", kind: "time", required: true, help: "Drop-off time. Required." },
  { key: "dropoff_tz", label: "Drop-off tz", kind: "tz", inheritsFrom: "timezone", help: "Drop-off time zone (UTC offset). Defaults to defaults.timezone (GMT)." },
  { key: "dropoff_location", label: "Drop-off location", kind: "text", placeholder: "the pick-up location", help: "Where you drop off the car. Defaults to the pick-up location." },
  { key: "dropoff_duration", label: "Drop-off duration", kind: "duration", help: "How long the drop-off takes. Optional (not shown when unset)." },
  { key: "company", label: "Company", kind: "text", help: "Rental company. Optional." },
  { key: "booking_number", label: "Booking number", kind: "text", help: "Reservation reference. Optional." },
  { key: "website", label: "Website", kind: "text", placeholder: "https://example.com", help: "Link to the rental company's website. Optional." },
  { key: "booking_link", label: "Booking link", kind: "text", placeholder: "https://example.com", help: "Direct link to this reservation. Optional." },
  { key: "status", label: "Status", kind: "enum", enum: STATUSES, placeholder: "none (no badge)", help: "Reservation status, shown as a badge. No badge when unset." },
  { key: "description", label: "Description", kind: "textarea", placeholder: "Short note", help: "A short note for whatever the other fields don't cover — the insurance excess, a fuel policy, where the desk is. Optional." },
  { key: "price", label: "Price", kind: "number", placeholder: "amount only, no symbol", help: "Rental price (amount only, no symbol). Optional." },
  { key: "currency", label: "Currency", kind: "text", inheritsFrom: "currency", help: "Currency this price is in (3-letter ISO). Defaults to defaults.currency." },
  { key: "paid", label: "Paid", kind: "paid", help: "Payment state, shown as a badge. No badge when unset." },
  { key: "car_type", label: "Car type", kind: "enum", enum: CAR_TYPES, placeholder: "regular", help: "Car category, shown as a badge. Defaults to 'regular'." },
  { key: "car_model", label: "Car model", kind: "text", help: "Car make/model. Optional." },
  { key: "contact", label: "Contact", kind: "text", placeholder: "phone or email", help: "Phone or email for the rental company. Optional." },
  { key: "additional_drivers", label: "Additional drivers", kind: "integer", placeholder: "0", help: "Number of additional drivers. Defaults to 0." },
];

// -------------------------------------------------------------- new-item stubs
// Minimal valid-ish starting points inserted by the "Add" buttons. Kept sparse
// (only the required fields) so pruning on save keeps files clean.
export function newActivity(type: SrcActivityType): SrcActivity {
  switch (type) {
    case "road":
      return { type, legs: [newRoadLeg()] };
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

export function newRoadLeg(): SrcRoadLeg {
  return { start_location: "", end_location: "" };
}

export function newMeal(): SrcMeal {
  return { type: "meal" };
}

export function newDay(): SrcDay {
  return { title: "", activities: [newActivity("point_of_interest")] };
}

export function newTransport(): SrcTransport {
  return { type: "other", legs: [newTransportLeg()] };
}

export function newTransportLeg(): SrcTransportLeg {
  return { start: "", end: "", start_date: "", start_time: "" };
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

export function newEmergencyContact(): SrcEmergencyContact {
  return { name: "", contact: "" };
}
