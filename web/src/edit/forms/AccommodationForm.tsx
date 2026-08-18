import type { SrcAccommodation } from "../../types/source";
import { ACCOMMODATION_FIELDS } from "../schema";
import { CoordinateField } from "../fields/CoordinateField";
import { FieldList } from "../fields/FieldList";

type Rec = Record<string, unknown>;

export interface AccommodationFormProps {
  value: SrcAccommodation;
  onChange: (next: SrcAccommodation) => void;
}

export function AccommodationForm({ value, onChange }: AccommodationFormProps) {
  const rec = value as unknown as Rec;
  const set = (next: Rec) => onChange(next as unknown as SrcAccommodation);

  return (
    <div className="accommodation-form">
      <FieldList specs={ACCOMMODATION_FIELDS} value={rec} onChange={set} />
      <CoordinateField value={value.coordinate} onChange={(c) => set({ ...rec, coordinate: c })} />
    </div>
  );
}
