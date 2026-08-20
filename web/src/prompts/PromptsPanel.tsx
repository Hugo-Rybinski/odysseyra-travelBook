import { useCallback, useEffect, useRef, useState, type ReactNode } from "react";
import { useT } from "../i18n";

// The "🤖 LLM prompts" tab. Each entry in `skills/` (bundled as a static Markdown
// file, copied in by vite.config's viteStaticCopy) is presented as a card: a
// short human description of what the skill does and what to feed it, plus a big
// "Copy prompt" button that puts the whole self-contained Markdown on the
// clipboard — ready to paste into an LLM chat alongside your own material.
//
// The Markdown is fetched lazily on mount from `${BASE_URL}skills/<file>` (the
// same mechanism the bundled sample itineraries use); it's precached by the
// service worker (workbox globs *.md) so copying works offline too.

interface Skill {
  file: string; // filename under skills/ (and public/skills/ once copied)
  emoji: string;
  title: string;
  // A couple of lines describing what the skill produces.
  what: string;
  // What to give the LLM alongside this prompt.
  inputs: string[];
  // What comes back.
  output: string;
}

// Descriptions are English-source keys (translated via useT); the Markdown files
// themselves are the authoritative, self-contained prompts — we don't duplicate
// their content here, only summarise them.
const SKILLS: Skill[] = [
  {
    file: "build-full-json.md",
    emoji: "🗂️",
    title: "Build the full itinerary JSON",
    what:
      "Turns raw trip material into one complete, ready-to-render itinerary JSON " +
      "file. The prompt is self-contained: it carries every field, value format " +
      "and rule the LLM needs to get the JSON right on the first pass.",
    inputs: [
      "Your trip material — a brief, a day-by-day plan, booking-confirmation " +
        "emails, hotel/rental vouchers, screenshots, a guidebook PDF, links to " +
        "blog posts, a KML/KMZ track (e.g. exported from a custom Google Map), a " +
        "GPX track for a hike or off-road drive, or an MBOX export (e.g. a Gmail " +
        "label exported via Google Takeout).",
      "The more concrete the sources, the fewer gaps the LLM has to leave blank.",
    ],
    output:
      "A single <title>.json you can open here (Options → Open JSON…), plus a " +
      "report of the gaps and any conflicts it found between your sources.",
  },
  {
    file: "build-guidebook-kml.md",
    emoji: "🗺️",
    title: "Build a Google My Maps KML from a guidebook PDF",
    what:
      "Turns a guidebook PDF into an importable KML map: one placemark per place, " +
      "grouped into folders by region, color-coded by category, with page " +
      "references, descriptions and hike stats. The result is a custom Google Map " +
      "you can then export as KML/KMZ and feed to the itinerary-JSON prompt above.",
    inputs: [
      "A guidebook PDF — even a scanned, image-only one (the prompt reads pages " +
        "visually rather than assuming selectable text).",
      "Optionally, a list of nearby-city road distances / driving times to attach " +
        "to city placemarks.",
    ],
    output:
      "A grouped, color-coded guidebook_places_grouped_colored.kml, ready to " +
      "import into Google My Maps — plus the source CSVs and scripts to rebuild it.",
  },
  {
    file: "build-itinerary-from-guidebook.md",
    emoji: "📖",
    title: "Expand a guidebook into a day-by-day itinerary",
    what:
      "Turns a guidebook PDF plus a bare-bones outline (just days → destinations) " +
      "into a detailed, chronological Markdown itinerary: each day expanded with " +
      "guide-sourced activities and descriptions, clearly-labelled walks/hikes with " +
      "their metrics, explicit “Route from X to Y” stops, and printed-page citations. " +
      "It enriches your outline from the guide alone — it never invents facts.",
    inputs: [
      "A guidebook PDF for the region — even a scanned, image-only one (the prompt " +
        "reads pages visually rather than assuming selectable text).",
      "A very brief trip outline: one line per day with its destination " +
        "(e.g. “Day 1 → Paris, Day 2 → Mont Saint-Michel…”). No timings needed.",
    ],
    output:
      "A <destination>_<dates>_detailed_itinerary.md you can then feed to the " +
      "itinerary-JSON prompt above (or edit by hand first).",
  },
  {
    file: "fix-missing-duration-distance.md",
    emoji: "📏",
    title: "Fix missing durations & distances",
    what:
      "Builds a fill-in-the-blank Markdown worksheet for the roads, hikes and " +
      "activities that are missing a duration, distance or elevation — one entry " +
      "per missing value, with Google Maps links for road distances and " +
      "web-sourced estimates (tagged “to be checked”) for hikes.",
    inputs: [
      "Your itinerary JSON.",
      "The ⚠️ warnings about missing duration/distance/elevation — copy them from " +
        "the 🔎 Findings tab (or the validator output).",
    ],
    output:
      "A <title>-missing.md worksheet to complete by hand, then merge the figures " +
      "back into your JSON.",
  },
];

