"""Glue executed inside Pyodide: a thin, JSON-in/JSON-out surface over the
`odysseyra_travelbook` package for the JS layer to call. Kept deliberately small — all
real logic stays in the Python package.

- validate(text, lang)  -> JSON string {findings: [{level, line, message}]}
- resolve(text)          -> JSON string of the resolved-model dict (to_dict),
                            *without* maps, so the UI can paint the book at once
- render_day(text, index)-> JSON string {day: <that day, with map images + pin
                            labels merged in>}; called per day after resolve so
                            the (blocking) tile fetches don't hold up the text
- build(text, lang, ink_saver, maps) -> PDF bytes (maps embedded when on)

Each returns {"error": "..."} (validate/resolve) or raises (build) on failure;
the JS wrappers surface it.

Maps: the `odysseyra_travelbook.maps` package reaches the network through a single seam,
``odysseyra_travelbook.maps.http_get``. Pyodide has no sockets, so we override that seam
with a browser ``fetch`` (a synchronous XHR exposed from JS as ``tb_js``). All
three map endpoints (Carto tiles, OSRM, Nominatim) send ``ACAO: *``, so the
fetch works cross-origin with no proxy — the app stays local-only.
"""

import base64
import io
import json

# Pyodide's urllib.request omits the ssl/socket-based handlers (there are no
# sockets in the browser sandbox), but fpdf2 imports some of them at module load
# even though we never fetch images over the network from that path. Stub any
# that are missing before importing odysseyra_travelbook so the import succeeds.
import urllib.request as _urllib_request

for _name in (
    "HTTPSHandler", "HTTPHandler", "ProxyHandler", "OpenerDirector",
    "HTTPRedirectHandler", "build_opener", "install_opener",
):
    if not hasattr(_urllib_request, _name):
        setattr(_urllib_request, _name, type(_name, (), {}))

from odysseyra_travelbook import Itinerary, build_pdf, to_dict, validate_text


# --- browser network seam for maps -----------------------------------------

def _install_browser_http() -> None:
    """Point the maps package's HTTP seam at the browser's ``fetch`` (sync XHR),
    so tiles/routes/geocoding work under Pyodide. A no-op (leaving urllib in
    place) when ``tb_js`` isn't registered, e.g. under native pytest."""
    try:
        import tb_js  # registered from runtime.ts before the bridge is used
    except Exception:
        return
    import urllib.error

    import odysseyra_travelbook.maps as _maps

    def http_get(url, timeout=20):  # noqa: ARG001 — timeout unused in the browser
        res = tb_js.httpGetSync(url)
        if not res.ok:
            code = int(res.status) or 599  # 0 (network failure) -> transient
            raise urllib.error.HTTPError(url, code, res.error or "fetch failed",
                                         None, None)
        return bytes(res.bytes.to_py())

    _maps.http_get = http_get


_install_browser_http()


# --- map rendering ----------------------------------------------------------

def _png_data_uri(image) -> str:
    buf = io.BytesIO()
    image.save(buf, format="PNG")
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode("ascii")


def _rendered_map(rendered) -> dict:
    return {"image": _png_data_uri(rendered.image), "legend": list(rendered.legend)}


def _stamp_pins(dm, day, day_out, itinerary) -> None:
    """Copy each object's pin label (by object identity, via ``dm.number_for``)
    onto the matching serialized dict entry."""
    def walk(acts, out_acts):
        for act, out in zip(acts, out_acts):
            label = dm.number_for(act)
            if label is not None:
                out["map_pin"] = label
            nested = getattr(act, "activities", None)
            if nested and out.get("activities"):
                walk(nested, out["activities"])

    walk(day.activities, day_out["activities"])
    stay = itinerary.stay_for(day.date)
    if stay is not None and day_out.get("stay"):
        label = dm.number_for(stay)
        if label is not None:
            day_out["stay"]["map_pin"] = label


