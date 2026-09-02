// Date formatting (localized via Intl from the model's ISO dates) plus a small
// map of the handful of UI labels the book renderer needs, in English/French.

export type Lang = "en" | "fr";

// Parse an ISO "YYYY-MM-DD" as a *local* date (avoid the UTC-midnight day shift).
function parseISO(iso: string): Date {
  return new Date(`${iso}T00:00:00`);
}

export function fmtDate(iso: string | null, lang: Lang, long = false): string {
  if (!iso) return "";
  const opts: Intl.DateTimeFormatOptions = long
    ? { weekday: "long", day: "numeric", month: "long", year: "numeric" }
    : { day: "numeric", month: "short" };
  return new Intl.DateTimeFormat(lang, opts).format(parseISO(iso));
}

export function fmtDateRange(
  start: string | null,
  end: string | null,
  lang: Lang,
): string {
  if (start && end) {
    const opts: Intl.DateTimeFormatOptions = { day: "numeric", month: "short", year: "numeric" };
    const f = new Intl.DateTimeFormat(lang, opts);
    return `${f.format(parseISO(start))} – ${f.format(parseISO(end))}`;
  }
  if (start) return fmtDate(start, lang, true);
  return "";
}

const LABELS = {
  en: {
    day: "Day",
    overview: "Day-by-day",
    dayCol: "Day",
    dateCol: "Date",
    activitiesCol: "Highlights",
    sleepCol: "Sleep in",
    days: "days",
    nights: "nights",
    night: "night",
    tonight: "Tonight",
    aboard: "aboard",
    freeTime: "Buffer",
    transport: "Transport",
    accommodation: "Accommodation",
    carRentals: "Car rentals",
    paid: "paid",
    toPay: "to pay",
    booked: "booked",
    confirmed: "confirmed",
    breakfastIncluded: "breakfast included",
    pickUp: "Pick-up",
    dropOff: "Drop-off",
    pickUpCar: "Pick up the rental car",
    dropOffCar: "Drop off the rental car",
    nowhere: "no accommodation on file",
    elevation: "elevation",
    distance: "distance",
    offRoad: "off-road",
    navigate: "Navigate",
    website: "Website",
    reservation: "Reservation",
    // the same template pdf/base.py's `_guidebook` fills (translations.py holds
    // the PDF's French twin) — keep the two wordings in step
    guidebook: "Guidebook p. {pages}",
    via: "Via",
    includes: "Includes",
    overnight: "Overnight",
    onBoard: "on board",
    bookedVia: "Booked via {source}",
    ref: "Ref {ref}",
    // the badge on each leg of a multi-leg transport booking — the same template
    // the PDF localizes via translations.py ("Leg {n}"); keep the two in step
    leg: "Leg {n}",
    driver: "{n} additional driver",
    drivers: "{n} additional drivers",
    nightIndex: "Night {n}/{total}",
    bookedWindow: "Booked {start} → {end}",
    bookedFrom: "Booked from {start}",
    contact: "Contact",
    flight: "Flight {number}",
    train: "Train {number}",
    road: "Road",
    overnightTravel: "Overnight travel",
    overnightType: "Overnight {type}",
    dayMapCaption: "Day {index} overview",
    areaMapCaption: "Zoom — {area}",
    tripMapCaption: "Whole trip",
    // A hike's embedded GPX: the trail map's caption and the elevation profile.
    // The first four are the same templates the PDF localizes via
    // translations.py ("Trail — {name}" / "Elevation profile" / "↑ {m} m" /
    // "↓ {m} m") — keep the wordings in step. `hikeProfileAlt` is screen-only
    // (the chart's accessible description; paper needs no alt text).
    hikeMapCaption: "Trail — {name}",
    hikeProfile: "Elevation profile",
    hikeAscent: "↑ {m} m",
    hikeDescent: "↓ {m} m",
    hikeProfileAlt: "Elevation profile over {km} km, from {low} m to {high} m",
    // Screen-only: hands back the .gpx the hike carries. Paper can't download a
    // file, so this has no PDF twin.
    getGpx: "(Get GPX track)",
    // A leg with no recording: the app builds the file from the drawn route, so
    // the link says so rather than borrowing the "get the track" wording.
    buildGpx: "(Build GPX file)",
    gpxFailed: "The GPX file couldn't be read.",
    gpxUnavailable: "No route to build a GPX file from.",
    buildingMap: "Building map…",
    noTripMap: "No coordinates on file — add coordinates (or turn maps on) to map the trip.",
    tripMapUnavailable: "The trip map couldn't be loaded.",
    // A day/area map slot with interactive maps ON that failed to load. There is
    // deliberately no fall back to the static PNG (see DayCard's MapView).
    mapUnavailable: "The interactive map couldn't be loaded.",
    noTransport: "No transport on file",
    noAccommodation: "No accommodation on file",
    // Moon phases (keys shared with the Python model's moon.py).
    moonNew: "New moon",
    moonWaxingCrescent: "Waxing crescent",
    moonFirstQuarter: "First quarter",
    moonWaxingGibbous: "Waxing gibbous",
    moonFull: "Full moon",
    moonWaningGibbous: "Waning gibbous",
    moonLastQuarter: "Last quarter",
    moonWaningCrescent: "Waning crescent",
    // The day's sun-times line. Same template the PDF localizes via
    // translations.py; the times themselves come resolved from the Python model.
    sunTimes: "☀️ Sunrise: {sunrise}, Sunset: {sunset}",
    // …and the same line closed by the night's moon phase, used when
    // show_moon_phase is on too (the phase then leaves the stay bar, so the day
    // never shows it twice). `{moon}` is filled with the localized phase name.
    sunTimesMoon: "☀️ Sunrise: {sunrise}, Sunset: {sunset}, {emoji} {moon}",
    // The bank-holiday banner opening a day (the day's `bank_holiday`). Same two
    // strings the PDF localizes via translations.py, where the label is keyed
    // uppercase; here CSS uppercases it — keep the wordings in step.
    bankHoliday: "Bank holiday",
    bankHolidayNote: "Expect closures and reduced opening hours.",
    // A point of interest's opening days/hours (its `opening`). The label is the
    // same English source the PDF localizes via translations.py; the weekday
    // abbreviations mirror lang/dates.py's `_WEEKDAY_ABBR`, Monday first — keep
    // both in step. The hours need no key: `hours_display` is digits only.
    open: "Open",
    wdMon: "Mon",
    wdTue: "Tue",
    wdWed: "Wed",
    wdThu: "Thu",
    wdFri: "Fri",
    wdSat: "Sat",
    wdSun: "Sun",
    // The trip's emergency contacts (`misc.emergency_contacts`), listed at the
    // foot of the 🗺️ Overview tab. The heading is the same English source the
    // PDF localizes via translations.py ("Emergency contacts", on its own final
    // page) — keep the two wordings in step. The contacts themselves are free
    // text and need no label; the viewer only turns a dialable one into a link.
    emergencyContacts: "Emergency contacts",
    // Weather-forecast condition labels (WMO codes → text; see weather.ts wmo()).
    wxClear: "Clear sky",
    wxMainlyClear: "Mainly clear",
    wxPartlyCloudy: "Partly cloudy",
    wxOvercast: "Overcast",
    wxFog: "Fog",
    wxDrizzle: "Drizzle",
    wxRain: "Rain",
    wxSnow: "Snow",
    wxRainShowers: "Rain showers",
    wxSnowShowers: "Snow showers",
    wxThunder: "Thunderstorm",
    wxUnknown: "Weather",
    wxPrecip: "☔ {p}%",
    wxWind: "💨 {v} km/h",
  },
  fr: {
    day: "Jour",
    overview: "Jour par jour",
    dayCol: "Jour",
    dateCol: "Date",
    activitiesCol: "Temps forts",
    sleepCol: "Nuit à",
    days: "jours",
    nights: "nuits",
    night: "nuit",
    tonight: "Cette nuit",
    aboard: "à bord",
    freeTime: "Pause",
    transport: "Transport",
    accommodation: "Hébergement",
    carRentals: "Locations de voiture",
    paid: "payé",
    toPay: "à payer",
    booked: "réservé",
    confirmed: "confirmé",
    breakfastIncluded: "petit-déjeuner inclus",
    pickUp: "Prise en charge",
    dropOff: "Restitution",
    pickUpCar: "Récupérer la voiture de location",
    dropOffCar: "Restituer la voiture de location",
    nowhere: "aucun hébergement renseigné",
    elevation: "dénivelé",
    distance: "distance",
    offRoad: "hors-piste",
    navigate: "Y aller",
    website: "Site web",
    reservation: "Réservation",
    guidebook: "Guide p. {pages}",
    via: "Via",
    includes: "Comprend",
    overnight: "De nuit",
    onBoard: "à bord",
    bookedVia: "Réservé via {source}",
    ref: "Réf {ref}",
    leg: "Trajet {n}",
    driver: "{n} conducteur supplémentaire",
    drivers: "{n} conducteurs supplémentaires",
    nightIndex: "Nuit {n}/{total}",
    bookedWindow: "Réservé {start} → {end}",
    bookedFrom: "Réservé à partir de {start}",
    contact: "Contact",
    flight: "Vol {number}",
    train: "Train {number}",
    road: "Route",
    overnightTravel: "Trajet de nuit",
    overnightType: "{type} de nuit",
    dayMapCaption: "Aperçu du jour {index}",
    areaMapCaption: "Zoom — {area}",
    tripMapCaption: "L'ensemble du voyage",
    hikeMapCaption: "Tracé — {name}",
    hikeProfile: "Profil altimétrique",
    hikeAscent: "↑ {m} m",
    hikeDescent: "↓ {m} m",
    hikeProfileAlt: "Profil altimétrique sur {km} km, de {low} m à {high} m",
    getGpx: "(Obtenir la trace GPX)",
    buildGpx: "(Générer le fichier GPX)",
    gpxFailed: "Le fichier GPX n'a pas pu être lu.",
    gpxUnavailable: "Aucun itinéraire pour générer un fichier GPX.",
    buildingMap: "Génération de la carte…",
    noTripMap:
      "Aucune coordonnée enregistrée — ajoutez des coordonnées (ou activez les cartes) pour cartographier le voyage.",
    tripMapUnavailable: "La carte du voyage n'a pas pu être chargée.",
    mapUnavailable: "La carte interactive n'a pas pu être chargée.",
    noTransport: "Aucun transport enregistré",
    noAccommodation: "Aucun hébergement enregistré",
    moonNew: "Nouvelle lune",
    moonWaxingCrescent: "Premier croissant",
    moonFirstQuarter: "Premier quartier",
    moonWaxingGibbous: "Lune gibbeuse croissante",
    moonFull: "Pleine lune",
    moonWaningGibbous: "Lune gibbeuse décroissante",
    moonLastQuarter: "Dernier quartier",
    moonWaningCrescent: "Dernier croissant",
    sunTimes: "☀️ Lever : {sunrise}, Coucher : {sunset}",
    sunTimesMoon: "☀️ Lever : {sunrise}, Coucher : {sunset}, {emoji} {moon}",
    bankHoliday: "Jour férié",
    bankHolidayNote: "Attendez-vous à des fermetures et à des horaires réduits.",
    open: "Ouvert",
    wdMon: "lun.",
    wdTue: "mar.",
    wdWed: "mer.",
    wdThu: "jeu.",
    wdFri: "ven.",
    wdSat: "sam.",
    wdSun: "dim.",
    emergencyContacts: "Numéros d'urgence",
    wxClear: "Ciel dégagé",
    wxMainlyClear: "Plutôt dégagé",
    wxPartlyCloudy: "Partiellement nuageux",
    wxOvercast: "Couvert",
    wxFog: "Brouillard",
    wxDrizzle: "Bruine",
    wxRain: "Pluie",
    wxSnow: "Neige",
    wxRainShowers: "Averses",
    wxSnowShowers: "Averses de neige",
    wxThunder: "Orage",
    wxUnknown: "Météo",
    wxPrecip: "☔ {p} %",
    wxWind: "💨 {v} km/h",
  },
} as const;

