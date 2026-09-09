// Turning a phone number or an email address into something tappable.
//
// Two jobs, deliberately kept apart because they ask different questions of the
// same text:
//
//   * `contactHref` — is this **whole value** a number or an address? Used for
//     the fields that hold nothing else: `misc.emergency_contacts[].contact` and
//     an activity's `contact`. Anchored, and generous with what it accepts,
//     because the alternative is a value that is obviously a number and not a
//     link — a bare `112` or `15` is exactly the number you most want to tap.
//
//   * `linkifyProse` — is there a number **inside this sentence**? Used for
//     every description the book prints, via `Clamp`. Unanchored, and much
//     *stricter*: a loose rule let into prose would happily claim `09:30-18:00`,
//     `12 km`, a guidebook range `25-30` or a year span `1789-1799`, and a
//     number that dials the wrong thing is worse than one that doesn't dial.
//
// There is no PDF twin, which is the same divergence `(Get GPX track)` has: fpdf
// can emit a link and most readers honour `tel:`, but on paper the number is
// already legible, a link would print as accent emphasis on a page that spends
// its accent elsewhere, and `--ink-saver` drops every hyperlink anyway — so the
// affordance would exist only in the one mode the book isn't printed in.

import type { ReactNode } from "react";

// --- the whole-value rules (an entire field is the contact) ------------------

// `tel:` strips everything a dialler doesn't want (spaces, dots, brackets,
// dashes) but keeps a leading + and the digits — including a short code like
// "112" or "15".
const DIALABLE = /^\+?[\d\s.()/-]{2,}$/;
const MAILABLE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

/** A `tel:` / `mailto:` target for a field that holds only a contact, or null
 *  for an address, a sentence — anything with nothing to hand an app. */
export function contactHref(contact: string): string | null {
  if (MAILABLE.test(contact)) return `mailto:${contact}`;
  if (DIALABLE.test(contact)) return `tel:${contact.replace(/[^\d+]/g, "")}`;
  return null;
}

// --- the in-prose rule (a number sitting inside a sentence) -----------------

// Candidates only: an email-shaped run, or a `+`-led / bare run of digits and
// the separators a written number uses. `:` and `,` are deliberately *not*
// separators — they are what a time and a page list are made of — so
// `09:30-18:00` never reaches the classifier as one token, it arrives as four
// two-digit ones and every branch below rejects those on length.
const CANDIDATE = /[A-Za-z0-9._%+-]+@[A-Za-z0-9][A-Za-z0-9.-]*[A-Za-z0-9]|\+?\d[\d .()-]*\d/g;

const PROSE_MAIL = /^[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,}$/;

/** A character that, sitting against a candidate, says it is part of something
 *  larger: a word, an address, a time, a date, a decimal, a fraction — or a URL,
 *  which is why the query-string punctuation is in here too (`?id=1234567890` is
 *  not a phone number, and a `description` may well carry a booking link). */
const GLUED = /[\w@:/=?&#%~]/;

const SEPARATORS = /[ .()-]/g;

/** How many digits a number needs before we will dial it.
 *
 *  A leading `+` is its own evidence — nothing else written in a trip file opens
 *  that way — so it only has to be long enough to be a number at all. Without
 *  one the floor is a full national number: 9 digits clears every date (8),
 *  price, distance, altitude and page range a description carries. */
const MIN_DIGITS_INTL = 7;
const MIN_DIGITS_LOCAL = 9;

function dialable(token: string): boolean {
  const digits = token.replace(/\D/g, "").length;
  if (token.startsWith("+")) return digits >= MIN_DIGITS_INTL;
  if (digits < MIN_DIGITS_LOCAL) return false;
  // A single separator, and a decimal is the likelier reading: `1234.56789` is
  // nine digits and not a phone number, while a real one is either grouped
  // (`01 42 60 30 30`, `+1 (212) 555-1234`) or solid (`0142603030`). Costs us a
  // number written with exactly one space, which is not how anyone writes one.
  const seps = token.match(SEPARATORS)?.length ?? 0;
  return seps === 0 || seps >= 2;
}

/** Split a paragraph into text and `tel:` / `mailto:` links.
 *
 *  Returns the string itself when nothing matched, so the common case adds no
 *  wrapper element and no array to the tree. */
export function linkifyProse(text: string): ReactNode {
  const out: ReactNode[] = [];
  let last = 0;
  let key = 0;

  for (const m of text.matchAll(CANDIDATE)) {
    const start = m.index ?? 0;
    // Trim the trailing separators the class swept up — a sentence's full stop,
    // a closing bracket that opened outside the match.
    const token = m[0].replace(/[ .()-]+$/, "");
    if (!token) continue;
    const before = start > 0 ? text[start - 1] : "";
    const after = text[start + token.length] ?? "";
    if (GLUED.test(before) || before === "." || before === "+" || before === "-") continue;
    if (GLUED.test(after)) continue;

    const href = PROSE_MAIL.test(token)
      ? `mailto:${token}`
      : dialable(token)
        ? `tel:${token.replace(/[^\d+]/g, "")}`
        : null;
    if (!href) continue;

    if (start > last) out.push(text.slice(last, start));
    out.push(
      <a className="prose-link" key={key++} href={href}>
        {token}
      </a>,
    );
    last = start + token.length;
  }

  if (!out.length) return text;
  if (last < text.length) out.push(text.slice(last));
  return out;
}
