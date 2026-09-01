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
        {"type": "road", "legs": [
            {"start_location": "Pau", "start_coordinate": {"lat": 43.29, "long": -0.36},
             "end_location": "Lourdes", "end_coordinate": {"lat": 43.09, "long": -0.05}}]},
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
    monkeypatch.setattr("odysseyra_travelbook.maps.build.route", lambda a, b, cache, **kw: [a, b])
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


def test_resolve_day_road_routes_through_its_legs(monkeypatch):
    """A road draws its first leg's departure → each leg's arrival, in order —
    so the last leg's arrival is where the drive ends up."""
    monkeypatch.setattr("odysseyra_travelbook.maps.build.route", lambda a, b, cache, **kw: [a, b])
    day = {"title": "d", "city": "Lourdes", "activities": [
        {"type": "road", "legs": [
            {"start_location": "A", "start_coordinate": {"lat": 0.0, "long": 0.0},
             "end_location": "One", "end_coordinate": {"lat": 1.0, "long": 1.0}},
            {"end_location": "Two", "end_coordinate": {"lat": 2.0, "long": 2.0}},
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
    """render_map produces an RGB image without network (tiles stubbed).

    An empty dict is a legitimate decoded tile — the ocean has no features — so
    stubbing the fetch this way exercises the whole drawing path over a bare
    background."""
    monkeypatch.setattr(
        "odysseyra_travelbook.maps.basemap.fetch_tile",
        lambda z, x, y, td: {})
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
        {"type": "road", "legs": [
            {"start_location": "Pau", "end_location": "Lourdes",
             "end_coordinate": {"lat": 1.0, "long": 2.0}}]},
    ]}]}
    filled, missed = fill_coordinates(data, ["FR"], cache=None, geocoder=_stub)
    acts = data["days"][0]["activities"]
    assert acts[0]["coordinate"] == {"lat": 43.097, "long": -0.058}
    assert "coordinate" not in acts[1]                 # geocoder returned None
    # a road leg's endpoint names geocode into its own start_/end_coordinate
    leg = acts[2]["legs"][0]
    assert leg["start_coordinate"] == {"lat": 43.29, "long": -0.36}
    assert leg["end_coordinate"] == {"lat": 1.0, "long": 2.0}  # untouched
    assert filled == 2 and missed == 1


# -- the network seam (odysseyra_travelbook.maps.http_get) -----------------------------
def test_fetch_tile_uses_http_get_seam(monkeypatch, tmp_path):
    """Tiles are fetched through the overridable odysseyra_travelbook.maps.http_get seam,
    so the browser (Pyodide, no sockets) can swap in a fetch-based transport."""
    import odysseyra_travelbook.maps as maps
    from odysseyra_travelbook.maps import basemap

    seen = []

    def fake_http_get(url, timeout=20):
        seen.append(url)
        return b""              # an empty tile still decodes — to nothing

    monkeypatch.setattr(maps, "http_get", fake_http_get)
    assert basemap.fetch_tile(5, 1, 1, tmp_path) == {}
    assert seen and "cartocdn.com" in seen[0] and seen[0].endswith(".mvt")
    # cached to disk as the wire bytes, so a second call needs no network
    assert (tmp_path / "vec_5_1_1.mvt").exists()
    assert basemap.fetch_tile(5, 1, 1, tmp_path) == {}
    assert len(seen) == 1


def test_tile_fetch_retries_transient_failures_but_not_a_4xx(monkeypatch, tmp_path):
    """A rate-limited tile is retried (one blip mid-stitch would otherwise cost
    the whole map), while a definitive 4xx fails straight away."""
    import urllib.error

    import odysseyra_travelbook.maps as maps
    from odysseyra_travelbook.maps import basemap

    monkeypatch.setattr(basemap.time, "sleep", lambda s: None)  # no real backoff
    calls = []

    def flaky(url, timeout=20):
        calls.append(url)
        if len(calls) < 3:
            raise urllib.error.HTTPError(url, 429, "slow down", None, None)
        return b""

    monkeypatch.setattr(maps, "http_get", flaky)
    assert basemap.fetch_tile(6, 1, 1, tmp_path) == {}
    assert len(calls) == 3

    calls.clear()

    def gone(url, timeout=20):
        calls.append(url)
        raise urllib.error.HTTPError(url, 404, "nope", None, None)

    monkeypatch.setattr(maps, "http_get", gone)
    with pytest.raises(urllib.error.HTTPError):
        basemap.fetch_tile(6, 2, 2, tmp_path)
    assert len(calls) == 1


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