def _day_geo(itinerary, day, cache):
    """Structured geo for an interactive (MapLibre) day map: numbered points, the
    OSRM route polylines, per-area detail points, the accent colour and a bounds
    box. Mirrors render_day_maps' numbering (activities 1..N, the night's stay
    '*', area points A/B/C…). ``None`` when the day has nothing locatable."""
    from odysseyra_travelbook.maps.build import STAY_PIN, _within, resolve_day

    main_pts, routes, route_nodes, area_details = resolve_day(day, itinerary, cache)
    points = [{"lat": p.lat, "long": p.long, "label": str(i), "title": p.label}
              for i, p in enumerate(main_pts, start=1)]
    stay = itinerary.stay_for(day.date)
    stay_coord = None
    if stay is not None and stay.coordinate is not None and stay.coordinate.show_on_map:
        stay_coord = (stay.coordinate.lat, stay.coordinate.long)
        points.append({"lat": stay_coord[0], "long": stay_coord[1],
                       "label": STAY_PIN, "title": stay.name})

    areas = []
    for title, pts in area_details:
        coords = [(p.lat, p.long) for p in pts]
        apoints = [{"lat": p.lat, "long": p.long, "label": chr(ord("A") + j), "title": p.label}
                   for j, p in enumerate(pts)]
        # the night's-stay ★, but only when it already sits inside this area's
        # extent (mirrors the static area map — never widens the zoom).
        if stay_coord is not None and _within(stay_coord[0], stay_coord[1], coords):
            apoints.append({"lat": stay_coord[0], "long": stay_coord[1],
                            "label": STAY_PIN, "title": stay.name})
        alats = [c[0] for c in coords]
        alons = [c[1] for c in coords]
        areas.append({
            "title": title,
            "points": apoints,
            # bounds from the area's own points only, so the ★ (when inside)
            # doesn't widen the fitted extent.
            "bounds": [[min(alats), min(alons)], [max(alats), max(alons)]],
        })
    coords = ([(p["lat"], p["long"]) for p in points]
              + [(lat, lon) for line in routes for lat, lon in line])
    if not coords:
        return None
    lats = [c[0] for c in coords]
    lons = [c[1] for c in coords]
    return {
        "points": points,
        "routes": [[[lat, lon] for lat, lon in line] for line in routes],
        "route_nodes": [[lat, lon] for line in route_nodes for lat, lon in line],
        "areas": areas,
        "accent": itinerary.cover_color,
        "bounds": [[min(lats), min(lons)], [max(lats), max(lons)]],
    }


# --- surface ----------------------------------------------------------------

# Parse once and memoize (Pyodide keeps module state across calls), so the
# per-day map renders reuse a single parse and share object identity with it —
# which is what `dm.number_for` (keyed by id()) relies on.
_PARSE = {"text": None, "itin": None}


def _parsed(text):
    if _PARSE["text"] != text:
        _PARSE["itin"] = Itinerary.from_dict(json.loads(text))
        _PARSE["text"] = text
    return _PARSE["itin"]


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
    # Deliberately maps-free: rendering maps fetches tiles synchronously (there
    # are no sockets under Pyodide, so the browser seam blocks the main thread),
    # so we hand back the text at once and let the UI request each day's map
    # afterwards via render_day.
    try:
        data = to_dict(_parsed(text))
    except Exception as exc:  # noqa: BLE001
        return json.dumps({"error": str(exc)})
    return json.dumps({"itinerary": data})


def render_day(text, index):
    """Render one day's maps (screen palette, never ink-saver) and return that
    day's serialized dict with the map images + pin labels merged in, for the UI
    to swap in place. Degrades gracefully — any failure returns the day mapless
    (``map.main`` is null), never an error."""
    try:
        itinerary = _parsed(text)
        day = itinerary.days[index]
        day_out = to_dict(itinerary)["days"][index]
        day_out["map"] = {"main": None, "areas": [], "geo": None}
        try:
            from odysseyra_travelbook.maps import Cache, render_day_maps
            cache = Cache.open()
            dm = render_day_maps(day, itinerary, cache, ink_saver=False)
            try:
                cache.save()
            except Exception:
                pass
            day_out["map"] = {
                "main": _rendered_map(dm.main) if dm.main else None,
                "areas": [{"title": t, **_rendered_map(m)} for t, m in dm.areas],
                # structured geo for the interactive map (shares resolve_day's
                # routing cache with the PNG render just done above).
                "geo": _day_geo(itinerary, day, cache),
            }
            _stamp_pins(dm, day, day_out, itinerary)
        except Exception:
            pass  # offline / tile failure — leave the day mapless
    except Exception as exc:  # noqa: BLE001 — a bad index / parse is reportable
        return json.dumps({"error": str(exc)})
    return json.dumps({"day": day_out})


def geocode(text_query, countrycodes=""):
    """Geocode a single free-text address/name via Nominatim (through the browser
    HTTP seam), for the Edit tab's "geocode from address" action. Returns
    ``{"coordinate": {"lat", "long"}}``, ``{"coordinate": null}`` (no match), or
    ``{"error": ...}``. Needs the network. ``countrycodes`` is a comma-joined
    list of 2-letter ISO codes (from ``defaults.inference_countries``)."""
    try:
        from odysseyra_travelbook.maps import Cache
        from odysseyra_travelbook.maps.geocode import geocode as _geocode
        countries = [c.strip() for c in countrycodes.split(",") if c.strip()]
        cache = Cache.open()
        result = _geocode(text_query, countries, cache)
        try:
            cache.save()
        except Exception:
            pass
        if result is None:
            return json.dumps({"coordinate": None})
        return json.dumps({"coordinate": {"lat": result[0], "long": result[1]}})
    except Exception as exc:  # noqa: BLE001 — report, don't crash the worker
        return json.dumps({"error": str(exc)})


def build(text, lang="en", ink_saver=False, maps=None):
    itinerary = Itinerary.from_dict(json.loads(text))
    out = "/tmp/odysseyra-out.pdf"
    # `maps=None` leaves the file's own `include_maps_in_render` in force; the
    # browser HTTP seam (installed above) lets tiles/routes/geocoding work.
    build_pdf(itinerary, out, lang=lang, ink_saver=ink_saver, maps=maps)
    with open(out, "rb") as fh:
        return fh.read()
