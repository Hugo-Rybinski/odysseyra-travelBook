// Small shared render bits: a price (default currency + faded conversions and a
// paid/to-pay chip), a booked/confirmed status chip, and a collapsible card head.
import type { ReactNode } from "react";
import type { Money } from "../types/resolved";
import { primaryMoney, secondaryMoney } from "./money";
import { tr, type Lang } from "./format";

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
