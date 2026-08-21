import type { ReactNode } from "react";
import { useT } from "../i18n";

// The pipeline shown above the prompt cards: how raw trip material becomes an
// itinerary JSON and, finally, a PDF. Rendered as a vertical run of stages;
// each stage holds one or more expandable cards (native <details>) that open to
// reveal an example or a step-by-step for the manual parts. Skill cards link
// down to their matching prompt card. Plain HTML/CSS — CSP-safe, no libraries.

type Kind = "input" | "skill" | "app";

interface Detail {
  label: string;
  ordered: boolean;
  // Each item may carry inline links written as [label](https://…); they render
  // as external links in place, so a "learn more" URL sits right where it's
  // relevant in the sentence.
  items: string[];
}

interface Card {
  kind: Kind;
  title: string;
  from: string;
  to: string;
  summary: string;
  detail: Detail;
  skillFile?: string; // anchors to the matching prompt card below
}

interface Stage {
  num: string;
  title: string;
  desc: string;
  cards: Card[];
}

const STAGES: Stage[] = [
  {
    num: "1",
    title: "Prepare your source material",
    desc: "First, gather the raw documents the prompts will read. Collect only what fits your trip — you don't need everything.",
    cards: [
      {
        kind: "input",
        title: "Gather your booking confirmations",
        from: "Gmail, inbox, photos",
        to: ".mbox, emails, screenshots",
        summary: "Round up every hotel, transport and activity booking you've made.",
        detail: {
          label: "Step by step",
          ordered: true,
          items: [
            "Find every confirmation for the trip — hotels, flights or trains, car rental, tours and tickets.",
            "If you use Gmail, the quickest way is to give them all one label (a label is just a folder/tag — [how to create one](https://support.google.com/mail/answer/118708)), then download that label with [Google Takeout](https://takeout.google.com/), Google's official data-export tool: choose Mail, tick only that label, and you get a single “.mbox” file (one file holding those emails).",
            "You can freely mix source types — there's no either/or. Alongside (or instead of) the .mbox, paste individual confirmation emails and add screenshots or photos of any booking, including ones that only exist as a web page. The more you provide, the more complete the result.",
          ],
        },
      },
      {
        kind: "input",
        title: "Collect your guidebook & reading",
        from: "guidebook, web",
        to: "Guidebook PDF, blog posts",
        summary: "Gather the travel content you want your itinerary drawn from.",
        detail: {
          label: "Step by step",
          ordered: true,
          items: [
            "Get your guidebook as a PDF. A scan or clear photos of the pages work fine — the prompts can read images, so the text doesn't need to be selectable.",
            "Save the links (or copy the text) of any blog posts or articles about the places you'll visit.",
          ],
        },
      },
      {
        kind: "input",
        title: "Build your own map (optional)",
        from: "Google My Maps",
        to: "KML file",
        summary: "Prefer to plan the route yourself? Make a custom map by hand and export it.",
        detail: {
          label: "Step by step",
          ordered: true,
          items: [
            "Go to [Google My Maps](https://www.google.com/mymaps) (a free Google tool for building your own maps) and click “Create a new map”.",
            "Search for each place you want and add it as a pin; you can group related pins into layers if you like.",
            "If you'll be driving, add driving directions between your stops ([how to draw directions](https://support.google.com/mymaps/answer/3067635)) so the real road route is saved on the map.",
            "Export the finished map to a KML file: open the map's menu (the three dots ⋮) and choose “Export to KML/KMZ”. Keep that file — it's a source for the next steps.",
            "Don't want to start from a blank page? The next section's “Map the guidebook” prompt builds a starter map from your guidebook that you then refine here instead.",
          ],
        },
      },
      {
        kind: "input",
        title: "Sketch a rough day-by-day plan",
        from: "you",
        to: "rough plan",
        summary: "Decide the shape of the trip — mainly where you sleep each night.",
        detail: {
          label: "Step by step",
          ordered: true,
          items: [
            "Write one line per day with its main destination — for example: “Day 1 → Paris, Day 2 → Mont-Saint-Michel, Day 3 → Saint-Malo”. No times or details needed; the prompts fill those in.",
            "Optionally, add anything you already know to steer the result — real dates, a rough theme for a day (“museums”, “beach day”), a must-do stop, or where you're sleeping. Every hint helps the LLM, but all are optional.",
          ],
        },
      },
    ],
  },
  {
    num: "2",
    title: "Preprocess your source material",
    desc: "Now run these prompts to turn the raw documents into a few clean files. They're independent — do only the ones you need.",
    cards: [
      {
        kind: "skill",
        title: "Extract your bookings",
        from: ".mbox, emails, screenshots",
        to: "a bookings .md file",
        summary: "Consolidate every booking confirmation into one attributed file.",
        skillFile: "extract-bookings.md",
        detail: {
          label: "Step by step",
          ordered: true,
          items: [
            "This prompt reads the confirmations you gathered and writes every detail into one neat file — so you never copy dates and reference numbers by hand.",
            "Open the prompt (in the 🤖 LLM prompts tab), copy it into an AI chat such as [Claude](https://claude.ai) or [ChatGPT](https://chatgpt.com), and attach your “.mbox” file, pasted emails and/or screenshots.",
            "It replies with a bookings `.md` file (a plain-text file) — one entry per booking, each noting where it came from, so nothing is made up.",
            "Double-check the file and correct it by hand if needed — it's plain text, so it opens in any text editor.",
          ],
        },
      },
      {
        kind: "skill",
        title: "Map the guidebook",
        from: "Guidebook PDF, blog posts",
        to: "KML file",
        summary: "Turn a guidebook into a map of places you then refine by hand.",
        skillFile: "build-guidebook-kml.md",
        detail: {
          label: "Step by step",
          ordered: true,
          items: [
            "This step is optional — do it only if you want a real map of the places in your guidebook. It works best when you plan to drive.",
            "Copy the prompt into an AI chat (Claude or ChatGPT) with your guidebook. It returns a “KML” file — a standard map file that simply lists places by name and location.",
            "Go to [Google My Maps](https://www.google.com/mymaps) (a free Google tool for building your own maps) and click “Create a new map”.",
            "Import the KML file into that map (in the map, click Import and choose the file — [how to import](https://support.google.com/mymaps/answer/3024836)). Every place from your guidebook shows up as a pin.",
            "Check the pins: drag any that landed in the wrong place, and add any spots the guide mentions that are missing.",
            "If you'll be driving, add driving directions between the stops you'll drive between ([how to draw directions](https://support.google.com/mymaps/answer/3067635)) — this saves the real road route on the map.",
            "When you're happy, export the map back to a KML file: open the map's menu (the three dots ⋮) and choose “Export to KML/KMZ”. Keep that exported file for the next steps.",
          ],
        },
      },
      {
        kind: "skill",
        title: "Draft the day-by-day",
        from: "Guidebook PDF, blog posts, rough plan",
        to: "an itinerary .md file",
        summary: "Expand a one-line-per-day outline into a detailed, sourced itinerary.",
        skillFile: "build-itinerary-from-guidebook.md",
        detail: {
          label: "Step by step",
          ordered: true,
          items: [
            "This prompt turns your rough plan into a full day-by-day itinerary, using your guidebook as the source of ideas.",
            "Copy the prompt into an AI chat (Claude or ChatGPT), then add your rough plan, the guidebook and any blog posts.",
            "You get back an itinerary `.md` file: each day filled out with things to see and do, walks and hikes, and the guidebook page numbers it drew from — so you can double-check anything.",
            "Double-check the file and correct it by hand if needed — it's plain text, so it opens in any text editor.",
          ],
        },
      },
    ],
  },
  {
    num: "3",
    title: "Assemble the itinerary JSON",
    desc: "Hand the prepared files to a single prompt that reconciles them into one JSON.",
    cards: [
      {
        kind: "skill",
        title: "Assemble the full JSON",
        from: "bookings .md, itinerary .md, KML",
        to: "a travel .json file",
        summary: "Merge the prepared files (plus any extra material) into one complete itinerary JSON.",
        skillFile: "build-full-json.md",
        detail: {
          label: "Step by step",
          ordered: true,
          items: [
            "This is the main step: it combines everything above into one file this app can open — an “itinerary JSON” (JSON is just a structured text format that apps read).",
            "Copy the prompt into an AI chat (Claude or ChatGPT), then attach the files you made: the bookings `.md`, the exported KML, and the itinerary `.md`. You don't need all three — use whichever you have.",
            "It merges them into one itinerary. If two sources disagree — say two different check-in times — it points that out so you can decide which is right.",
            "You get one file named after your trip, ending in “.json”. That's what you open in the app in the next step.",
            "Double-check the file and correct it by hand if needed — it's plain text, so it opens in any text editor.",
          ],
        },
      },
    ],
  },
  {
    num: "4",
    title: "Fill the gaps — if needed",
    desc: "Only when the validator flags missing distances, durations or elevations.",
    cards: [
      {
        kind: "skill",
        title: "Fill the missing figures",
        from: "a travel .json file, ⚠️ warnings",
        to: "an updated travel .json file",
        summary: "Turn the validator's warnings into a fill-in-the-blank worksheet.",
        skillFile: "fix-missing-duration-distance.md",
        detail: {
          label: "Step by step",
          ordered: true,
          items: [
            "Sometimes the itinerary is missing a distance, a duration, or the elevation of a drive or hike. This optional prompt helps you fill those in.",
            "Open your JSON file in this app (menu → Options → Open JSON…). Go to the 🔎 Findings tab and copy the ⚠️ warning lines it shows — these list exactly what's missing.",
            "Copy the prompt into an AI chat (Claude or ChatGPT) with your JSON file and those warning lines.",
            "It replies with a worksheet — a simple checklist of the blanks. For road distances it adds a [Google Maps](https://www.google.com/maps) link so you can read the number off the map; for hikes it pre-fills a best guess from the web, marked “to check” so you confirm it.",
            "Fill in the blanks, then either give the worksheet back to the prompt, or type the values straight into the ✏️ Edit tab of the app.",
          ],
        },
      },
    ],
  },
  {
    num: "5",
    title: "Use it in the app",
    desc: "Open the JSON here to finish it, then export and back it up.",
    cards: [
      {
        kind: "app",
        title: "Open & fix it in the app",
        from: "the travel .json file",
        to: "the final travel .json file",
        summary: "Import the JSON, then resolve anything the sources didn't cover.",
        detail: {
          label: "Step by step",
          ordered: true,
          items: [
            "Everything so far happened in an AI chat. From here you work inside this app to finish your travel book.",
            "Open the menu (☰, top-right) and choose Options → Open JSON…, then pick the “.json” file you made.",
            "Open the 🔎 Findings tab. It lists anything that's wrong (❌ errors) or worth checking (⚠️ warnings) in plain language, and points to the exact spot.",
            "Open the ✏️ Edit tab to fix those and add anything missing, then press “Apply changes” to refresh the preview.",
            "When it looks right, save it from the Edit tab — that's your final travel `.json` file.",
          ],
        },
      },
      {
        kind: "app",
        title: "Export & back it up",
        from: "the final travel .json file",
        to: "PDF, offline app, print",
        summary: "Take the finished travel book with you.",
        detail: {
          label: "Step by step",
          ordered: true,
          items: [
            "Install this app on your phone (in your browser's menu, tap “Add to Home Screen” or “Install app”) and open your file there — the travel book then works even with no internet.",
            "Make a printable PDF: menu → Options → Export, then “Generate PDF”.",
            "Print that PDF and keep it in your bag as a paper backup — handy if your phone runs out of battery.",
          ],
        },
      },
    ],
  },
];

