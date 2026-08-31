"""The trip's ``misc`` group: reference data that belongs to the whole trip but
to no point on its timeline.

Today it holds one thing — the **emergency contacts** — but it is deliberately a
group rather than a bare top-level array, so the next such list has somewhere
obvious to go instead of becoming a fifth content array beside ``days``.

Unlike ``travel_description`` and ``defaults``, whose keys are also accepted at
the top level for compatibility, ``misc`` is read *only* from its own object:
it is new, so there is no older shape to stay compatible with, and a bare
top-level ``emergency_contacts`` would read as trip content rather than
reference material.
"""

from __future__ import annotations

from dataclasses import dataclass

from .parsers import ItineraryError


@dataclass(frozen=True)
class EmergencyContact:
    """Who to reach in an emergency, and how.

    Both halves are free text on purpose. ``name`` is whatever identifies the
    service to the traveller ("SAMU (medical)", "US Embassy, Paris"), and
    ``contact`` is however you reach it — a short emergency code (``112``), a
    full international number, an email, or an address. Nothing parses it, so a
    country's own conventions survive as written; the viewer only *guesses*
    whether it looks dialable in order to offer a tap-to-call link.

    **Both are optional**, and a half-filled entry is rendered as the half it
    has rather than refused. A number with no label is still dialable, and the
    point of the whole group is that an unknown value should be left out — so
    failing the build over one would push the user to invent something. The
    validator warns about the missing half, where the fix belongs.
    """

    name: str = ""
    contact: str = ""

    @classmethod
    def from_dict(cls, data: dict) -> "EmergencyContact":
        if not isinstance(data, dict):
            raise ItineraryError("Each emergency contact must be an object")
        return cls(name=str(data.get("name", "")).strip(),
                   contact=str(data.get("contact", "")).strip())


def parse_emergency_contacts(raw) -> list[EmergencyContact]:
    """Build the ``misc.emergency_contacts`` list. Absent or empty means the
    trip simply lists none — both renderers then draw nothing at all rather
    than an empty section.

    An entry with *neither* half filled carries nothing to draw, so it is
    dropped here instead of printing a blank row; the shape of the group is
    still enforced (an array, of objects), because that is a typo, not a gap."""
    if raw is None or raw == "":
        return []
    if not isinstance(raw, list):
        raise ItineraryError("'emergency_contacts' must be an array")
    contacts = [EmergencyContact.from_dict(entry) for entry in raw]
    return [c for c in contacts if c.name or c.contact]
