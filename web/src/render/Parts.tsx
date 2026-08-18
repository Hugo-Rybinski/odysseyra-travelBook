// Small shared render bits: a price (default currency + faded conversions and a
// paid/to-pay chip) and a booked/confirmed status chip.
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
  return <span className={`chip status ${status}`}>{tr(lang, status)}</span>;
}