// Render a step string, turning [label](url) into an inline external link and
// `code` into an inline <code> span.
function renderInline(s: string): ReactNode {
  const re = /\[([^\]]+)\]\(([^)]+)\)|`([^`]+)`/g;
  const out: ReactNode[] = [];
  let last = 0;
  let m: RegExpExecArray | null;
  let i = 0;
  while ((m = re.exec(s)) !== null) {
    if (m.index > last) out.push(s.slice(last, m.index));
    if (m[1] !== undefined) {
      out.push(
        <a key={i++} className="fc-inline-link" href={m[2]} target="_blank" rel="noreferrer">
          {m[1]}
        </a>,
      );
    } else {
      out.push(<code key={i++}>{m[3]}</code>);
    }
    last = m.index + m[0].length;
  }
  if (last < s.length) out.push(s.slice(last));
  return out;
}

function FlowCard({
  card,
  onOpenPrompt,
}: {
  card: Card;
  onOpenPrompt?: (file: string) => void;
}): ReactNode {
  const t = useT();
  const List = card.detail.ordered ? "ol" : "ul";
  return (
    <div className={`flow-card kind-${card.kind}`}>
      <div className="fc-head">
        <span className="fc-line1">
          <span className="fc-chip">
            {card.kind === "skill" ? t("Prompt") : card.kind === "app" ? t("In the app") : t("Gather")}
          </span>
          <span className="fc-title">{t(card.title)}</span>
        </span>
        <span className="fc-io">
          <code>{t(card.from)}</code>
          <span className="fc-arrow" aria-hidden>
            →
          </span>
          <code>{t(card.to)}</code>
        </span>
      </div>
      <div className="fc-body">
        <p className="fc-desc">{t(card.summary)}</p>
        <div className="fc-detail">
          <span className="fc-detail-label">{t(card.detail.label)}</span>
          <List>
            {card.detail.items.map((it, i) => (
              <li key={i}>{renderInline(t(it))}</li>
            ))}
          </List>
        </div>
        {card.skillFile &&
          (onOpenPrompt ? (
            <button type="button" className="fc-link" onClick={() => onOpenPrompt(card.skillFile!)}>
              {t("Open this prompt →")}
            </button>
          ) : (
            <a className="fc-link" href={`#prompt-${card.skillFile}`}>
              {t("Open this prompt →")}
            </a>
          ))}
      </div>
    </div>
  );
}

