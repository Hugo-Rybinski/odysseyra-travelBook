"""Network-free tests for the maps subsystem: projection/geometry, resolving a
day into points/routes/areas from explicit coordinates, and geocode write-back
(with a stub geocoder)."""

import math

import pytest
from PIL import Image

from odysseyra_travelbook.maps.build import _anchor_city, _hex_to_rgb, render_day_maps, resolve_day
from odysseyra_travelbook.maps.render import lonlat_to_px, pin_angles, render_map
from odysseyra_travelbook.maps.routing import route
from odysseyra_travelbook.maps.writeback import fill_coordinates
from odysseyra_travelbook.models import Coordinate, ItineraryError, Itinerary, _parse_coordinate


# -- model coordinate parsing ------------------------------------------------
def test_coordinate_parsing_valid_and_defaults():
    c = _parse_coordinate({"lat": 43.1, "long": -0.05})
    assert c == Coordinate(43.1, -0.05, True)  # show_on_map defaults True
    assert _parse_coordinate(None) is None
    assert _parse_coordinate({"lat": 0, "long": 0, "show_on_map": False}).show_on_map is False


def test_coordinate_parsing_rejects_bad_values():
    for bad in ({"lat": 999, "long": 0}, {"lat": 0, "long": 500},
                {"lat": 1}, {"lat": 0, "long": "west"}):
        with pytest.raises(ItineraryError):
            _parse_coordinate(bad)


def _itin(days, **defaults):
    doc = {"travel_description": {"title": "T", "cover_color": "#2f6b4f"},
           "defaults": defaults, "days": days}
    return Itinerary.from_dict(doc)


# -- pure helpers ------------------------------------------------------------
def test_hex_to_rgb():
    assert _hex_to_rgb("#2f6b4f") == (47, 107, 79)
    assert _hex_to_rgb("2f6b4f") == (47, 107, 79)
    assert _hex_to_rgb("nope") == (31, 78, 95)  # fallback


def test_anchor_city_strips_arrow():
    assert _anchor_city("Paris → Lourdes") == "Lourdes"
    assert _anchor_city("Bishkek -> Cholpon-Ata") == "Cholpon-Ata"
    assert _anchor_city("Lourdes") == "Lourdes"


def test_lonlat_to_px_monotonic():
    # x grows with longitude, y grows going south (lower latitude)
    x0, y0 = lonlat_to_px(43.0, 0.0, 12)
    x1, y1 = lonlat_to_px(43.0, 1.0, 12)
    x2, y2 = lonlat_to_px(42.0, 0.0, 12)
    assert x1 > x0
    assert y2 > y0


def test_pin_angles_fans_coincident_pins():
    R = 30
    # three pins on the same spot -> three distinct angles
    px = [(100, 100), (100, 100), (100, 100)]
    angles = pin_angles(px, head_r=R)
    assert len(set(round(a, 3) for a in angles)) == 3
    # an isolated pin points straight up
    assert pin_angles([(0, 0)], head_r=R) == [-math.pi / 2]


# -- resolving a day (explicit coordinates, no network) ----------------------
DAY = {
    "title": "d", "city": "Lourdes",
    "activities": [
        {"type": "road", "start": "Pau",
         "coordinate": {"lat": 43.29, "long": -0.36},
         "waypoints": [{"coordinate": {"lat": 43.09, "long": -0.05}, "location": "Lourdes"}]},
        {"type": "point_of_interest", "name": "Sanctuary",
         "coordinate": {"lat": 43.097, "long": -0.058}},
        {"type": "point_of_interest", "name": "Hidden",
         "coordinate": {"lat": 43.1, "long": -0.05, "show_on_map": False}},
        {"type": "place", "name": "Old town",
         "coordinate": {"lat": 43.095, "long": -0.046},
         "activities": [
             {"type": "point_of_interest", "name": "Castle",
              "coordinate": {"lat": 43.096, "long": -0.049}},
             {"type": "point_of_interest", "name": "Bridge",
              "coordinate": {"lat": 43.095, "long": -0.053}},
         ]},
    ],
}


def test_resolve_day_points_routes_and_areas(monkeypatch):
    # stub routing so the road's route needs no network
    monkeypatch.setattr("odysseyra_travelbook.maps.build.route", lambda a, b, cache: [a, b])
    it = _itin([DAY])
    points, routes, _nodes, areas = resolve_day(it.days[0], it, cache=None)
    labels = [p.label for p in points]
    assert "Sanctuary" in labels
    assert "Old town" in labels          # the area contributes one pin
    assert "Hidden" not in labels        # show_on_map=False is skipped
    assert "Castle" not in labels        # nested points are not on the main map
    assert len(routes) == 1              # the road becomes one route
    assert routes[0][0] == (43.29, -0.36) and routes[0][-1] == (43.09, -0.05)
    assert len(areas) == 1 and areas[0][0] == "Old town"
    assert [p.label for p in areas[0][1]] == ["Castle", "Bridge"]