def test_geocode_caches_a_real_miss_but_never_a_transient_failure(monkeypatch):
    """The distinction the cache turns on. "Nothing matches that text" is worth
    remembering forever; "we couldn't ask" must not be — a coordinate that
    failed once would otherwise stay missing in every later build, and a missing
    coordinate is a missing pin, so enough of them silently cost a whole map."""
    import urllib.error

    import odysseyra_travelbook.maps as maps
    from odysseyra_travelbook.maps import geocode

    monkeypatch.setattr(geocode.time, "sleep", lambda s: None)

    # an empty result set is Nominatim answering: definitive, cached
    monkeypatch.setattr(maps, "http_get", lambda url, timeout=20: b"[]")
    cache = type("C", (), {"geocode": {}})()
    assert geocode.geocode("an aire near Limoges", ["FR"], cache) is None
    assert cache.geocode == {"an aire near Limoges|FR": None}

    # a network/TLS blip is not an answer: retried, warned, and NOT remembered
    calls = []

    def flaky(url, timeout=20):
        calls.append(url)
        raise OSError("[SSL: CERTIFICATE_VERIFY_FAILED] unable to get local issuer")

    monkeypatch.setattr(maps, "http_get", flaky)
    cache = type("C", (), {"geocode": {}})()
    assert geocode.geocode("Sanctuary, Lourdes", ["FR"], cache) is None
    assert len(calls) == geocode.GEOCODE_RETRIES      # retried, like OSRM
    assert cache.geocode == {}                       # nothing poisoned

    # …so once the blip passes, the very next call resolves it
    monkeypatch.setattr(
        maps, "http_get",
        lambda url, timeout=20: b'[{"lat": "43.09", "lon": "-0.05"}]')
    assert geocode.geocode("Sanctuary, Lourdes", ["FR"], cache) == (43.09, -0.05)


def test_geocode_does_not_retry_a_definitive_4xx(monkeypatch):
    """A malformed query is our fault and will fail identically three times."""
    import urllib.error

    import odysseyra_travelbook.maps as maps
    from odysseyra_travelbook.maps import geocode

    monkeypatch.setattr(geocode.time, "sleep", lambda s: None)
    calls = []

    def bad(url, timeout=20):
        calls.append(url)
        raise urllib.error.HTTPError(url, 400, "bad request", None, None)

    monkeypatch.setattr(maps, "http_get", bad)
    cache = type("C", (), {"geocode": {}})()
    assert geocode.geocode("???", [], cache) is None
    assert len(calls) == 1
    assert cache.geocode == {"???|": None}       # definitive, so remembered


def test_geocode_survives_a_rate_limit_then_succeeds(monkeypatch):
    """Nominatim's 429 is the transient case that actually happens in a build."""
    import urllib.error

    import odysseyra_travelbook.maps as maps
    from odysseyra_travelbook.maps import geocode

    monkeypatch.setattr(geocode.time, "sleep", lambda s: None)
    calls = []

    def limited(url, timeout=20):
        calls.append(url)
        if len(calls) < 3:
            raise urllib.error.HTTPError(url, 429, "slow down", None, None)
        return b'[{"lat": "42.5", "lon": "76.0"}]'

    monkeypatch.setattr(maps, "http_get", limited)
    cache = type("C", (), {"geocode": {}})()
    assert geocode.geocode("Karakol", ["KG"], cache) == (42.5, 76.0)
    assert len(calls) == 3


