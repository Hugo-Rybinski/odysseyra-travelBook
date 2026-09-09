import type { Itinerary } from "../types/resolved";
import { contactHref } from "./contact";
import { tr, type Lang } from "./format";

// The trip's emergency contacts (`misc.emergency_contacts`), listed at the foot
// of the 🗺️ Overview tab — the twin of the PDF's final page (pdf/misc.py). Keep
// the two in step.
//
// One deliberate difference: here a contact that looks dialable (or mailable) is
// a real link, so an emergency number is one tap away on a phone. Paper has no
// twin for that, which is why that sniffing lives only on this side — the same
// split as the hike's `(Get GPX track)` button. The rule itself is
// `contact.tsx`'s `contactHref`, shared with an activity's `contact` row.
//
// Both halves of a contact are optional; whichever is present is drawn. A name
// with nothing to call is still worth listing (the traveller knows to look the
// number up), and a bare number is still dialable.
export function EmergencyContacts({
  itinerary,
  lang,
}: {
  itinerary: Itinerary;
  lang: Lang;
}) {
  const contacts = itinerary.emergency_contacts ?? [];
  if (!contacts.length) return null;

  return (
    <section className="emergency" aria-label={tr(lang, "emergencyContacts")}>
      <h2>{tr(lang, "emergencyContacts")}</h2>
      <ul>
        {contacts.map((c, i) => (
          <li key={i}>
            {c.name && <span className="emergency-name">{c.name}</span>}
            {c.contact && <ContactValue contact={c.contact} />}
          </li>
        ))}
      </ul>
    </section>
  );
}

function ContactValue({ contact }: { contact: string }) {
  const target = contactHref(contact);
  if (!target) return <span className="emergency-contact">{contact}</span>;
  return (
    <a className="emergency-contact" href={target}>
      {contact}
    </a>
  );
}
