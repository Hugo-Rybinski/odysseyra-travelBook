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
    freeTime: "Free time",
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
    nowhere: "no accommodation on file",
    elevation: "elevation",
    distance: "distance",
    offRoad: "off-road",
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
    freeTime: "Temps libre",
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
    nowhere: "aucun hébergement renseigné",
    elevation: "dénivelé",
    distance: "distance",
    offRoad: "hors-piste",
  },
} as const;

export type LabelKey = keyof (typeof LABELS)["en"];

export function tr(lang: Lang, key: LabelKey): string {
  return LABELS[lang][key];
}
