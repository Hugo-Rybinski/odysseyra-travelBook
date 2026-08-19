import { createContext, Fragment, useContext, useMemo, type ReactNode } from "react";
import type { Lang } from "../render/format";
import { FR } from "./fr";

// Lightweight UI i18n for the app *chrome* (top bar, Options, Edit tab, findings
// panel, toasts). It mirrors the Python side's philosophy: English is the source
// string and the key, French is a lookup table, and a missing key falls back to
// the English source. The travel-book renderer (render/) keeps its own compact
// label table (render/format.ts `tr`) and is untouched by this layer.
//
// Templates keep {placeholders} — translate *then* fill (so word order can move
// the placeholder), exactly like the Python `tr(...).format(...)` convention.

export type { Lang };

const TABLES: Record<Lang, Record<string, string>> = { en: {}, fr: FR };

/** Fill {placeholders} in a (possibly translated) template. */
function fill(template: string, vars?: Record<string, string | number>): string {
  if (!vars) return template;
  return template.replace(/\{(\w+)\}/g, (_, k) => String(vars[k] ?? `{${k}}`));
}

/** Translate `text` into `lang` (English source is the key); fill placeholders. */
export function translate(
  lang: Lang,
  text: string,
  vars?: Record<string, string | number>,
): string {
  const table = TABLES[lang];
  const out = (table && table[text]) || text;
  return fill(out, vars);
}

export type TFn = (text: string, vars?: Record<string, string | number>) => string;

const I18nContext = createContext<Lang>("en");

export function I18nProvider({ lang, children }: { lang: Lang; children: ReactNode }) {
  return <I18nContext.Provider value={lang}>{children}</I18nContext.Provider>;
}

/** The active UI language. */
export function useLang(): Lang {
  return useContext(I18nContext);
}

/** A `t(text, vars?)` bound to the active language. */
export function useT(): TFn {
  const lang = useContext(I18nContext);
  return useMemo<TFn>(() => (text, vars) => translate(lang, text, vars), [lang]);
}

export type TxFn = (
  text: string,
  nodes: Record<string, ReactNode>,
  vars?: Record<string, string | number>,
) => ReactNode;

/**
 * A rich `t` that lets {tokens} in the (translated) template stand for React
 * nodes — e.g. a bolded tab name embedded in a sentence — so word order can move
 * with the language. Tokens present in `nodes` become that node; tokens in
 * `vars` become their string; anything else is left literal.
 */
export function useTx(): TxFn {
  const lang = useContext(I18nContext);
  return useMemo<TxFn>(
    () => (text, nodes, vars) => {
      const template = translate(lang, text);
      const parts = template.split(/(\{\w+\})/g);
      return parts.map((part, i) => {
        const m = /^\{(\w+)\}$/.exec(part);
        if (m) {
          const key = m[1];
          if (key in nodes) return <Fragment key={i}>{nodes[key]}</Fragment>;
          if (vars && key in vars) return <Fragment key={i}>{String(vars[key])}</Fragment>;
        }
        return <Fragment key={i}>{part}</Fragment>;
      });
    },
    [lang],
  );
}
