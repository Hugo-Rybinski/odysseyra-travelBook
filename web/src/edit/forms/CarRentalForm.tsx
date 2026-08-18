import type { SrcCarRental } from "../../types/source";
import { CAR_RENTAL_FIELDS } from "../schema";
import { CoordinateField } from "../fields/CoordinateField";
import { FieldList } from "../fields/FieldList";

type Rec = Record<string, unknown>;

export interface CarRentalFormProps {
  value: SrcCarRental;
  onChange: (next: SrcCarRental) => void;
}

export function CarRentalForm({ value, onChange }: CarRentalFormProps) {
  const rec = value as unknown as Rec;
  const set = (next: Rec) => onChange(next as unknown as SrcCarRental);

  return (
    <div className="car-rental-form">
      <FieldList specs={CAR_RENTAL_FIELDS} value={rec} onChange={set} />
      <CoordinateField
        label="Pick-up coordinate"
        value={value.pickup_coordinate}
        onChange={(c) => set({ ...rec, pickup_coordinate: c })}
      />
      <CoordinateField
        label="Drop-off coordinate"
        value={value.dropoff_coordinate}
        onChange={(c) => set({ ...rec, dropoff_coordinate: c })}
      />
    </div>
  );
}