# -- area detail map: the night's-stay ★ only when inside the extent ---------
def test_area_map_always_pins_the_stay_without_moving_the_zoom(monkeypatch, tmp_path):
    """The zoomed area map always carries that night's stay ★ — but as a pin
    only, so the extent (and hence the zoom/centering) stays the area's own
    points whether the hotel is inside them or far away."""
    from odysseyra_travelbook.maps import Cache
    from odysseyra_travelbook.maps import build as buildmod

    monkeypatch.setattr(buildmod, "route", lambda a, b, cache, **kw: [a, b])
    captured = []

    def fake_render_map(all_coords, routes, points, accent, tiles_dir, **kw):
        captured.append((list(kw.get("labels") or []), list(all_coords)))
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
    area_pts = [(43.0, 0.0), (43.2, 0.4)]  # the area's own two points
    for coord in ({"lat": 43.1, "long": 0.2},    # hotel inside the area's box
                  {"lat": 50.0, "long": 50.0}):  # …and far outside it
        captured.clear()
        it = make(coord)
        render_day_maps(it.days[0], it, cache, ink_saver=False)
        labels, extent = next((l, e) for l, e in captured if "A" in l)
        assert "★" in labels          # pinned either way
        assert extent == area_pts     # but never part of the framing


# -- transport legs (dotted origin -> destination lines) ---------------------
def _trip_with_leg(**leg):
    """A 3-day trip whose single transport leg carries both endpoints."""
    doc = {
        "travel_description": {"title": "T", "cover_color": "#2f6b4f"},
        "defaults": {"include_maps_in_render": True},
        "days": [
            {"title": f"d{n}", "date": f"2026-06-0{n}", "city": "X",
             "activities": [{"type": "point_of_interest", "name": f"P{n}",
                             "coordinate": {"lat": 43.0 + n / 10, "long": 0.1 * n}}]}
            for n in (1, 2, 3)
        ],
        # One booking with one leg; `leg` overrides fields on the leg itself,
        # which is where every place and time now lives.
        "transport": [{
            "type": "plane",
            "legs": [{
                "start": "A", "end": "B", "start_time": "22:10",
                "start_coordinate": {"lat": 40.0, "long": -70.0},
                "end_coordinate": {"lat": 49.0, "long": 2.5},
                **leg,
            }],
        }],
    }
    return Itinerary.from_dict(doc)


def test_day_legs_same_day_only_on_that_day():
    from odysseyra_travelbook.maps.build import day_legs
    it = _trip_with_leg(start_date="2026-06-02")
    assert day_legs(it.days[0], it) == []
    assert day_legs(it.days[1], it) == [[(40.0, -70.0), (49.0, 2.5)]]
    assert day_legs(it.days[2], it) == []


def test_day_legs_overnight_leg_is_on_both_day_maps():
    """An overnight leg belongs to the day it leaves *and* the day it lands."""
    from odysseyra_travelbook.maps.build import day_legs
    it = _trip_with_leg(start_date="2026-06-01", end_date="2026-06-02")
    leg = [(40.0, -70.0), (49.0, 2.5)]
    assert day_legs(it.days[0], it) == [leg]   # departure day
    assert day_legs(it.days[1], it) == [leg]   # arrival day
    assert day_legs(it.days[2], it) == []


def test_day_legs_needs_both_endpoints_and_respects_show_on_map():
    from odysseyra_travelbook.maps.build import day_legs
    for leg in ({"end_coordinate": None},
                {"start_coordinate": {"lat": 40.0, "long": -70.0, "show_on_map": False}}):
        it = _trip_with_leg(start_date="2026-06-01", **leg)
        assert day_legs(it.days[0], it) == []


def test_legs_do_not_widen_the_day_extent(monkeypatch, tmp_path):
    """A far-off leg is drawn but must not zoom the day map out to reach it: the
    extent stays the day's own pins/drives, and the dotted line is clipped."""
    from odysseyra_travelbook.maps import Cache
    from odysseyra_travelbook.maps import build as buildmod

    seen = {}

    def fake_render_map(all_coords, routes, points, accent, tiles_dir, **kw):
        seen["extent"] = list(all_coords)
        seen["legs"] = list(kw.get("legs") or [])
        return Image.new("RGB", (10, 10))

    monkeypatch.setattr(buildmod, "render_map", fake_render_map)
    it = _trip_with_leg(start_date="2026-06-01", end_date="2026-06-02")
    render_day_maps(it.days[0], it, Cache.open(tmp_path), ink_saver=False)

    assert seen["legs"] == [[(40.0, -70.0), (49.0, 2.5)]]   # drawn
    assert seen["extent"] == [(43.1, 0.1)]                   # but not framed for


