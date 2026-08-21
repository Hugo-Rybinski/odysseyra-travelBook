import type { ReactNode } from "react";
import { useT } from "../i18n";
import { PromptFlow } from "./PromptFlow";

// The "Usage guide" tab: the end-to-end pipeline (PromptFlow) that explains how
// raw trip material becomes an itinerary JSON and then a PDF. Its per-step
// "Open this prompt" links call onOpenPrompt, which the app wires to switch to
// the LLM-prompts tab and scroll to the matching prompt card.
export function GuidePanel({
  onOpenPrompt,
}: {
  onOpenPrompt?: (file: string) => void;
}): ReactNode {
  const t = useT();
  return (
    <section className="options-page" role="region" aria-label={t("Usage guide")}>
      <h1 className="options-title">{t("Usage guide")}</h1>
      <p className="opt-desc prompts-intro">
        {t(
          "From a pile of trip material to a finished, printable travel book — the steps, what each one takes in and produces, and how to do the manual parts.",
        )}
      </p>
      <PromptFlow onOpenPrompt={onOpenPrompt} />
    </section>
  );
}
