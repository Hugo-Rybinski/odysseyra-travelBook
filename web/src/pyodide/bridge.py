"""Glue executed inside Pyodide: a thin, JSON-in/JSON-out surface over the
`odysseyra_travelbook` package for the JS layer to call. Kept deliberately small — all
real logic stays in the Python package.

- validate(text, lang)  -> JSON string {findings: [{level, line, message}]}
- resolve(text)          -> JSON string of the resolved-model dict (to_dict),
                            *without* maps, so the UI can paint the book at once
- render_day(text, index)-> JSON string {day: <that day, with map images + pin
                            labels merged in>}; called per day after resolve so
                            the (blocking) tile fetches don't hold up the text
- build(text, lang, ink_saver, maps, map_provider)
                         -> PDF bytes (maps embedded when on). Address inference
                            has no override here: it is read from the file's
                            `defaults`, like everything else about the trip.

Each returns {"error": "..."} (validate/resolve) or raises (build) on failure;
the JS wrappers surface it.

Maps: the `odysseyra_travelbook.maps` package reaches the network through a single seam,
``odysseyra_travelbook.maps.http_get``. Pyodide has no sockets, so we override that seam
with a browser ``fetch`` (a synchronous XHR exposed from JS as ``tb_js``). All
three map endpoints (Carto tiles, OSRM, Nominatim) send ``ACAO: *``, so the
fetch works cross-origin with no proxy — the app stays local-only.

This module runs inside a Web Worker (web/src/pyodide/worker.ts), so the blocking
calls below occupy that worker and not the page.
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

from odysseyra_travelbook import (
    Itinerary,
    build_ics,
    build_pdf,
    to_dict,
    validate_text,
)


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


def _stamp_hike_maps(itinerary, day, day_out, cache) -> None:
    """Render each hike's trail map from its GPX and merge it into the serialized
    day, as ``track.map``.

    The viewer's interactive trail map draws itself from the ``track`` geometry
    that arrives with the text, so this is only ever needed with the Options
    interactive-maps toggle **off** — the same alternative-not-fallback rule the
    day maps follow (see ``DayCard``'s ``MapView``). Without it, switching
    interactive maps off left a hike with its elevation profile and no trail at
    all, while the PDF printed both.

    Gated by ``defaults.include_hike_maps`` like every other reading of a
    ``track``, and independent of ``include_maps_in_render`` — attaching the GPX
    is the opt-in. Each hike is rendered in its own ``try``: one trail out where
    the tiles run thin must not cost the day's other maps.

    No ``lang`` on purpose, exactly as ``render_day`` renders the day map: the
    on-screen PNG then names places the way the viewer's own MapLibre map does,
    and the PDF it exports still goes through ``build(lang=…)``."""
    if not getattr(itinerary, "include_hike_maps", True):
        return
    from odysseyra_travelbook.maps import render_hike_map

    def walk(acts, out_acts):
        for act, out in zip(acts, out_acts):
            track = getattr(act, "track", None)
            if track is not None and out.get("track"):
                try:
                    img = render_hike_map(track, itinerary.cover_color, cache)
                    if img is not None:
                        out["track"]["map"] = {"image": _png_data_uri(img),
                                               "legend": []}
                except Exception:
                    pass  # offline / tile failure — the profile still draws
            nested = getattr(act, "activities", None)
            if nested and out.get("activities"):
                walk(nested, out["activities"])

    walk(day.activities, day_out["activities"])


def _stamp_pins(dm, day, day_out, itinerary) -> None:
    """Copy each object's pin label (by object identity, via ``dm.number_for``)
    onto the matching serialized dict entry.

    A road's own points are pinned too when it asks for them
    (``Road.display_*_on_maps``): the road's label is its **departure**, and each
    pinned junction/arrival is its waypoint's — which is why the waypoints are
    walked in step with their serialized twins here."""
    def walk(acts, out_acts):
        for act, out in zip(acts, out_acts):
            label = dm.number_for(act)
            if label is not None:
                out["map_pin"] = label
            wps = getattr(act, "waypoints", None)
            if wps and out.get("waypoints"):
                for wp, wp_out in zip(wps, out["waypoints"]):
                    wp_label = dm.number_for(wp)
                    if wp_label is not None:
                        wp_out["map_pin"] = wp_label
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
    OSRM route polylines, the dotted transport legs, per-area detail points, the
    accent colour and a bounds box. Mirrors render_day_maps' numbering
    (activities 1..N, the night's stay '*', area points A/B/C…) and its framing.
    ``None`` when the day has nothing locatable."""
    from odysseyra_travelbook.maps.build import (STAY_PIN, day_legs, fold_pins,
                                                 resolve_day)

    main_pts, routes, route_nodes, area_details = resolve_day(day, itinerary, cache)
    # Same folding as the static map, so a place the day names twice carries one
    # marker here too and the two renderings agree on what "3" is.
    main_groups = fold_pins(main_pts)
    points = [{"lat": g[0].lat, "long": g[0].long, "label": str(i), "title": g[0].label}
              for i, g in enumerate(main_groups, start=1)]
    stay = itinerary.stay_for(day.date)
    stay_coord = None
    if stay is not None and stay.coordinate is not None and stay.coordinate.show_on_map:
        stay_coord = (stay.coordinate.lat, stay.coordinate.long)
        points.append({"lat": stay_coord[0], "long": stay_coord[1],
                       "label": STAY_PIN, "title": stay.name})

    areas = []
    for title, pts in area_details:
        groups = fold_pins(pts)
        coords = [(g[0].lat, g[0].long) for g in groups]
        apoints = [{"lat": g[0].lat, "long": g[0].long,
                    "label": chr(ord("A") + j), "title": g[0].label}
                   for j, g in enumerate(groups)]
        # that night's stay ★ — a pin only, never part of `bounds` below, so it
        # can't widen the zoom (mirrors the static area map).
        if stay_coord is not None:
            apoints.append({"lat": stay_coord[0], "long": stay_coord[1],
                            "label": STAY_PIN, "title": stay.name})
        alats = [c[0] for c in coords]
        alons = [c[1] for c in coords]
        areas.append({
            "title": title,
            "points": apoints,
            # bounds from the area's own points only, so the ★ never widens the
            # fitted extent — it just sits wherever it falls.
            "bounds": [[min(alats), min(alons)], [max(alats), max(alons)]],
        })
    legs = day_legs(day, itinerary)
    coords = ([(p["lat"], p["long"]) for p in points]
              + [(lat, lon) for line in routes for lat, lon in line])
    # As in the static map, legs don't widen the fitted extent (a transatlantic
    # flight would zoom the day out to the ocean) — unless they're all there is.
    if not coords:
        coords = [c for line in legs for c in line]
    if not coords:
        return None
    lats = [c[0] for c in coords]
    lons = [c[1] for c in coords]
    return {
        "points": points,
        "routes": [[[lat, lon] for lat, lon in line] for line in routes],
        "route_nodes": [[lat, lon] for line in route_nodes for lat, lon in line],
        "legs": [[[lat, lon] for lat, lon in line] for line in legs],
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
    # are no sockets under Pyodide, so the browser seam blocks its thread), so we
    # hand back the text at once and let the UI request each day's map afterwards
    # via render_day — which also lets the book paint before any tile arrives.
    try:
        data = to_dict(_parsed(text))
    except Exception as exc:  # noqa: BLE001
        return json.dumps({"error": str(exc)})
    return json.dumps({"itinerary": data})


def render_day(text, index):
    """Render one day's maps (screen palette, never ink-saver) and return that
    day's serialized dict with the map images + pin labels merged in, for the UI
    to swap in place. Degrades gracefully — any failure returns the day mapless
    (``map.main`` is null), never an error.

    Two independent renders share one tile cache here: the day's own maps, and
    the trail map of any hike carrying a GPX (see :func:`_stamp_hike_maps`). They
    fail apart, because ``defaults.include_hike_maps`` is deliberately not gated
    behind ``include_maps_in_render`` — a trip that draws no day maps can still
    print its trails."""
    try:
        itinerary = _parsed(text)
        day = itinerary.days[index]
        day_out = to_dict(itinerary)["days"][index]
        day_out["map"] = {"main": None, "areas": [], "geo": None}
        try:
            from odysseyra_travelbook.maps import Cache
            cache = Cache.open()
        except Exception:
            return json.dumps({"day": day_out})  # no cache dir: nothing to draw
        try:
            from odysseyra_travelbook.maps import render_day_maps
            dm = render_day_maps(day, itinerary, cache, ink_saver=False)
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
        _stamp_hike_maps(itinerary, day, day_out, cache)
        try:
            cache.save()
        except Exception:
            pass
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


def leg_gpx(text, day_index, road_index, leg_index):
    """Build a GPX **route** file for one leg of one drive, from the geometry the
    map would draw for it — the answer to "give me this drive as a file" for a
    leg that carries no recording of its own.

    The leg is addressed as *the ``leg_index``-th hop of the ``road_index``-th
    drive of day ``day_index``*, all 0-based. Deliberately not an index into the
    resolved timeline: that has buffers woven through it, so its activity numbers
    don't line up with the input's — whereas "the Nth road of a day" is the same
    thing on both sides.

    Returns ``{"gpx": <file text>, "name": <suggested name>}``, or
    ``{"error": ...}``. It is an error rather than a straight line when routing
    is unavailable (see :func:`maps.build.road_leg_geometry`): a crow-flight line
    between two towns is a wrong route to hand a GPS, not a rough one.

    Needs the network unless that leg's geometry is already in the routing cache
    — which it normally is, the day's map having just been drawn from it."""
    try:
        from odysseyra_travelbook.maps import Cache
        from odysseyra_travelbook.maps.build import road_leg_geometry
        from odysseyra_travelbook.models import route_gpx

        itinerary = _parsed(text)
        day = itinerary.days[day_index]
        roads = [a for a in day.activities if getattr(a, "kind", "") == "road"]
        if not 0 <= road_index < len(roads):
            return json.dumps({"error": "no such drive on that day"})
        road = roads[road_index]
        cache = Cache.open()
        geometry = road_leg_geometry(road, day, itinerary, cache, leg_index)
        try:
            cache.save()
        except Exception:
            pass
        if geometry is None:
            return json.dumps({"error": "no route available for that leg"})
        wp, line = geometry
        legs = [w for w in road.waypoints if w.location]
        start = road.start if leg_index == 0 else legs[leg_index - 1].location
        name = f"{start} → {wp.location}" if start else wp.location
        return json.dumps({"gpx": route_gpx(line, name), "name": name})
    except Exception as exc:  # noqa: BLE001 — report, don't crash the worker
        return json.dumps({"error": str(exc)})


def ics(text, lang="en"):
    """Export the itinerary to iCalendar (.ics) text. No network, no maps —
    a pure transform of the resolved model. Returns ``{"error": ...}`` on a bad
    parse; the JS wrapper surfaces it."""
    try:
        itinerary = Itinerary.from_dict(json.loads(text))
        return json.dumps({"ics": build_ics(itinerary, lang=lang)})
    except Exception as exc:  # noqa: BLE001 — report, don't crash the worker
        return json.dumps({"error": str(exc)})


def build(text, lang="en", ink_saver=False, maps=None, map_provider="google"):
    # Address inference and its country scope are read from the file's
    # `defaults` (`infer_coordinates_from_address` / `inference_countries`) —
    # there is no export-time override, so edit them in the Edit tab.
    itinerary = Itinerary.from_dict(json.loads(text))
    out = "/tmp/odysseyra-out.pdf"
    # `maps=None` leaves the file's own `include_maps_in_render` in force; the
    # browser HTTP seam (installed above) lets tiles/routes/geocoding work.
    build_pdf(itinerary, out, lang=lang, ink_saver=ink_saver, maps=maps,
              map_provider=map_provider)
    with open(out, "rb") as fh:
        return fh.read()