def test_legs_frame_a_day_with_nothing_else_locatable(monkeypatch, tmp_path):
    """A pure travel day (no located activities) is framed on its legs, where it
    would otherwise get no map at all."""
    from odysseyra_travelbook.maps import Cache
    from odysseyra_travelbook.maps import build as buildmod

    seen = {}

    def fake_render_map(all_coords, routes, points, accent, tiles_dir, **kw):
        seen["extent"] = list(all_coords)
        return Image.new("RGB", (10, 10))

    monkeypatch.setattr(buildmod, "render_map", fake_render_map)
    it = _trip_with_leg(start_date="2026-06-01")
    it.days[0].activities = [a for a in it.days[0].activities if a.kind == "buffer"]
    maps = render_day_maps(it.days[0], it, Cache.open(tmp_path), ink_saver=False)

    assert seen["extent"] == [(40.0, -70.0), (49.0, 2.5)]
    assert maps.main is not None


# -- the whole-trip map (one map, pins labeled by day) -----------------------
def _trip_map_capture(monkeypatch):
    """Stub out render_map (and routing) and return the list it records into."""
    from odysseyra_travelbook.maps import build as buildmod

    seen = []
    monkeypatch.setattr(buildmod, "route", lambda a, b, cache, **kw: [a, b])

    def fake_render_map(all_coords, routes, points, accent, tiles_dir, **kw):
        seen.append({"extent": list(all_coords), "routes": list(routes),
                     "points": list(points), "labels": list(kw.get("labels") or []),
                     "legs": list(kw.get("legs") or []), "size": (kw.get("map_w"), kw.get("map_h"))})
        return Image.new("RGB", (10, 10))

    monkeypatch.setattr(buildmod, "render_map", fake_render_map)
    return seen


def test_resolve_trip_labels_every_pin_with_its_day_number(tmp_path):
    from odysseyra_travelbook.maps import Cache
    from odysseyra_travelbook.maps.build import resolve_trip

    it = _trip_with_leg(start_date="2026-06-01")
    points, labels, routes, legs = resolve_trip(it, Cache.open(tmp_path))
    assert points == [(43.1, 0.1), (43.2, 0.2), (43.3, 0.30000000000000004)]
    assert labels == ["1", "2", "3"]           # the day number, not 1..N per day
    assert routes == []
    assert legs == [[(40.0, -70.0), (49.0, 2.5)]]   # once, not per day it spans


def test_resolve_trip_collapses_a_days_neighbours_into_one_pin(tmp_path):
    """Two sights a few hundred metres apart are one dot at trip zoom, where a
    pin says only which day it is — so one pin, not a pinwheel of identical
    numbers. Far enough apart and they each keep their own."""
    from odysseyra_travelbook.maps import Cache
    from odysseyra_travelbook.maps.build import resolve_trip

    def pins(second):
        doc = {
            "travel_description": {"title": "T", "cover_color": "#2f6b4f"},
            "defaults": {"include_maps_in_render": True},
            "days": [{"title": "d", "date": "2026-06-01", "city": "Paris", "activities": [
                {"type": "point_of_interest", "name": "Louvre",
                 "coordinate": {"lat": 48.861, "long": 2.336}},
                {"type": "point_of_interest", "name": "other", "coordinate": second},
            ]}],
        }
        return resolve_trip(Itinerary.from_dict(doc), Cache.open(tmp_path))[0]

    assert len(pins({"lat": 48.860, "long": 2.333})) == 1    # ~300 m away
    assert len(pins({"lat": 48.887, "long": 2.343})) == 2    # ~3 km away


