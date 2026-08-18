import type { SrcTransport } from "../../types/source";
import { TRANSPORT_FIELDS } from "../schema";
import { CoordinateField } from "../fields/CoordinateField";
import { FieldList } from "../fields/FieldList";

type Rec = Record<string, unknown>;

export interface TransportFormProps {
  value: SrcTransport;
  onChange: (next: SrcTransport) => void;
}

export function TransportForm({ value, onChange }: TransportFormProps) {
  const rec = value as unknown as Rec;
  const set = (next: Rec) => onChange(next as unknown as SrcTransport);

  return (
    <div className="transport-form">
      <FieldList specs={TRANSPORT_FIELDS} value={rec} onChange={set} />
      <CoordinateField
        label="Start coordinate"
        value={value.start_coordinate}
        onChange={(c) => set({ ...rec, start_coordinate: c })}
      />
      <CoordinateField
        label="End coordinate"
        value={value.end_coordinate}
        onChange={(c) => set({ ...rec, end_coordinate: c })}
      />
    </div>
  );
}