export type LabelKey = keyof (typeof LABELS)["en"];

export function tr(lang: Lang, key: LabelKey): string {
  return LABELS[lang][key];
}

// The canonical weekday keys an `Opening` speaks in (models/opening.py's
// WEEKDAYS) → their label key here. Monday first, like the model's week order.
const WEEKDAY_KEYS: Record<string, LabelKey> = {
  monday: "wdMon",
  tuesday: "wdTue",
  wednesday: "wdWed",
  thursday: "wdThu",
  friday: "wdFri",
  saturday: "wdSat",
  sunday: "wdSun",
};

/** A point of interest's opening-day runs, localized: `[["tuesday","sunday"]]`
 * → `Tue–Sun` / `mar.–dim.`, and a run of one day → that day alone. The runs
 * arrive already folded by the model, so this only names them — the mirror of
 * `lang/dates.py`'s `fmt_weekday_runs`, which the PDF uses. */
export function fmtWeekdayRuns(runs: [string, string][], lang: Lang): string {
  const name = (key: string) => {
    const label = WEEKDAY_KEYS[key];
    return label ? tr(lang, label) : key;
  };
  return runs
    .map(([first, last]) => (first === last ? name(first) : `${name(first)}–${name(last)}`))
    .join(", ");
}

/* -- display rounding for the two measured figures ---------------------------
 * Both are estimates — a distance is routed or read off a guidebook, a climb is
 * accumulated off a GPS altimeter — and the precision a reader can use falls
 * off with the magnitude: 8.4 km of walking is a different afternoon from 8.7,
 * while 341 km of driving and 342 are the same day behind the wheel. So the
 * step coarsens as the number grows. The mirror of `models/parsers.py`'s
 * `round_km` / `round_elevation`, which the PDF and the `.ics` use — keep the
 * two in step. Unit-less on purpose: some callers put a `+` or an `↑` in front.
 */

/** A distance in km snapped to 0.1 below 10, 0.5 up to 20, whole km above. */
export function roundKm(value: number): number {
  const step = value < 10 ? 0.1 : value <= 20 ? 0.5 : 1;
  return Math.round(Math.round(value / step) * step * 10) / 10;
}

/** A climb in metres snapped to 5 below 100, and to 10 from there up. */
export function roundElevation(value: number): number {
  const step = value < 100 ? 5 : 10;
  return Math.round(value / step) * step;
}

/** `"8.4 km"` — a rounded distance with its unit, `""` when unset. */
export function fmtKm(value: number | null | undefined): string {
  return value == null ? "" : `${roundKm(value)} km`;
}

/** `"780 m"` — a rounded climb with its unit, `""` when unset. */
export function fmtElevation(value: number | null | undefined): string {
  return value == null ? "" : `${roundElevation(value)} m`;
}

/** Fill {placeholders} in a label template. */
export function fill(
  template: string,
  vars: Record<string, string | number>,
): string {
  return template.replace(/\{(\w+)\}/g, (_, k) => String(vars[k] ?? ""));
}
