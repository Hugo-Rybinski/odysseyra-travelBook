// The bundled Demo's dates, moved onto the calendar you're reading it on.
//
// `examples/france.json` is a fixed September-2026 trip, and has to be: it is
// the flagship the example PDFs and the tests are built from, so its dates are
// pinned there. Opened in the viewer, though, a trip that sits entirely in the
// past (or entirely in the future) shows none of what the book does with *where
// you are* — today's day band, the past days folded away behind their one line,
// the near-term weather forecast. So the Demo, and only the Demo, is shifted so
// its **second day is today**: one day behind you, the day you're on, the rest
// still to come.
//
// Three things are deliberate:
//
//   - **It rewrites the text, not a parsed document.** Only the date literals
//     change, so what the Edit tab seeds from, the autosave keeps and an export
//     renders is the demo file as written — formatting, key order and every key
//     this module has never heard of included. A parse-then-stringify would
//     reformat the whole thing. The one parse below is for *reading* the anchor.
//   - **It shifts any string value that is exactly an ISO date, whatever its
//     key.** There are nine of those keys today (`date`, `start_date`/`end_date`,
//     `arrival`/`departure`, `booking_start_date`/`booking_end_date`,
//     `pickup_date`/`dropoff_date`) and a tenth costs nothing; prose is never an
//     exact match, so a description that mentions a date is left alone.
//   - **The offset is whole days, and pinned** — "today is day 2" leaves no room
//     to also keep the weekdays, so they move. That is visible in the Demo: the
//     Louvre is open `wed-mon`, so opening it on a Tuesday puts that visit on the
//     one day the museum is shut and the validator says so. Real data, check
//     working.
//
// It also means the document's content — and so its hash — changes each calendar
// day, which is the map cache's key: the Demo redraws its maps once a day, and
// `dropStaleVersions` drops the previous day's set (both are `france.json`, the
// same document) rather than leaking it.
import { todayISO } from "../render/collapse";

// A JSON string value holding nothing but a date. Anchored on its own quotes, so
// it can't match inside a sentence.
const DATE_LITERAL = /"(\d{4}-\d{2}-\d{2})"/g;

const DAY_MS = 86_400_000;

// UTC throughout: a local-midnight arithmetic would gain or lose an hour across
// a DST boundary and land the shift a day out.
function toUTC(iso: string): number {
  const [y, m, d] = iso.split("-").map(Number);
  return Date.UTC(y, m - 1, d);
}

function addDays(iso: string, days: number): string {
  return new Date(toUTC(iso) + days * DAY_MS).toISOString().slice(0, 10);
}

/** The date the shift is measured from: the second day's own. Falls back to the
 * earliest date anywhere in the document plus one — a day with no `date` is
 * inferred as trip-start + its index, and the trip's start is the earliest date
 * across its days, transport and stays. Null when the document holds no date at
 * all: an undated trip has nothing to move. */
function anchorDate(text: string, earliest: string | null): string | null {
  try {
    const days = (JSON.parse(text) as { days?: { date?: unknown }[] }).days;
    const second = Array.isArray(days) && days.length > 1 ? days[1]?.date : null;
    if (typeof second === "string" && /^\d{4}-\d{2}-\d{2}$/.test(second)) return second;
  } catch {
    // Not valid JSON — `analyze` is about to report that properly. Fall through
    // to the earliest literal, which needs no parse.
  }
  return earliest == null ? null : addDays(earliest, 1);
}

/** Shift every date in the Demo's JSON text so that `today` is its second day.
 * Returns the text unchanged when there is nothing to move, or when it already
 * lands there. */
export function shiftDemoDates(text: string, today: string = todayISO()): string {
  const found = [...text.matchAll(DATE_LITERAL)].map((m) => m[1]);
  if (!found.length) return text;
  const anchor = anchorDate(text, found.reduce((a, b) => (b < a ? b : a)));
  if (anchor == null) return text;
  const offset = Math.round((toUTC(today) - toUTC(anchor)) / DAY_MS);
  if (offset === 0) return text;
  return text.replace(DATE_LITERAL, (_, d: string) => `"${addDays(d, offset)}"`);
}