export function PromptFlow({
  onOpenPrompt,
}: {
  onOpenPrompt?: (file: string) => void;
}): ReactNode {
  const t = useT();
  return (
    <section className="prompt-flow-section" aria-label={t("How the pieces fit together")}>
      <h2 className="prompt-flow-title">{t("How the pieces fit together")}</h2>
      <p className="opt-desc prompt-flow-caption">
        {t(
          "The pipeline that turns your raw trip material into an itinerary JSON — then a PDF. Each step spells out what to do (and how, for the manual parts); every prompt links to its full text in the 🤖 LLM prompts tab.",
        )}
      </p>
      <div className="flow2">
        {STAGES.map((stage, si) => (
          <div key={stage.num}>
            <section className="flow-stage">
              <h3 className="flow-stage-title">
                <span className="flow-stage-num">{stage.num}</span>
                {t(stage.title)}
              </h3>
              <p className="flow-stage-desc">{t(stage.desc)}</p>
              <div className={`flow-cards${stage.cards.length > 1 ? " flow-parallel" : ""}`}>
                {stage.cards.map((c) => (
                  <FlowCard key={c.title} card={c} onOpenPrompt={onOpenPrompt} />
                ))}
              </div>
            </section>
            {si < STAGES.length - 1 && (
              <div className="flow-arrow-down" aria-hidden>
                ↓
              </div>
            )}
          </div>
        ))}
      </div>
    </section>
  );
}