def test_resolve_trip_dedupes_a_spot_within_a_day_only(tmp_path):
    """The same spot twice in one day is one pin; revisited on another day it
    keeps its own, since the pin carries the day number."""
    from odysseyra_travelbook.maps import Cache
    from odysseyra_travelbook.maps.build import resolve_trip

    spot = {"lat": 43.0, "long": 0.0}
    doc = {
        "travel_description": {"title": "T", "cover_color": "#2f6b4f"},
        "defaults": {"include_maps_in_render": True},
        "days": [
            {"title": "d1", "date": "2026-06-01", "city": "X", "activities": [
                {"type": "point_of_interest", "name": "A", "coordinate": spot},
                {"type": "point_of_interest", "name": "A again", "coordinate": spot},
            ]},
            {"title": "d2", "date": "2026-06-02", "city": "X", "activities": [
                {"type": "point_of_interest", "name": "A", "coordinate": spot},
            ]},
        ],
    }
    it = Itinerary.from_dict(doc)
    points, labels, _routes, _legs = resolve_trip(it, Cache.open(tmp_path))
    assert points == [(43.0, 0.0), (43.0, 0.0)]
    assert labels == ["1", "2"]


def test_resolve_trip_pins_the_nights_stay(tmp_path):
    from odysseyra_travelbook.maps import Cache
    from odysseyra_travelbook.maps.build import resolve_trip

    doc = {
        "travel_description": {"title": "T", "cover_color": "#2f6b4f"},
        "defaults": {"include_maps_in_render": True},
        "days": [{"title": "d", "date": "2026-06-01", "city": "X", "activities": [
            {"type": "point_of_interest", "name": "A", "coordinate": {"lat": 43.0, "long": 0.0}},
        ]}],
        "accommodations": [{"name": "H", "city": "X", "arrival": "2026-06-01",
                            "departure": "2026-06-02",
                            "coordinate": {"lat": 43.5, "long": 0.5}}],
    }
    points, labels, _r, _l = resolve_trip(Itinerary.from_dict(doc), Cache.open(tmp_path))
    assert points == [(43.0, 0.0), (43.5, 0.5)]
    assert labels == ["1", "1"]   # the stay is day 1's pin too — no ★ at this zoom


def test_trip_map_is_never_framed_on_a_leg_but_still_draws_it(monkeypatch, tmp_path):
    """A transatlantic departure must not frame a France tour on the ocean: like
    a day map, the trip map ignores legs when framing and lets the dotted line
    run off the edge. Paper can't be zoomed out; the viewer's Overview can."""
    from odysseyra_travelbook.maps import Cache
    from odysseyra_travelbook.maps.build import render_trip_map

    seen = _trip_map_capture(monkeypatch)
    it = _trip_with_leg(start_date="2026-06-01", end_date="2026-06-02")
    assert render_trip_map(it, Cache.open(tmp_path)) is not None

    call = seen[-1]
    assert call["extent"] == [(43.1, 0.1), (43.2, 0.2), (43.3, 0.30000000000000004)]
    assert call["legs"] == [[(40.0, -70.0), (49.0, 2.5)]]   # drawn all the same
    assert call["labels"] == ["1", "2", "3"]


