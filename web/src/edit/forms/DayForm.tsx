import type { SrcActivity, SrcActivityType, SrcDay } from "../../types/source";
import { ACTIVITY_TYPES, ACTIVITY_TYPE_LABELS, DAY_FIELDS, newActivity } from "../schema";
import { useT } from "../../i18n";
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
  const t = useT();
  const rec = day as unknown as Rec;
  const set = (next: Rec) => onChange(next as unknown as SrcDay);

  return (
    <div className="day-form">
      <div className="box-findings">
        <FieldFindings path={path} />
      </div>
      <FieldList specs={DAY_FIELDS} value={rec} path={path} onChange={set} />

      <section className="sub-array">
        <h4>{t("Activities")}</h4>
        <ArrayEditor<SrcActivity>
          items={day.activities ?? []}
          onChange={(acts) => set({ ...rec, activities: acts })}
          basePath={`${path}.activities`}
          defaultOpen={false}
          itemTitle={(a, i) => activityTitle(a, i, t)}
          add={ACTIVITY_TYPES.map((ty: SrcActivityType) => ({
            label: t(ACTIVITY_TYPE_LABELS[ty]).toLowerCase(),
            make: () => newActivity(ty),
          }))}
          emptyLabel={t("No activities — a day needs at least one.")}
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
