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
//   * `linkifyProse` — is there a URL, an email address or a number **inside
//     this sentence**? Used for every description the book prints, via `Clamp`.
//     Unanchored, and much *stricter*: a loose rule let into prose would happily
//     claim `09:30-18:00`, `12 km`, a guidebook range `25-30` or a year span
//     `1789-1799`, and a link that goes to the wrong place is worse than one
//     that isn't there.
//
// **The PDF implements the same in-prose rule**, in `prose_links.py`, drawn
// through fpdf2's markdown (`pdf/base.py`'s `_prose_markup`) and switched off
// under `--ink-saver` like every other hyperlink there. Keep the two in step;
// `tests/test_prose_links.py` is the contract both sides answer to. Only
// `contactHref` is viewer-only, and only because the *whole-field* case has a
// PDF row that already prints the value in full.

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

// Candidates only: a URL, an email-shaped run, or a `+`-led / bare run of digits
// and the separators a written number uses. `:` and `,` are deliberately *not*
// separators — they are what a time and a page list are made of — so
// `09:30-18:00` never reaches the classifier as one token, it arrives as four
// two-digit ones and every branch below rejects those on length.
//
// The URL alternative comes **first** so it is tried at each position before the
// others: `https://x.com/1234567890` has to be consumed whole rather than
// leaving its digits behind to be read as a number.
const CANDIDATE =
  /(?:https?:\/\/|www\.)[^\s<>"'[\]]+|[A-Za-z0-9._%+-]+@[A-Za-z0-9][A-Za-z0-9.-]*[A-Za-z0-9]|\+?\d[\d .()-]*\d/g;

const PROSE_MAIL = /^[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,}$/;

/** Sentence punctuation a URL may collect but never own. */
const URL_TRAIL = /[.,;:!?'"“”’«»]+$/;

/** Drop the sentence punctuation a URL swept up, and a closing bracket that was
 *  opened outside it — while keeping the one in `…/wiki/Foo_(bar)`, which is
 *  part of the address. */
function trimUrl(token: string): string {
  let t = token.replace(URL_TRAIL, "");
  while (t.endsWith(")") && (t.split(")").length - 1) > (t.split("(").length - 1)) {
    t = t.slice(0, -1).replace(URL_TRAIL, "");
  }
  return t;
}

/** A URL must **name itself** — `https://…` or a `www.` host. A bare
 *  `example.com` is deliberately not enough: `trip.json`, `p.m.` and a sentence
 *  that runs "…the abbey.Or the château" all look the same to that pattern, and
 *  the cost of guessing wrong is a link to nowhere. */
const URL_LED = /^(?:https?:\/\/|www\.)/i;

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
    // Each branch trims its own trailing punctuation: a URL keeps a `(bar)` that
    // is part of the address, where a number's brackets never are.
    let token: string;
    let href: string | null;
    if (URL_LED.test(m[0])) {
      token = trimUrl(m[0]);
      // "www.a.bc" is the shortest thing worth pointing at.
      href = token.length >= 8 ? (/^http/i.test(token) ? token : `https://${token}`) : null;
    } else if (PROSE_MAIL.test(m[0])) {
      token = m[0];
      href = `mailto:${token}`;
    } else {
      token = m[0].replace(/[ .()-]+$/, "");
      href = dialable(token) ? `tel:${token.replace(/[^\d+]/g, "")}` : null;
    }
    if (!token || !href) continue;

    const before = start > 0 ? text[start - 1] : "";
    const after = text[start + token.length] ?? "";
    if (GLUED.test(before) || before === "." || before === "+" || before === "-") continue;
    if (GLUED.test(after)) continue;

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
