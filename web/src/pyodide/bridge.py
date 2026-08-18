"""Glue executed inside Pyodide: a thin, JSON-in/JSON-out surface over the
`travelbook` package for the JS layer to call. Kept deliberately small — all
real logic stays in the Python package.

- validate(text, lang) -> JSON string {findings: [{level, line, message}]}
- resolve(text)         -> JSON string of the resolved-model dict (to_dict)
- build(text, lang, ink_saver) -> PDF bytes (maps are off in v1)

Each returns {"error": "..."} (validate/resolve) or raises (build) on failure;
the JS wrappers surface it.
"""

import json

# Pyodide's urllib.request omits the ssl/socket-based handlers (there are no
# sockets in the browser sandbox), but fpdf2 imports some of them at module load
# even though we never fetch images over the network. Stub any that are missing
# before importing travelbook so the import succeeds; maps stay off in v1
# regardless (see README "Future iterations").
import urllib.request as _urllib_request

for _name in (
    "HTTPSHandler", "HTTPHandler", "ProxyHandler", "OpenerDirector",
    "HTTPRedirectHandler", "build_opener", "install_opener",
):
    if not hasattr(_urllib_request, _name):
        setattr(_urllib_request, _name, type(_name, (), {}))

from travelbook import Itinerary, build_pdf, to_dict, validate_text


def validate(text, lang="en"):
    try:
        findings = validate_text(text, lang)
    except Exception as exc:  # noqa: BLE001 — report, don't crash the worker
        return json.dumps({"error": str(exc)})
    return json.dumps({
        "findings": [
            {"level": f.level, "line": f.line, "message": f.message}
            for f in findings
        ]
    })


def resolve(text):
    try:
        itinerary = Itinerary.from_dict(json.loads(text))
    except Exception as exc:  # noqa: BLE001
        return json.dumps({"error": str(exc)})
    return json.dumps({"itinerary": to_dict(itinerary)})


def build(text, lang="en", ink_saver=False):
    itinerary = Itinerary.from_dict(json.loads(text))
    out = "/tmp/travelbook-out.pdf"
    # Maps are intentionally off in v1: the maps package reaches the network via
    # urllib, which has no sockets under Pyodide. See README "Future iterations".
    build_pdf(itinerary, out, lang=lang, ink_saver=ink_saver, maps=False)
    with open(out, "rb") as fh:
        return fh.read()
