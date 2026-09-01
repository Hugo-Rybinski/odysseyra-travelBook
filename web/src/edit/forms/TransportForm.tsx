import type { SrcTransport, SrcTransportLeg } from "../../types/source";
import { TRANSPORT_FIELDS, TRANSPORT_LEG_FIELDS, newTransportLeg } from "../schema";
import { CoordinateField } from "../fields/CoordinateField";
import { FieldFindings } from "../fields/FieldFindings";
import { FieldList } from "../fields/FieldList";
import { ArrayEditor } from "../fields/ArrayEditor";
import { useT } from "../../i18n";

type Rec = Record<string, unknown>;

export interface TransportFormProps {
  value: SrcTransport;
  path: string;
  onChange: (next: SrcTransport) => void;
}

// A booking's reservation fields, then its legs as a sub-array (the same shape a
// road's legs use). The coordinates belong to a leg's endpoints, not to the
// booking, so they sit inside each leg's item.
export function TransportForm({ value, path, onChange }: TransportFormProps) {
  const t = useT();
  const rec = value as unknown as Rec;
  const set = (next: Rec) => onChange(next as unknown as SrcTransport);

  return (
    <div className="transport-form">
      <div className="box-findings">
        <FieldFindings path={path} />
      </div>
      <FieldList specs={TRANSPORT_FIELDS} value={rec} path={path} onChange={set} />

      <section className="sub-array">
        <h4>{t("Legs")}</h4>
        <div className="box-findings">
          <FieldFindings path={`${path}.legs`} />
        </div>
        <ArrayEditor<SrcTransportLeg>
          items={value.legs ?? []}
          onChange={(legs) => set({ ...rec, legs })}
          basePath={`${path}.legs`}
          defaultOpen={false}
          itemTitle={(leg, i) =>
            [leg.start, leg.end].filter(Boolean).join(" → ") || t("Leg {n}", { n: i + 1 })
          }
          add={[{ label: t("leg"), make: newTransportLeg }]}
          emptyLabel={t("No legs — a transport needs at least one (a single-hop booking has one).")}
          renderItem={(leg, _i, onItemChange, itemPath) => (
            <>
              <div className="box-findings">
                <FieldFindings path={itemPath} />
              </div>
              <FieldList
                specs={TRANSPORT_LEG_FIELDS}
                value={leg as unknown as Rec}
                path={itemPath}
                onChange={(next) => onItemChange(next as unknown as SrcTransportLeg)}
              />
              <CoordinateField
                label="Start coordinate"
                path={`${itemPath}.start_coordinate`}
                value={leg.start_coordinate}
                geocodeQuery={leg.start}
                onChange={(c) => onItemChange({ ...leg, start_coordinate: c })}
              />
              <CoordinateField
                label="End coordinate"
                path={`${itemPath}.end_coordinate`}
                value={leg.end_coordinate}
                geocodeQuery={leg.end}
                onChange={(c) => onItemChange({ ...leg, end_coordinate: c })}
              />
            </>
          )}
        />
      </section>
    </div>
  );
}
