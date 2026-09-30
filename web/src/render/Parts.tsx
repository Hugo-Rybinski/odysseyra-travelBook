// Small shared render bits: a price (default currency + faded conversions and a
// paid/to-pay chip), a booked/confirmed status chip, a collapsible card head,
// the one line a folded-away run of past entries leaves behind, and the
// captioned figure a pre-rendered map PNG is drawn in.
import { useCallback, useEffect, useState, type ReactNode } from "react";
import type { Money, RenderedMap } from "../types/resolved";
import { primaryMoney, secondaryMoney } from "./money";
import { fill, tr, type Lang, type LabelKey } from "./format";

/** One pre-rendered map image with its caption — a day's map, an area's zoom, or
 * a hike's trail. Shown only with the Options interactive-maps toggle **off**
 * (see `MapView` in DayCard.tsx): the PNG and the MapLibre map are alternatives,
 * so a GL failure never substitutes this one. */
export function MapFigure({ rendered, caption }: { rendered: RenderedMap; caption: string }) {
  return (
    <figure className="day-map">
      <figcaption>{caption}</figcaption>
      <img src={rendered.image} alt={caption} loading="lazy" />
    </figure>
  );
}

/** The state behind a `PastFold`: whether the folded-away run is on screen.
 *
 * It starts **revealed when every entry is past** — a list already lived
 * through. Folding then leaves one line where the whole list should be, which
 * reads as a broken render rather than a tidy one: there is nothing below the
 * run to get to, because it *is* the list. The line then reads "Hide …" and is
 * how you put it away.
 *
 * `folded` is the fold set (`foldedForItems`, or its day-number mapping) and
 * doubles as the re-fold signal: a caller memoizes it per view + list, so a new
 * identity means one of those changed and the run folds back — to `allPast`,
 * not to false.
 *
 * `reveal` is for a jump from outside the list: a folded-away entry has no
 * element to scroll to. */
export function usePastFold<T>(folded: Set<T>, allPast: boolean) {
  const [shown, setShown] = useState(allPast);
  useEffect(() => setShown(allPast), [folded, allPast]);
  const toggle = useCallback(() => setShown((s) => !s), []);
  const reveal = useCallback(() => setShown(true), []);
  return {
    shown,
    toggle,
    reveal,
    /** Is this entry folded away right now (so: render no card for it)? */
    hidden: (key: T) => !shown && folded.has(key),
  };
}

/** The single line a folded-away run of past entries leaves behind, in place of
 * their cards (see `foldedForItems`). One component for the four lists that
 * fold — days, transport bookings, car rentals, stays — so the seam looks and
 * behaves the same in each; only the wording differs, which is why the two
 * label keys are the caller's to name ("days" / "bookings" / "rentals" /
 * "stays"). It sits at the head of its list, where those entries are: a list in
 * file order is normally in trip order, so what is behind you is at the top. */
export function PastFold({
  n,
  shown,
  onToggle,
  lang,
  showKey,
  hideKey,
}: {
  n: number;
  shown: boolean;
  onToggle: () => void;
  lang: Lang;
  showKey: LabelKey;
  hideKey: LabelKey;
}) {
  if (n <= 0) return null;
  return (
    <button
      type="button"
      className="past-days"
      aria-expanded={shown}
      onClick={onToggle}
    >
      <span className="past-days-caret" aria-hidden>
        {shown ? "▾" : "▸"}
      </span>
      {fill(tr(lang, shown ? hideKey : showKey), { n })}
    </button>
  );
}

export function Price({ price, lang }: { price: Money | null; lang: Lang }) {
  if (!price) return null;
  const secondary = secondaryMoney(price, lang);
  return (
    <span className="price">
      <span className="price-main">{primaryMoney(price, lang)}</span>
      {secondary && <span className="price-sec">{secondary}</span>}
      {price.paid === true && <span className="chip paid">{tr(lang, "paid")}</span>}
      {price.paid === false && <span className="chip topay">{tr(lang, "toPay")}</span>}
    </span>
  );
}

export function Status({ status, lang }: { status: string; lang: Lang }) {
  if (status !== "booked" && status !== "confirmed") return null;
  // Confirmed is emphasized (filled); booked is de-emphasized (outline).
  const emphasis = status === "confirmed" ? "filled" : "outline";
  return <span className={`chip status ${emphasis}`}>{tr(lang, status)}</span>;
}

// A clickable card header that toggles its card open/closed (with a caret).
export function CardHead({
  collapsed,
  onToggle,
  children,
}: {
  collapsed: boolean;
  onToggle: () => void;
  children: ReactNode;
}) {
  return (
    <div
      className="card-head"
      role="button"
      tabIndex={0}
      aria-expanded={!collapsed}
      onClick={onToggle}
      onKeyDown={(e) => {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          onToggle();
        }
      }}
    >
      {children}
      <span className="card-caret" aria-hidden>
        {collapsed ? "▸" : "▾"}
      </span>
    </div>
  );
}