function SkillCard({ skill }: { skill: Skill }) {
  const t = useT();
  const [text, setText] = useState<string | null>(null);
  const [loadError, setLoadError] = useState(false);
  const [copied, setCopied] = useState(false);
  const timer = useRef<number | undefined>(undefined);

  useEffect(() => {
    let cancelled = false;
    fetch(`${import.meta.env.BASE_URL}skills/${skill.file}`)
      .then((r) => {
        if (!r.ok) throw new Error(String(r.status));
        return r.text();
      })
      .then((body) => {
        if (!cancelled) setText(body);
      })
      .catch(() => {
        if (!cancelled) setLoadError(true);
      });
    return () => {
      cancelled = true;
    };
  }, [skill.file]);

  useEffect(() => () => window.clearTimeout(timer.current), []);

  const onCopy = useCallback(async () => {
    if (!text) return;
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      window.clearTimeout(timer.current);
      timer.current = window.setTimeout(() => setCopied(false), 2000);
    } catch {
      setLoadError(true);
    }
  }, [text]);

  return (
    <section className="opt-group prompt-card">
      <h2>
        <span aria-hidden>{skill.emoji} </span>
        {t(skill.title)}
      </h2>
      <p className="opt-desc">{t(skill.what)}</p>
      <div className="prompt-inputs">
        <span className="prompt-inputs-label">{t("Give it")}</span>
        <ul>
          {skill.inputs.map((line, i) => (
            <li key={i}>{t(line)}</li>
          ))}
        </ul>
      </div>
      <p className="prompt-output">
        <span className="prompt-output-label">{t("You get")}</span> {t(skill.output)}
      </p>
      <div className="opt-row prompt-actions">
        <button className="btn" onClick={onCopy} disabled={!text}>
          {copied ? t("✓ Copied") : t("📋 Copy prompt")}
        </button>
        {loadError ? (
          <span className="prompt-hint prompt-hint-error">{t("Couldn't load this prompt.")}</span>
        ) : (
          <span className="prompt-hint">
            {t("Paste it into an LLM chat, then add your material.")}
          </span>
        )}
      </div>
    </section>
  );
}

export function PromptsPanel(): ReactNode {
  const t = useT();
  return (
    <section className="options-page" role="region" aria-label={t("🤖 LLM prompts")}>
      <h1 className="options-title">{t("LLM prompts")}</h1>
      <p className="opt-desc prompts-intro">
        {t(
          "Ready-made prompts that turn your raw trip material into itinerary JSON — or help you fill its gaps. Copy one, paste it into your favourite LLM (Claude, ChatGPT…), and add your own documents.",
        )}
      </p>
      <div className="options">
        {SKILLS.map((s) => (
          <SkillCard key={s.file} skill={s} />
        ))}
      </div>
    </section>
  );
}