def test_trip_map_sets_aside_a_far_off_drive(monkeypatch, tmp_path):
    """A whole drive on the other side of the world (the ride to the departure
    airport) is drawn but doesn't drag the framing across an ocean, while the
    trip's own drives keep framing it."""
    from odysseyra_travelbook.maps import Cache
    from odysseyra_travelbook.maps.build import render_trip_map

    seen = _trip_map_capture(monkeypatch)
    doc = {
        "travel_description": {"title": "T", "cover_color": "#2f6b4f"},
        "defaults": {"include_maps_in_render": True},
        "days": [
            {"title": "d1", "date": "2026-06-01", "city": "New York", "activities": [
                {"type": "road", "legs": [
                    {"start_location": "Manhattan", "start_coordinate": {"lat": 40.75, "long": -73.99},
                     "end_location": "JFK", "end_coordinate": {"lat": 40.64, "long": -73.78}}]}]},
            {"title": "d2", "date": "2026-06-02", "city": "Paris", "activities": [
                {"type": "point_of_interest", "name": "Louvre",
                 "coordinate": {"lat": 48.86, "long": 2.34}}]},
            {"title": "d3", "date": "2026-06-03", "city": "Amboise", "activities": [
                {"type": "point_of_interest", "name": "Château",
                 "coordinate": {"lat": 47.41, "long": 0.98}},
                {"type": "road", "legs": [
                    {"start_location": "Paris", "start_coordinate": {"lat": 48.86, "long": 2.34},
                     "end_location": "Amboise", "end_coordinate": {"lat": 47.41, "long": 0.98}}]}]},
        ],
    }
    render_trip_map(Itinerary.from_dict(doc), Cache.open(tmp_path))

    call = seen[-1]
    assert (40.75, -73.99) not in call["extent"]     # the US drive: out of frame
    assert (48.86, 2.34) in call["extent"]           # the French one: in frame
    assert [(40.75, -73.99), (40.64, -73.78)] in call["routes"]   # drawn all the same


def test_trip_map_frames_a_trip_of_pure_travel_on_its_legs(monkeypatch, tmp_path):
    """With nothing else locatable there is no frame to keep, so the legs get it
    (mirroring the day maps' same last resort)."""
    from odysseyra_travelbook.maps import Cache
    from odysseyra_travelbook.maps.build import render_trip_map

    seen = _trip_map_capture(monkeypatch)
    it = _trip_with_leg(start_date="2026-06-01")
    for day in it.days:
        day.activities = [a for a in day.activities if a.kind == "buffer"]
    assert render_trip_map(it, Cache.open(tmp_path)) is not None
    assert seen[-1]["extent"] == [(40.0, -70.0), (49.0, 2.5)]


def test_render_trip_map_is_none_when_nothing_is_located(monkeypatch, tmp_path):
    from odysseyra_travelbook.maps import Cache
    from odysseyra_travelbook.maps.build import render_trip_map

    _trip_map_capture(monkeypatch)
    doc = {
        "travel_description": {"title": "T", "cover_color": "#2f6b4f"},
        "defaults": {"include_maps_in_render": True},
        "days": [{"title": "d", "date": "2026-06-01", "city": "X", "activities": [
            {"type": "point_of_interest", "name": "unlocated"}]}],
    }
    assert render_trip_map(Itinerary.from_dict(doc), Cache.open(tmp_path)) is None


def test_trip_map_page_follows_the_cover_only_with_maps_on(monkeypatch, tmp_path):
    """`TripMapMixin.trip_map` adds exactly one page when maps are on, and is a
    silent no-op otherwise (so a maps-off book is unchanged)."""
    from odysseyra_travelbook.pdf import TravelPDF

    _trip_map_capture(monkeypatch)
    it = _trip_with_leg(start_date="2026-06-01")

    pdf = TravelPDF(it, "en")
    pdf.map_cache_dir = tmp_path
    pdf.trip_map()
    assert pdf.page_no() == 1

    it.include_maps_in_render = False
    off = TravelPDF(it, "en")
    off.map_cache_dir = tmp_path
    off.trip_map()
    assert off.page_no() == 0


def test_trip_map_survives_a_render_failure(monkeypatch, tmp_path):
    """A map problem must never break the build — no page, no exception."""
    from odysseyra_travelbook.maps import build as buildmod
    from odysseyra_travelbook.pdf import TravelPDF

    def boom(*a, **kw):
        raise RuntimeError("tiles unreachable")

    monkeypatch.setattr(buildmod, "render_map", boom)
    pdf = TravelPDF(_trip_with_leg(start_date="2026-06-01"), "en")
    pdf.map_cache_dir = tmp_path
    pdf.trip_map()
    assert pdf.page_no() == 0