def test_area_centroid_fallback():
    """A place with no own coordinate but located sub-points gets a main-map pin
    at their centroid (unless it is explicitly hidden)."""
    day = {"title": "d", "city": "Lourdes", "activities": [
        {"type": "place", "name": "No-coord area", "activities": [
            {"type": "point_of_interest", "name": "A", "coordinate": {"lat": 43.0, "long": 0.0}},
            {"type": "point_of_interest", "name": "B", "coordinate": {"lat": 43.2, "long": 0.4}},
        ]}]}
    it = _itin([day])
    points, _, _nodes, areas = resolve_day(it.days[0], it, cache=None)
    assert [p.label for p in points] == ["No-coord area"]
    assert points[0].lat == pytest.approx(43.1) and points[0].long == pytest.approx(0.2)
    assert len(areas) == 1


def test_resolve_day_road_routes_through_waypoints(monkeypatch):
    """A road draws departure (coordinate) → wp1 → … → last waypoint; the last
    waypoint is the arrival."""
    monkeypatch.setattr("odysseyra_travelbook.maps.build.route", lambda a, b, cache: [a, b])
    day = {"title": "d", "city": "Lourdes", "activities": [
        {"type": "road", "start": "A",
         "coordinate": {"lat": 0.0, "long": 0.0},
         "waypoints": [
             {"coordinate": {"lat": 1.0, "long": 1.0}, "location": "One"},
             {"coordinate": {"lat": 2.0, "long": 2.0}, "location": "Two"},
         ]}]}
    it = _itin([day])
    _points, routes, nodes, _areas = resolve_day(it.days[0], it, cache=None)
    assert len(routes) == 1
    assert routes[0] == [(0.0, 0.0), (1.0, 1.0), (2.0, 2.0)]
    # the route's nodes (departure + waypoints) are exposed for the map discs
    assert nodes == [[(0.0, 0.0), (1.0, 1.0), (2.0, 2.0)]]


def test_route_failure_falls_back_but_does_not_cache(monkeypatch):
    """A failed OSRM lookup returns a straight [a, b] line but must NOT be
    cached — otherwise a transient failure poisons the cache into a permanent
    straight line."""
    from odysseyra_travelbook.maps import routing
    monkeypatch.setattr(routing.time, "sleep", lambda s: None)  # no real backoff
    monkeypatch.setattr("odysseyra_travelbook.maps.routing.urllib.request.urlopen",
                        lambda *a, **k: (_ for _ in ()).throw(OSError("no network")))
    cache = type("C", (), {"routes": {}})()
    a, b = (42.9, 0.36), (43.0, 0.57)
    assert route(a, b, cache) == [a, b]  # straight fallback
    assert cache.routes == {}            # nothing cached, so it retries later


def test_route_retries_transient_failure_then_caches(monkeypatch):
    """A transient failure is retried; once it succeeds the geometry is cached."""
    from odysseyra_travelbook.maps import routing
    monkeypatch.setattr(routing.time, "sleep", lambda s: None)
    good = [(1.0, 2.0), (1.1, 2.1), (1.2, 2.2)]
    calls = {"n": 0}

    def fake(coords):
        calls["n"] += 1
        if calls["n"] == 1:
            raise routing._Transient("HTTP 503")
        return good
    monkeypatch.setattr(routing, "_request_route", fake)
    cache = type("C", (), {"routes": {}})()
    assert route((1.0, 2.0), (1.2, 2.2), cache) == good
    assert calls["n"] == 2          # retried once, then succeeded
    assert list(cache.routes.values()) == [good]  # real geometry cached


def test_route_no_route_is_not_retried(monkeypatch):
    """A definitive 'no route' answer is not retried — it falls straight back."""
    from odysseyra_travelbook.maps import routing
    monkeypatch.setattr(routing.time, "sleep", lambda s: None)
    calls = {"n": 0}

    def fake(coords):
        calls["n"] += 1
        return None  # definitive no-route
    monkeypatch.setattr(routing, "_request_route", fake)
    cache = type("C", (), {"routes": {}})()
    a, b = (1.0, 2.0), (1.2, 2.2)
    assert route(a, b, cache) == [a, b]
    assert calls["n"] == 1          # NOT retried
    assert cache.routes == {}


def test_render_map_offline(monkeypatch, tmp_path):
    """render_map produces an RGB image without network (tiles stubbed)."""
    monkeypatch.setattr(
        "odysseyra_travelbook.maps.render._fetch_tile",
        lambda url, style, z, x, y, td: Image.new("RGBA", (512, 512), (240, 240, 240, 255)))
    pts = [(43.09, -0.05), (43.10, -0.04)]
    img = render_map(pts, [pts], pts, (47, 107, 79), tmp_path)
    assert img.mode == "RGB" and img.width > 0 and img.height > 0


def test_resolve_day_no_inference_when_off():
    day = {"title": "d", "city": "Lourdes", "activities": [
        {"type": "point_of_interest", "name": "Somewhere with no coordinate"}]}
    it = _itin([day])  # infer defaults off
    points, routes, nodes, areas = resolve_day(it.days[0], it, cache=None)
    assert points == [] and routes == [] and nodes == [] and areas == []


