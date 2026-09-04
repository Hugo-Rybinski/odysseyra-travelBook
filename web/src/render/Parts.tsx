// Small shared render bits: a price (default currency + faded conversions and a
// paid/to-pay chip), a booked/confirmed status chip, a collapsible card head,
// and the captioned figure a pre-rendered map PNG is drawn in.
import type { ReactNode } from "react";
import type { Money, RenderedMap } from "../types/resolved";
import { primaryMoney, secondaryMoney } from "./money";
import { tr, type Lang } from "./format";

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
