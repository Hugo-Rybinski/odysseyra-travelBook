"""Command-line interface.

    odysseyra-travelBook build trip.json -o trip.pdf   # build a PDF (default)
    odysseyra-travelBook validate trip.json            # check the JSON, report problems
    odysseyra-travelBook stitch trip/                   # assemble one JSON from a directory

For convenience the ``build`` sub-command may be omitted:
``odysseyra-travelBook trip.json -o trip.pdf`` still works.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .lang import DEFAULT_LANGUAGE, LANGUAGES, tr
from .models import DEFAULT_MAP_PROVIDER, MAP_PROVIDERS, Itinerary, ItineraryError
from .pdf import build_pdf
from .stitch import (
    SKELETON_DIRS,
    StitchError,
    aggregate,
    create_skeleton,
    fragment_files,
    safe_filename,
)
from .validate import format_findings, validate_fragment, validate_text


def _run_build(input_path: Path, output: Path | None, lang: str,
               ink_saver: bool = False, maps: bool | None = None,
               map_country: str | None = None, cache_dir: Path | None = None,
               map_provider: str = DEFAULT_MAP_PROVIDER) -> int:
    output = output or input_path.with_suffix(".pdf")

    # Surface validation errors (errors only) before building.
    try:
        findings = validate_text(Path(input_path).read_text(encoding="utf-8"), lang)
    except OSError:
        findings = []
    if any(f.level == "error" for f in findings):
        print(tr("Validation errors (building anyway):", lang), file=sys.stderr)
        print(format_findings(findings, verbose=1, lang=lang), file=sys.stderr)

    try:
        itinerary = Itinerary.from_json_file(input_path)
        if map_country:
            itinerary.inference_countries = [c.strip().upper()
                                             for c in map_country.split(",") if c.strip()]
        path = build_pdf(itinerary, output, lang, ink_saver,
                         maps=maps, cache_dir=cache_dir,
                         map_provider=map_provider)
    except ItineraryError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    print(tr("Wrote {path}  ({days} days)", lang).format(
        path=path, days=len(itinerary.days)))
    return 0


def _run_geocode(input_path: Path, output: Path | None, country: str | None,
                 lang: str) -> int:
    """Fill missing coordinates by geocoding, writing them back into the JSON."""
    from .maps import Cache
    from .maps.writeback import fill_coordinates

    try:
        itinerary = Itinerary.from_json_file(input_path)
    except ItineraryError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    data = json.loads(Path(input_path).read_text(encoding="utf-8"))
    countries = ([c.strip().upper() for c in country.split(",") if c.strip()]
                 if country else itinerary.inference_countries)
    filled, missed = fill_coordinates(data, countries, Cache.open())
    out = output or input_path
    out.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n",
                   encoding="utf-8")
    print(tr("Geocoded {filled} coordinate(s), {missed} not found → {path}",
             lang).format(filled=filled, missed=missed, path=out))
    return 0


def _run_validate(input_path: Path, verbose: int, lang: str) -> int:
    try:
        text = Path(input_path).read_text(encoding="utf-8")
    except FileNotFoundError:
        print(f"error: file not found: {input_path}", file=sys.stderr)
        return 1
    findings = validate_text(text, lang)
    print(format_findings(findings, verbose, lang))
    return 1 if any(f.level == "error" for f in findings) else 0


def _run_stitch(directory: Path, verbose: int, lang: str) -> int:
    directory = Path(directory)

    # Phase 1 — validate each fragment file on its own, so line numbers point at
    # the file you actually edit (once stitched, they'd point at the merged
    # output). The `defaults` fragment is parsed first and fed to the others so
    # currency / timezone checks match their post-stitch behavior.
    frags = fragment_files(directory)
    defaults = None
    for kind, path in frags:
        if kind == "defaults":
            try:
                loaded = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                loaded = None
            defaults = loaded if isinstance(loaded, dict) else None
            break

    frag_errors = 0
    if frags:
        print(tr("Validating {n} fragment file(s):", lang).format(n=len(frags)))
    for kind, path in frags:
        try:
            text = path.read_text(encoding="utf-8")
        except OSError as exc:
            print(f"  error: {exc}", file=sys.stderr)
            frag_errors += 1
            continue
        findings = validate_fragment(
            text, kind, lang, defaults=None if kind == "defaults" else defaults)
        frag_errors += sum(1 for f in findings if f.level == "error")
        rel = path.relative_to(directory)
        print(f"  {rel}")
        for line in format_findings(findings, verbose, lang).splitlines():
            print(f"    {line}")

    # Phase 2 — attempt the stitch.
    try:
        data = aggregate(directory)
    except StitchError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    # Phase 3 — re-validate the assembled JSON (as text, so line numbers point
    # at the file we are about to write), report, then save it in the directory.
    text = json.dumps(data, indent=2, ensure_ascii=False) + "\n"
    findings = validate_text(text, lang)
    if frags:
        print()
    print(tr("Validating the assembled itinerary:", lang))
    print(format_findings(findings, verbose, lang))

    title = str(data.get("travel_description", {}).get("title", ""))
    out = Path(directory) / f"{safe_filename(title)}.json"
    out.write_text(text, encoding="utf-8")
    print(tr("Wrote {path}  ({days} days)", lang).format(
        path=out, days=len(data.get("days", []))))
    return 1 if (frag_errors or any(f.level == "error" for f in findings)) else 0


def _run_create_skeleton(path: Path, name: str) -> int:
    try:
        root = create_skeleton(path, name)
    except StitchError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    print(f"Created skeleton at {root}")
    for d in SKELETON_DIRS:
        print(f"  {root / d}/")
    print(f"  {root / 'travel_description.json'}  (title: FIXME)")
    print(f"Fill it in, then: odysseyra-travelBook stitch {root}")
    return 0


def _add_lang(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("-l", "--lang", choices=LANGUAGES, default=DEFAULT_LANGUAGE,
                        help="output language (default: en)")


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)

    parser = argparse.ArgumentParser(
        prog="odysseyra-travelBook",
        description="Build a travel PDF from JSON, or validate the JSON.",
    )
    sub = parser.add_subparsers(dest="command")

    b = sub.add_parser("build", help="build a PDF from a travel JSON")
    b.add_argument("input", type=Path, help="path to the itinerary JSON")
    b.add_argument("-o", "--output", type=Path, default=None,
                   help="output PDF path (default: <input>.pdf)")
    b.add_argument("--ink-saver", action="store_true",
                   help="draw outlines and thin rules instead of large solid "
                        "colored fills, to save printer ink")
    b.add_argument("--maps", dest="maps", action=argparse.BooleanOptionalAction,
                   default=None,
                   help="draw per-day maps (--no-maps to force off), overriding "
                        "defaults.include_maps_in_render")
    b.add_argument("--map-country", default=None,
                   help="ISO country code(s) to restrict geocoding to, e.g. FR")
    b.add_argument("--map-provider", choices=MAP_PROVIDERS,
                   default=DEFAULT_MAP_PROVIDER,
                   help="which app the inline (Navigate) links open "
                        f"(default: {DEFAULT_MAP_PROVIDER})")
    b.add_argument("--cache-dir", type=Path, default=None,
                   help="where to cache map tiles / geocode / route results")
    _add_lang(b)

    v = sub.add_parser("validate", help="validate a travel JSON and report problems")
    v.add_argument("input", type=Path, help="path to the itinerary JSON")
    v.add_argument("-v", "--verbose", type=int, choices=(1, 2, 3), default=2,
                   help="1=errors only, 2=errors + warnings (default), "
                        "3=everything incl. low-priority info")
    _add_lang(v)

    s = sub.add_parser("stitch", help="assemble one itinerary JSON from a "
                       "directory of fragment files")
    s.add_argument("directory", type=Path,
                   help="directory holding travel_description.json, defaults.json "
                        "and days/ transports/ accommodations/ car-rentals/ folders")
    s.add_argument("-v", "--verbose", type=int, choices=(1, 2, 3), default=2,
                   help="validation verbosity for the assembled JSON "
                        "(1=errors, 2=+warnings [default], 3=+info)")
    _add_lang(s)

    g = sub.add_parser("geocode", help="fill missing coordinates by geocoding "
                       "names/addresses and write them back into the JSON")
    g.add_argument("input", type=Path, help="path to the itinerary JSON")
    g.add_argument("-o", "--output", type=Path, default=None,
                   help="output path (default: overwrite the input in place)")
    g.add_argument("--country", default=None,
                   help="ISO country code(s) to restrict geocoding to (default: "
                        "the trip's inference_countries)")
    _add_lang(g)

    c = sub.add_parser("create-skeleton", help="scaffold an empty fragment "
                       "directory (sub-folders + a travel_description.json stub) "
                       "for `stitch`")
    c.add_argument("path", type=Path,
                   help="parent directory in which to create the skeleton")
    c.add_argument("name", help="name of the skeleton directory to create")

    _commands = ("build", "validate", "stitch", "create-skeleton", "geocode")
    # Backward-compat: `odysseyra-travelBook trip.json ...` implies `build`.
    if argv and argv[0] not in _commands + ("-h", "--help"):
        argv = ["build"] + argv

    args = parser.parse_args(argv)
    if args.command == "validate":
        return _run_validate(args.input, args.verbose, args.lang)
    if args.command == "stitch":
        return _run_stitch(args.directory, args.verbose, args.lang)
    if args.command == "create-skeleton":
        return _run_create_skeleton(args.path, args.name)
    if args.command == "geocode":
        return _run_geocode(args.input, args.output, args.country, args.lang)
    if args.command == "build":
        return _run_build(args.input, args.output, args.lang, args.ink_saver,
                          maps=args.maps, map_country=args.map_country,
                          cache_dir=args.cache_dir, map_provider=args.map_provider)
    parser.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
