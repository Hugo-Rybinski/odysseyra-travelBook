import type { SrcActivity, SrcActivityType, SrcDay } from "../../types/source";
import { ACTIVITY_TYPES, ACTIVITY_TYPE_LABELS, DAY_FIELDS, newActivity } from "../schema";
import { ArrayEditor } from "../fields/ArrayEditor";
import { FieldFindings } from "../fields/FieldFindings";
import { FieldList } from "../fields/FieldList";
import { ActivityForm, activityTitle } from "./ActivityForm";

type Rec = Record<string, unknown>;

export interface DayFormProps {
  day: SrcDay;
  path: string;
  onChange: (next: SrcDay) => void;
}

export function DayForm({ day, path, onChange }: DayFormProps) {
  const rec = day as unknown as Rec;
  const set = (next: Rec) => onChange(next as unknown as SrcDay);

  return (
    <div className="day-form">
      <div className="box-findings">
        <FieldFindings path={path} />
      </div>
      <FieldList specs={DAY_FIELDS} value={rec} path={path} onChange={set} />

      <section className="sub-array">
        <h4>Activities</h4>
        <ArrayEditor<SrcActivity>
          items={day.activities ?? []}
          onChange={(acts) => set({ ...rec, activities: acts })}
          basePath={`${path}.activities`}
          defaultOpen={false}
          itemTitle={activityTitle}
          add={ACTIVITY_TYPES.map((t: SrcActivityType) => ({
            label: ACTIVITY_TYPE_LABELS[t].toLowerCase(),
            make: () => newActivity(t),
          }))}
          emptyLabel="No activities — a day needs at least one."
          renderItem={(a, _i, onItemChange, itemPath) => (
            <ActivityForm
              activity={a}
              path={itemPath}
              onChange={onItemChange}
              allowedTypes={ACTIVITY_TYPES}
              allowNesting
            />
          )}
        />
      </section>
    </div>
  );
}
