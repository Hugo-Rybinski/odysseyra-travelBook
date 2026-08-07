"""Network-free tests for the maps subsystem: projection/geometry, resolving a
day into points/routes/areas from explicit coordinates, and geocode write-back
(with a stub geocoder)."""

import math

import pytest
from PIL import Image

from travelbook.maps.build import _anchor_city, _hex_to_rgb, resolve_day
from travelbook.maps.render import lonlat_to_px, pin_angles, render_map
from travelbook.maps.writeback import fill_coordinates
from travelbook.models import Coordinate, ItineraryError, Itinerary, _parse_coordinate


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
        {"type": "road", "start": "Pau", "end": "Lourdes",
         "start_coordinate": {"lat": 43.29, "long": -0.36},
         "end_coordinate": {"lat": 43.09, "long": -0.05}},
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
    monkeypatch.setattr("travelbook.maps.build.route", lambda a, b, cache: [a, b])
    it = _itin([DAY])
    points, routes, areas = resolve_day(it.days[0], it, cache=None)
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
    points, _, areas = resolve_day(it.days[0], it, cache=None)
    assert [p.label for p in points] == ["No-coord area"]
    assert points[0].lat == pytest.approx(43.1) and points[0].long == pytest.approx(0.2)
    assert len(areas) == 1


def test_render_map_offline(monkeypatch, tmp_path):
    """render_map produces an RGB image without network (tiles stubbed)."""
    monkeypatch.setattr(
        "travelbook.maps.render._fetch_tile",
        lambda url, style, z, x, y, td: Image.new("RGBA", (512, 512), (240, 240, 240, 255)))
    pts = [(43.09, -0.05), (43.10, -0.04)]
    img = render_map(pts, [pts], pts, (47, 107, 79), tmp_path)
    assert img.mode == "RGB" and img.width > 0 and img.height > 0


def test_resolve_day_no_inference_when_off():
    day = {"title": "d", "city": "Lourdes", "activities": [
        {"type": "point_of_interest", "name": "Somewhere with no coordinate"}]}
    it = _itin([day])  # infer defaults off
    points, routes, areas = resolve_day(it.days[0], it, cache=None)
    assert points == [] and routes == [] and areas == []


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
        {"type": "road", "start": "Pau", "end": "Lourdes",
         "end_coordinate": {"lat": 1.0, "long": 2.0}},  # already set, keep it
    ]}]}
    filled, missed = fill_coordinates(data, ["FR"], cache=None, geocoder=_stub)
    acts = data["days"][0]["activities"]
    assert acts[0]["coordinate"] == {"lat": 43.097, "long": -0.058}
    assert "coordinate" not in acts[1]                 # geocoder returned None
    assert acts[2]["start_coordinate"] == {"lat": 43.29, "long": -0.36}
    assert acts[2]["end_coordinate"] == {"lat": 1.0, "long": 2.0}  # preserved
    assert filled == 2 and missed == 1
