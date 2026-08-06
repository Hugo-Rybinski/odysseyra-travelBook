"""Command-line interface.

    travelbook build trip.json -o trip.pdf   # build a PDF (default)
    travelbook validate trip.json            # check the JSON, report problems

For convenience the ``build`` sub-command may be omitted:
``travelbook trip.json -o trip.pdf`` still works.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .lang import DEFAULT_LANGUAGE, LANGUAGES, tr
from .models import Itinerary, ItineraryError
from .pdf import build_pdf
from .validate import format_findings, validate_text


def _run_build(input_path: Path, output: Path | None, lang: str,
               ink_saver: bool = False) -> int:
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
        path = build_pdf(itinerary, output, lang, ink_saver)
    except ItineraryError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    print(tr("Wrote {path}  ({days} days)", lang).format(
        path=path, days=len(itinerary.days)))
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


def _add_lang(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("-l", "--lang", choices=LANGUAGES, default=DEFAULT_LANGUAGE,
                        help="output language (default: en)")


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)

    parser = argparse.ArgumentParser(
        prog="travelbook",
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
    _add_lang(b)

    v = sub.add_parser("validate", help="validate a travel JSON and report problems")
    v.add_argument("input", type=Path, help="path to the itinerary JSON")
    v.add_argument("-v", "--verbose", type=int, choices=(1, 2, 3), default=2,
                   help="1=errors only, 2=errors + warnings (default), "
                        "3=everything incl. low-priority info")
    _add_lang(v)

    # Backward-compat: `travelbook trip.json ...` implies `build`.
    if argv and argv[0] not in ("build", "validate", "-h", "--help"):
        argv = ["build"] + argv

    args = parser.parse_args(argv)
    if args.command == "validate":
        return _run_validate(args.input, args.verbose, args.lang)
    if args.command == "build":
        return _run_build(args.input, args.output, args.lang, args.ink_saver)
    parser.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
