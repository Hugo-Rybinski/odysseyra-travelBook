import type { SrcTransport } from "../../types/source";
import { TRANSPORT_FIELDS } from "../schema";
import { CoordinateField } from "../fields/CoordinateField";
import { FieldList } from "../fields/FieldList";

type Rec = Record<string, unknown>;

export interface TransportFormProps {
  value: SrcTransport;
  path: string;
  onChange: (next: SrcTransport) => void;
}

export function TransportForm({ value, path, onChange }: TransportFormProps) {
  const rec = value as unknown as Rec;
  const set = (next: Rec) => onChange(next as unknown as SrcTransport);

  return (
    <div className="transport-form">
      <FieldList specs={TRANSPORT_FIELDS} value={rec} path={path} onChange={set} />
      <CoordinateField
        label="Start coordinate"
        path={`${path}.start_coordinate`}
        value={value.start_coordinate}
        geocodeQuery={value.start}
        onChange={(c) => set({ ...rec, start_coordinate: c })}
      />
      <CoordinateField
        label="End coordinate"
        path={`${path}.end_coordinate`}
        value={value.end_coordinate}
        geocodeQuery={value.end}
        onChange={(c) => set({ ...rec, end_coordinate: c })}
      />
    </div>
  );
}
