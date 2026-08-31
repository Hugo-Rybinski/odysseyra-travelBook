import { type ReactNode } from "react";
import { countLevelsUnder, FINDING_ICON, useFindingIndex } from "../findings";
import { useT } from "../../i18n";

// A generic editor for an array of objects: each item is a card with a header
// (its title + move up/down + remove) and a body rendered by the caller. New
// items are added from one or more "Add" options (a single option → one button;
// several → a button per option, e.g. the six activity types).
export interface AddOption<T> {
  label: string;
  make: () => T;
}

export interface ArrayEditorProps<T> {
  items: T[];
  onChange: (next: T[]) => void;
  // Dot-path of the array itself; each item's path is `${basePath}.${index}`,
  // passed to renderItem so nested fields can anchor validation findings.
  basePath: string;
  itemTitle: (item: T, index: number) => ReactNode;
  renderItem: (item: T, index: number, onItemChange: (next: T) => void, path: string) => ReactNode;
  add: AddOption<T>[];
  emptyLabel?: string;
  className?: string;
  // Whether items start expanded. Days/activities default collapsed so a big
  // itinerary is scannable; a badge on the header flags hidden findings.
  defaultOpen?: boolean;
}

export function ArrayEditor<T>({
  items,
  onChange,
  basePath,
  itemTitle,
  renderItem,
  add,
  emptyLabel,
  className = "",
  defaultOpen = true,
}: ArrayEditorProps<T>) {
  const t = useT();
  const { byPath: findingsMap } = useFindingIndex();
  const replaceAt = (i: number, next: T) => {
    const copy = items.slice();
    copy[i] = next;
    onChange(copy);
  };
  const removeAt = (i: number) => {
    const copy = items.slice();
    copy.splice(i, 1);
    onChange(copy);
  };
  const move = (i: number, dir: -1 | 1) => {
    const j = i + dir;
    if (j < 0 || j >= items.length) return;
    const copy = items.slice();
    [copy[i], copy[j]] = [copy[j], copy[i]];
    onChange(copy);
  };

  return (
    <div className={`array-editor ${className}`}>
      {items.length === 0 && <p className="array-empty">{emptyLabel ?? t("None yet.")}</p>}

      {items.map((item, i) => {
        // Errors/warnings anchored anywhere inside this item — badged on the
        // header as count pills so a collapsed tile still flags hidden findings
        // (CSS hides them when the tile is expanded, where the inline marks show).
        const counts = countLevelsUnder(findingsMap, `${basePath}.${i}`);
        return (
        // <details> so a long list (many days/activities) can be collapsed. The
        // header controls live in <summary>; each stops propagation so clicking
        // move/remove doesn't also toggle the disclosure.
        <details className="array-item" key={i} open={defaultOpen}>
          <summary className="array-item-head">
            <span className="array-item-title">{itemTitle(item, i)}</span>
            {(counts.error > 0 || counts.warning > 0) && (
              <span className="subtree-finding">
                {counts.error > 0 && (
                  <span
                    className="finding-pill error"
                    title={t(counts.error > 1 ? "{n} errors" : "{n} error", { n: counts.error })}
                  >
                    {FINDING_ICON.error} {counts.error}
                  </span>
                )}
                {counts.warning > 0 && (
                  <span
                    className="finding-pill warning"
                    title={t(counts.warning > 1 ? "{n} warnings" : "{n} warning", { n: counts.warning })}
                  >
                    {FINDING_ICON.warning} {counts.warning}
                  </span>
                )}
              </span>
            )}
            <span className="array-item-controls">
              <button
                type="button"
                className="icon-btn"
                onClick={(e) => {
                  e.preventDefault();
                  e.stopPropagation();
                  move(i, -1);
                }}
                disabled={i === 0}
                aria-label={t("Move up")}
                data-tip={t("Move up")}
              >
                <span className="fade-label">↑</span>
              </button>
              <button
                type="button"
                className="icon-btn"
                onClick={(e) => {
                  e.preventDefault();
                  e.stopPropagation();
                  move(i, 1);
                }}
                disabled={i === items.length - 1}
                aria-label={t("Move down")}
                data-tip={t("Move down")}
              >
                <span className="fade-label">↓</span>
              </button>
              <button
                type="button"
                className="icon-btn danger"
                onClick={(e) => {
                  e.preventDefault();
                  e.stopPropagation();
                  removeAt(i);
                }}
                aria-label={t("Remove")}
                data-tip={t("Remove")}
              >
                ✕
              </button>
            </span>
          </summary>
          <div className="array-item-body">
            {renderItem(item, i, (next) => replaceAt(i, next), `${basePath}.${i}`)}
          </div>
        </details>
        );
      })}

      <div className="array-add">
        {add.map((opt) => (
          <button
            key={opt.label}
            type="button"
            className="btn subtle"
            onClick={() => onChange([...items, opt.make()])}
          >
            + {opt.label}
          </button>
        ))}
      </div>
    </div>
  );
}
