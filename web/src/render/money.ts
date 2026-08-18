// Money formatting for the viewer, mirroring models/currency.py: a price is
// shown in the trip's default currency, with any secondary-currency conversions
// faded alongside. Major currencies use their symbol (leading in English,
// trailing in French); others show the ISO code.
import type { Money } from "../types/resolved";

const SYMBOLS: Record<string, string> = { EUR: "€", USD: "$", GBP: "£", JPY: "¥" };

function fmtAmount(amount: number): string {
  return Math.abs(amount - Math.round(amount)) < 0.005
    ? String(Math.round(amount))
    : amount.toFixed(2);
}

// Converted (approximate) amounts: cents below 25, whole at/above.
function fmtConverted(amount: number): string {
  return Math.abs(amount) < 25 ? amount.toFixed(2) : String(Math.round(amount));
}

export function formatMoney(
  amount: number,
  code: string,
  lang: "en" | "fr" = "en",
  converted = false,
): string {
  const n = converted ? fmtConverted(amount) : fmtAmount(amount);
  const sym = SYMBOLS[(code || "").toUpperCase()];
  if (!sym) return `${n} ${code}`.trim();
  return lang === "fr" ? `${n} ${sym}` : `${sym}${n}`;
}

/** Primary display: the amount in the default currency (converted when needed),
 * falling back to the raw amount/currency if no rate is known. */
export function primaryMoney(price: Money, lang: "en" | "fr" = "en"): string {
  if (price.in_default != null) {
    const converted = price.currency !== price.default_currency;
    return formatMoney(price.in_default, price.default_currency, lang, converted);
  }
  return formatMoney(price.amount, price.currency, lang);
}

/** The faded "(≈ $279 · £218)" secondary conversions, or "" if none. */
export function secondaryMoney(price: Money, lang: "en" | "fr" = "en"): string {
  if (!price.secondaries.length) return "";
  const parts = price.secondaries.map((s) =>
    formatMoney(s.amount, s.currency, lang, true),
  );
  return `≈ ${parts.join(" · ")}`;
}
