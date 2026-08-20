import type { SrcDefaults, SrcSecondaryCurrency, SrcTravelDescription } from "../../types/source";
import {
  DEFAULTS_FIELDS,
  newSecondaryCurrency,
  SECONDARY_CURRENCY_FIELDS,
  TRAVEL_DESCRIPTION_FIELDS,
} from "../schema";
import { useT } from "../../i18n";
import { ArrayEditor } from "../fields/ArrayEditor";
import { FieldFindings } from "../fields/FieldFindings";
import { FieldList } from "../fields/FieldList";

type Rec = Record<string, unknown>;

// Round to 4 significant digits and drop trailing zeros (1.08, 0.9259, 150).
function fmtRate(n: number): string {
  return parseFloat(n.toPrecision(4)).toString();
}

// A two-way readout of a secondary currency's rate, shown live inside its box:
// "1 USD = 0.926 EUR and 1 EUR = 1.08 USD". `change_rate` is units of the
// secondary per one unit of the default, so it *is* "new per main"; its inverse
// is "main per new". Hidden until both a code and a positive rate are present.
function ConversionHint({
  secondary,
  defaultCurrency,
}: {
  secondary: SrcSecondaryCurrency;
  defaultCurrency: string;
}) {
  const t = useT();
  const code = (secondary.currency ?? "").trim().toUpperCase();
  const rate = secondary.change_rate;
  if (!code || typeof rate !== "number" || !Number.isFinite(rate) || rate <= 0) return null;
  return (
    <p className="currency-conversion">
      {t("1 {new} = {x} {main} and 1 {main} = {y} {new}", {
        new: code,
        main: defaultCurrency,
        x: fmtRate(1 / rate),
        y: fmtRate(rate),
      })}
    </p>
  );
}

export function TravelDescriptionForm({
  value,
  path,
  onChange,
}: {
  value: SrcTravelDescription;
  path: string;
  onChange: (next: SrcTravelDescription) => void;
}) {
  return (
    <div className="travel-description-form">
      <div className="box-findings">
        <FieldFindings path={path} />
      </div>
      <FieldList
        specs={TRAVEL_DESCRIPTION_FIELDS}
        value={value as unknown as Rec}
        path={path}
        onChange={(next) => onChange(next as unknown as SrcTravelDescription)}
      />
    </div>
  );
}

export function DefaultsForm({
  value,
  path,
  onChange,
}: {
  value: SrcDefaults;
  path: string;
  onChange: (next: SrcDefaults) => void;
}) {
  const t = useT();
  const rec = value as unknown as Rec;
  const set = (next: Rec) => onChange(next as unknown as SrcDefaults);

  return (
    <div className="defaults-form">
      <div className="box-findings">
        <FieldFindings path={path} />
      </div>
      <FieldList specs={DEFAULTS_FIELDS} value={rec} path={path} onChange={set} />

      <section className="sub-array">
        <h4>{t("Secondary currencies")}</h4>
        <ArrayEditor<SrcSecondaryCurrency>
          items={value.secondary_currencies ?? []}
          onChange={(list) => set({ ...rec, secondary_currencies: list })}
          basePath={`${path}.secondary_currencies`}
          itemTitle={(c, i) => c.currency || t("Currency {n}", { n: i + 1 })}
          add={[{ label: t("currency"), make: newSecondaryCurrency }]}
          emptyLabel={t("No secondary currencies.")}
          renderItem={(c, _i, onItemChange, itemPath) => (
            <>
              <FieldList
                specs={SECONDARY_CURRENCY_FIELDS}
                value={c as unknown as Rec}
                path={itemPath}
                onChange={(next) => onItemChange(next as unknown as SrcSecondaryCurrency)}
              />
              <ConversionHint
                secondary={c}
                defaultCurrency={(value.currency ?? "").trim().toUpperCase() || "EUR"}
              />
            </>
          )}
        />
      </section>
    </div>
  );
}
