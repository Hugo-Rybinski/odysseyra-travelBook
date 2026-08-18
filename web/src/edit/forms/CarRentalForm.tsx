import type { SrcCarRental } from "../../types/source";
import { CAR_RENTAL_FIELDS } from "../schema";
import { CoordinateField } from "../fields/CoordinateField";
import { FieldList } from "../fields/FieldList";

type Rec = Record<string, unknown>;

export interface CarRentalFormProps {
  value: SrcCarRental;
  path: string;
  onChange: (next: SrcCarRental) => void;
}

export function CarRentalForm({ value, path, onChange }: CarRentalFormProps) {
  const rec = value as unknown as Rec;
  const set = (next: Rec) => onChange(next as unknown as SrcCarRental);

  return (
    <div className="car-rental-form">
      <FieldList specs={CAR_RENTAL_FIELDS} value={rec} path={path} onChange={set} />
      <CoordinateField
        label="Pick-up coordinate"
        path={`${path}.pickup_coordinate`}
        value={value.pickup_coordinate}
        geocodeQuery={value.pickup_location}
        onChange={(c) => set({ ...rec, pickup_coordinate: c })}
      />
      <CoordinateField
        label="Drop-off coordinate"
        path={`${path}.dropoff_coordinate`}
        value={value.dropoff_coordinate}
        geocodeQuery={value.dropoff_location || value.pickup_location}
        onChange={(c) => set({ ...rec, dropoff_coordinate: c })}
      />
    </div>
  );
}