# -- geocode write-back (stub geocoder) --------------------------------------
def _stub(query, countries, cache):
    table = {
        "Sanctuary, Lourdes": (43.097, -0.058),
        "Pau, Lourdes": (43.29, -0.36),
        "Lourdes, Lourdes": (43.09, -0.05),
    }
    return table.get(query)


def test_fill_coordinates_adds_and_preserves():
    data = {"days": [{"title": "d", "city": "Lourdes", "activities": [
        {"type": "point_of_interest", "name": "Sanctuary"},
        {"type": "point_of_interest", "name": "Unknown place"},
        {"type": "road", "start": "Pau",
         "waypoints": [{"coordinate": {"lat": 1.0, "long": 2.0}, "location": "Lourdes"}]},
    ]}]}
    filled, missed = fill_coordinates(data, ["FR"], cache=None, geocoder=_stub)
    acts = data["days"][0]["activities"]
    assert acts[0]["coordinate"] == {"lat": 43.097, "long": -0.058}
    assert "coordinate" not in acts[1]                 # geocoder returned None
    # a road's 'start' geocodes into its 'coordinate' (the departure point)
    assert acts[2]["coordinate"] == {"lat": 43.29, "long": -0.36}
    assert acts[2]["waypoints"][0]["coordinate"] == {"lat": 1.0, "long": 2.0}  # untouched
    assert filled == 2 and missed == 1


# -- the network seam (odysseyra_travelbook.maps.http_get) -----------------------------
def test_fetch_tile_uses_http_get_seam(monkeypatch, tmp_path):
    """Tiles are fetched through the overridable odysseyra_travelbook.maps.http_get seam,
    so the browser (Pyodide, no sockets) can swap in a fetch-based transport."""
    import io

    import odysseyra_travelbook.maps as maps
    from odysseyra_travelbook.maps import render

    buf = io.BytesIO()
    Image.new("RGBA", (8, 8), (1, 2, 3, 255)).save(buf, "PNG")
    seen = []

    def fake_http_get(url, timeout=20):
        seen.append(url)
        return buf.getvalue()

    monkeypatch.setattr(maps, "http_get", fake_http_get)
    img = render._fetch_tile(render.BASE_URL, "nolabels", 5, 1, 1, tmp_path)
    assert seen and "cartocdn.com" in seen[0]
    assert img.mode == "RGBA"


def test_geocode_uses_http_get_seam(monkeypatch):
    """Geocoding goes through the same seam and parses Nominatim's JSON body."""
    import odysseyra_travelbook.maps as maps
    from odysseyra_travelbook.maps import geocode

    monkeypatch.setattr(geocode.time, "sleep", lambda s: None)  # no rate-limit wait
    monkeypatch.setattr(
        maps, "http_get",
        lambda url, timeout=20: b'[{"lat": "43.1", "lon": "-0.05"}]')
    cache = type("C", (), {"geocode": {}})()
    assert geocode.geocode("Somewhere", ["FR"], cache) == (43.1, -0.05)


# -- area detail map: the night's-stay ★ only when inside the extent ---------
def test_area_map_includes_stay_star_only_when_inside(monkeypatch, tmp_path):
    """The zoomed area map shows the night's-stay ★ pin only when the hotel
    falls within the area's own extent — never dragged in from off-map (which
    would widen the zoom)."""
    from odysseyra_travelbook.maps import Cache
    from odysseyra_travelbook.maps import build as buildmod

    monkeypatch.setattr(buildmod, "route", lambda a, b, cache: [a, b])
    captured = []

    def fake_render_map(all_coords, routes, points, accent, tiles_dir, **kw):
        captured.append(list(kw.get("labels") or []))
        return Image.new("RGB", (10, 10))

    monkeypatch.setattr(buildmod, "render_map", fake_render_map)

    def make(stay_coord):
        doc = {
            "travel_description": {"title": "T", "cover_color": "#2f6b4f",
                                   "start_date": "2026-06-01", "end_date": "2026-06-02"},
            "defaults": {"include_maps_in_render": True},
            "days": [{"title": "d", "date": "2026-06-01", "city": "X", "activities": [
                {"type": "place", "name": "Old town", "activities": [
                    {"type": "point_of_interest", "name": "A", "coordinate": {"lat": 43.0, "long": 0.0}},
                    {"type": "point_of_interest", "name": "B", "coordinate": {"lat": 43.2, "long": 0.4}},
                ]}]}],
            "accommodations": [{"name": "H", "city": "X", "arrival": "2026-06-01",
                                "departure": "2026-06-02", "coordinate": stay_coord}],
        }
        return Itinerary.from_dict(doc)

    cache = Cache.open(tmp_path)
    # area bbox is lat[43.0, 43.2] x lon[0.0, 0.4]
    for coord, expect_star in (
        ({"lat": 43.1, "long": 0.2}, True),   # inside → ★ on the area map
        ({"lat": 50.0, "long": 50.0}, False),  # far away → not on the area map
    ):
        captured.clear()
        it = make(coord)
        render_day_maps(it.days[0], it, cache, ink_saver=False)
        area_labels = next(lbls for lbls in captured if "A" in lbls)
        assert ("★" in area_labels) is expect_star
