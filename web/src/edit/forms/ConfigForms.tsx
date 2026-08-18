import type { SrcDefaults, SrcSecondaryCurrency, SrcTravelDescription } from "../../types/source";
import {
  DEFAULTS_FIELDS,
  newSecondaryCurrency,
  SECONDARY_CURRENCY_FIELDS,
  TRAVEL_DESCRIPTION_FIELDS,
} from "../schema";
import { ArrayEditor } from "../fields/ArrayEditor";
import { FieldList } from "../fields/FieldList";

type Rec = Record<string, unknown>;

export function TravelDescriptionForm({
  value,
  onChange,
}: {
  value: SrcTravelDescription;
  onChange: (next: SrcTravelDescription) => void;
}) {
  return (
    <FieldList
      specs={TRAVEL_DESCRIPTION_FIELDS}
      value={value as unknown as Rec}
      onChange={(next) => onChange(next as unknown as SrcTravelDescription)}
    />
  );
}

export function DefaultsForm({
  value,
  onChange,
}: {
  value: SrcDefaults;
  onChange: (next: SrcDefaults) => void;
}) {
  const rec = value as unknown as Rec;
  const set = (next: Rec) => onChange(next as unknown as SrcDefaults);

  return (
    <div className="defaults-form">
      <FieldList specs={DEFAULTS_FIELDS} value={rec} onChange={set} />

      <section className="sub-array">
        <h4>Secondary currencies</h4>
        <ArrayEditor<SrcSecondaryCurrency>
          items={value.secondary_currencies ?? []}
          onChange={(list) => set({ ...rec, secondary_currencies: list })}
          itemTitle={(c, i) => c.currency || `Currency ${i + 1}`}
          add={[{ label: "currency", make: newSecondaryCurrency }]}
          emptyLabel="No secondary currencies."
          renderItem={(c, _i, onItemChange) => (
            <FieldList
              specs={SECONDARY_CURRENCY_FIELDS}
              value={c as unknown as Rec}
              onChange={(next) => onItemChange(next as unknown as SrcSecondaryCurrency)}
            />
          )}
        />
      </section>
    </div>
  );
}
