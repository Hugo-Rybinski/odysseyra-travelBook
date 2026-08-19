import type { SrcDefaults, SrcSecondaryCurrency, SrcTravelDescription } from "../../types/source";
import {
  DEFAULTS_FIELDS,
  newSecondaryCurrency,
  SECONDARY_CURRENCY_FIELDS,
  TRAVEL_DESCRIPTION_FIELDS,
} from "../schema";
import { ArrayEditor } from "../fields/ArrayEditor";
import { FieldFindings } from "../fields/FieldFindings";
import { FieldList } from "../fields/FieldList";

type Rec = Record<string, unknown>;

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
  const rec = value as unknown as Rec;
  const set = (next: Rec) => onChange(next as unknown as SrcDefaults);

  return (
    <div className="defaults-form">
      <div className="box-findings">
        <FieldFindings path={path} />
      </div>
      <FieldList specs={DEFAULTS_FIELDS} value={rec} path={path} onChange={set} />

      <section className="sub-array">
        <h4>Secondary currencies</h4>
        <ArrayEditor<SrcSecondaryCurrency>
          items={value.secondary_currencies ?? []}
          onChange={(list) => set({ ...rec, secondary_currencies: list })}
          basePath={`${path}.secondary_currencies`}
          itemTitle={(c, i) => c.currency || `Currency ${i + 1}`}
          add={[{ label: "currency", make: newSecondaryCurrency }]}
          emptyLabel="No secondary currencies."
          renderItem={(c, _i, onItemChange, itemPath) => (
            <FieldList
              specs={SECONDARY_CURRENCY_FIELDS}
              value={c as unknown as Rec}
              path={itemPath}
              onChange={(next) => onItemChange(next as unknown as SrcSecondaryCurrency)}
            />
          )}
        />
      </section>
    </div>
  );
}
