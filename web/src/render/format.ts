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
    via: "Via",
    includes: "Includes",
    overnight: "Overnight",
    onBoard: "on board",
    bookedVia: "Booked via {source}",
    ref: "Ref {ref}",
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
    buildingMap: "Building map…",
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
    via: "Via",
    includes: "Comprend",
    overnight: "De nuit",
    onBoard: "à bord",
    bookedVia: "Réservé via {source}",
    ref: "Réf {ref}",
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
    buildingMap: "Génération de la carte…",
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

/** Fill {placeholders} in a label template. */
export function fill(
  template: string,
  vars: Record<string, string | number>,
): string {
  return template.replace(/\{(\w+)\}/g, (_, k) => String(vars[k] ?? ""));
}
