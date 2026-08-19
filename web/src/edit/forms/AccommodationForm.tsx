import type { SrcAccommodation } from "../../types/source";
import { ACCOMMODATION_FIELDS } from "../schema";
import { CoordinateField } from "../fields/CoordinateField";
import { FieldFindings } from "../fields/FieldFindings";
import { FieldList } from "../fields/FieldList";

type Rec = Record<string, unknown>;

export interface AccommodationFormProps {
  value: SrcAccommodation;
  path: string;
  onChange: (next: SrcAccommodation) => void;
}

export function AccommodationForm({ value, path, onChange }: AccommodationFormProps) {
  const rec = value as unknown as Rec;
  const set = (next: Rec) => onChange(next as unknown as SrcAccommodation);

  return (
    <div className="accommodation-form">
      <div className="box-findings">
        <FieldFindings path={path} />
      </div>
      <FieldList specs={ACCOMMODATION_FIELDS} value={rec} path={path} onChange={set} />
      <CoordinateField
        path={`${path}.coordinate`}
        value={value.coordinate}
        geocodeQuery={
          [value.address || value.name, value.city].filter(Boolean).join(", ") || undefined
        }
        onChange={(c) => set({ ...rec, coordinate: c })}
      />
    </div>
  );
}
