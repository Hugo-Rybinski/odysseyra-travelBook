"""Stitch a directory of JSON fragments into one itinerary JSON.

The layout of the input directory mirrors the shape of the itinerary JSON:

    trip/
      travel_description.json     # -> "travel_description" (optional; prompted if absent)
      defaults.json               # -> "defaults" (optional; legacy name: default.json)
      days/*.json                 # -> "days"            (one entry per file)
      transports/*.json           # -> "transport"       (one entry per file)
      accommodations/*.json       # -> "accommodations"  (one entry per file)
      car-rentals/*.json          # -> "car_rentals"     (one entry per file)

Each array directory contributes one entry per JSON file, ordered by file name.
A file may also hold a JSON array, in which case every element is one entry.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Callable

from .validate.specs import TRAVEL_DESCRIPTION


class StitchError(Exception):
    """Raised when a directory can't be stitched into a valid itinerary shape."""


# Each array section maps one-or-more accepted directory names (the first that
# exists wins) to the itinerary key it feeds. Alternate spellings are accepted
# so a stray hyphen/underscore or a dropped 'm' doesn't silently drop a section.
_ARRAY_SECTIONS = [
    (["days"], "days"),
    (["transports", "transport"], "transport"),
    (["accommodations", "accomodations"], "accommodations"),
    (["car-rentals", "car_rentals", "car-rental"], "car_rentals"),
]

# The canonical (preferred) folder name for each array section — what `create`
# lays down and `stitch` reads back first.
SKELETON_DIRS = [names[0] for names, _ in _ARRAY_SECTIONS]


def _load_json(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise StitchError(f"invalid JSON in {path}: {exc}") from exc


def _load_array(directory: Path) -> list:
    """Every ``*.json`` in ``directory`` (sorted by name) as one list. A file
    holding an object is one entry; a file holding an array is spread in."""
    if not directory.is_dir():
        return []
    entries: list = []
    for path in sorted(directory.glob("*.json")):
        data = _load_json(path)
        if isinstance(data, list):
            entries.extend(data)
        else:
            entries.append(data)
    return entries


def _prompt_travel_description(ask: Callable[[str], str]) -> dict:
    """Interactively gather the ``travel_description`` fields, driven by the
    validator's spec table. Required fields are re-asked until answered;
    optional ones are skipped on a blank line."""
    desc: dict = {}
    print("No travel_description.json found — enter the trip details:")
    for spec in TRAVEL_DESCRIPTION:
        suffix = "" if spec.required else " (optional — leave blank to skip)"
        while True:
            try:
                answer = ask(f"  {spec.name} — {spec.description}{suffix}: ").strip()
            except (EOFError, KeyboardInterrupt):
                raise StitchError(
                    "input ended before the trip details were complete — provide "
                    "a travel_description.json instead")
            if answer:
                desc[spec.name] = answer
                break
            if spec.required:
                print(f"    '{spec.name}' is required.")
                continue
            break
    return desc


def aggregate(directory: str | Path, ask: Callable[[str], str] = input) -> dict:
    """Read the fragment directory and return the assembled itinerary dict.

    ``ask`` is the prompt callable used only when ``travel_description.json`` is
    absent (overridable for testing)."""
    directory = Path(directory)
    if not directory.is_dir():
        raise StitchError(f"not a directory: {directory}")

    data: dict = {}

    td_file = directory / "travel_description.json"
    if td_file.is_file():
        td = _load_json(td_file)
        if not isinstance(td, dict):
            raise StitchError("travel_description.json must be a JSON object")
    else:
        td = _prompt_travel_description(ask)
    data["travel_description"] = td

    default_file = next(
        (directory / n for n in ("defaults.json", "default.json")
         if (directory / n).is_file()),
        None,
    )
    if default_file is not None:
        defaults = _load_json(default_file)
        if not isinstance(defaults, dict):
            raise StitchError(f"{default_file.name} must be a JSON object")
        data["defaults"] = defaults

    for names, key in _ARRAY_SECTIONS:
        entries: list = []
        for name in names:
            entries = _load_array(directory / name)
            if entries:
                break
        if entries:
            data[key] = entries

    if not data.get("days"):
        raise StitchError(
            f"no days found — add day JSON files under {directory / 'days'}/"
        )
    return data


def create_skeleton(path: str | Path, name: str) -> Path:
    """Create an empty fragment directory ``<path>/<name>`` ready for ``stitch``:
    the four array sub-directories plus a ``travel_description.json`` stub whose
    title is ``"FIXME"``. Refuses to clobber an existing stub."""
    root = Path(path) / name
    td_file = root / "travel_description.json"
    if td_file.exists():
        raise StitchError(f"{td_file} already exists — refusing to overwrite")
    root.mkdir(parents=True, exist_ok=True)
    for d in SKELETON_DIRS:
        (root / d).mkdir(exist_ok=True)
    td_file.write_text(
        json.dumps({"title": "FIXME"}, indent=2) + "\n", encoding="utf-8")
    return root


def safe_filename(title: str) -> str:
    """A filesystem-safe base name derived from the trip title."""
    name = (title or "").strip() or "itinerary"
    for ch in '/\\:*?"<>|':
        name = name.replace(ch, "-")
    return name