def test_dashes_splits_a_line_into_alternating_pieces():
    from odysseyra_travelbook.maps.render import dashes
    pieces = dashes([(0.0, 0.0), (100.0, 0.0)], dash=10, gap=10)
    assert pieces[0] == ((0.0, 0.0), (10.0, 0.0))       # dash
    assert pieces[1] == ((20.0, 0.0), (30.0, 0.0))      # after the gap
    assert len(pieces) == 5
    # the rhythm carries across a corner rather than restarting
    assert dashes([(0.0, 0.0), (5.0, 0.0), (5.0, 5.0)], dash=10, gap=10)[0] == (
        (0.0, 0.0), (5.0, 0.0))
    assert dashes([(0.0, 0.0)], dash=10, gap=10) == []  # nothing to walk


# -- a hike's GPX track ------------------------------------------------------

def _gpx_hike_itinerary(gpx_b64, **defaults):
    """A one-day trip whose only activity is a hike carrying ``gpx_b64``."""
    return _itin([{"title": "D", "date": "2026-06-01", "activities": [
        {"type": "hike", "name": "Ridge", "duration": "3h", "gpx": gpx_b64}]}],
        **defaults)


def _ridge_b64(n=40):
    import base64
    pts = "".join(f'<trkpt lat="{42.7 + i * 0.001:.6f}" lon="-0.14">'
                  f'<ele>{1000 + 5 * i}</ele></trkpt>' for i in range(n))
    xml = f'<?xml version="1.0"?><gpx><trk><trkseg>{pts}</trkseg></trk></gpx>'
    return base64.b64encode(xml.encode()).decode()


def test_a_hike_map_is_framed_on_its_own_track(monkeypatch, tmp_path):
    """Nothing to resolve: the geometry came with the itinerary, so the extent,
    the route and the two end discs are all the track itself."""
    from odysseyra_travelbook.maps import Cache
    from odysseyra_travelbook.maps.build import render_hike_map

    seen = _trip_map_capture(monkeypatch)
    it = _gpx_hike_itinerary(_ridge_b64())
    track = it.days[0].activities[0].track
    assert render_hike_map(track, it.cover_color, Cache.open(tmp_path)) is not None

    call = seen[-1]
    line = [(lat, long) for lat, long in track.points]
    assert call["extent"] == line
    assert call["routes"] == [line]
    assert call["points"] == []          # one trail — a pin would label it twice
    assert call["legs"] == []


def test_a_hike_map_needs_two_points_to_draw(tmp_path):
    from odysseyra_travelbook.maps import Cache
    from odysseyra_travelbook.maps.build import render_hike_map

    assert render_hike_map(None, "#2f6b4f", Cache.open(tmp_path)) is None


def test_the_hike_block_is_drawn_next_to_the_hike_and_follows_its_switch(
        monkeypatch, tmp_path):
    """The trail map + profile land on the hike's own page, and
    `defaults.include_hike_maps` switches the pair off without touching the rest
    of the day."""
    from odysseyra_travelbook.pdf import TravelPDF

    _trip_map_capture(monkeypatch)

    def rendered(it):
        pdf = TravelPDF(it, "en")
        pdf.map_cache_dir = tmp_path
        pdf.day(1, it.days[0])
        return pdf

    on = rendered(_gpx_hike_itinerary(_ridge_b64()))
    off = rendered(_gpx_hike_itinerary(_ridge_b64(), include_hike_maps=False))
    # The block adds height, so the switched-on book is the taller of the two.
    assert on.get_y() > off.get_y()


def test_the_hike_block_survives_a_map_failure(monkeypatch, tmp_path):
    """A tile failure loses the map, not the build — and not the profile either,
    which needs no network at all."""
    from odysseyra_travelbook.maps import build as buildmod
    from odysseyra_travelbook.pdf import TravelPDF

    def boom(*a, **kw):
        raise RuntimeError("tiles unreachable")

    monkeypatch.setattr(buildmod, "render_map", boom)
    it = _gpx_hike_itinerary(_ridge_b64())
    pdf = TravelPDF(it, "en")
    pdf.map_cache_dir = tmp_path
    before = pdf.get_y()
    pdf.day(1, it.days[0])
    assert pdf.get_y() > before   # the profile still drew
