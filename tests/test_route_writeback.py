"""The `route` command: each drive leg's computed line stored in the JSON.

The decisions pinned here (see `maps/writeback.py`'s `fill_routes` for the why):

* a leg with no `gpx` gets the line the maps draw, as a gzipped GPX `<rte>`,
  marked `gpx_generated: true`;
* a `gpx` without that mark is the user's recording and is never touched;
* a re-run recomputes every generated line (so it follows an edited endpoint)
  and is byte-stable when nothing moved — but a leg that can't be routed this
  time keeps the line it had;
* once stored, the line is drawn from the file with no routing at all, and it
  still reads as *computed* downstream: a `<rte>` in the GPX export, flagged in
  the resolved document.
"""

import base64
import copy
import gzip
import json
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

from odysseyra_travelbook import Itinerary
from odysseyra_travelbook.cli import main
from odysseyra_travelbook.gpx_bundle import gpx_files
from odysseyra_travelbook.maps.build import road_leg_lines
from odysseyra_travelbook.maps.writeback import fill_routes
from odysseyra_travelbook.models.serialize import to_dict
from odysseyra_travelbook.validate import validate_text

GPX_NS = {"g": "http://www.topografix.com/GPX/1/1"}

A = {"lat": 43.0974, "long": -0.0583}
B = {"lat": 42.9700, "long": -0.0950}
C = {"lat": 42.8900, "long": -0.1130}


class _FakeCache:
    def __init__(self):
        self.geocode = {}
        self.routes = {}
        self.dir = Path("/nonexistent")

    def save(self):
        pass


def _bent(a, b):
    """A three-point "road": through a midpoint pushed off the straight line,
    so a stored route can't be mistaken for the crow-flight pair."""
    mid = ((a[0] + b[0]) / 2 + 0.01, (a[1] + b[1]) / 2)
    return [a, mid, b]


@pytest.fixture(autouse=True)
def routed(monkeypatch):
    import odysseyra_travelbook.maps.build as build

    calls = []

    def fake(a, b, cache, fallback=True):
        calls.append((a, b))
        return _bent(a, b)

    monkeypatch.setattr(build, "route", fake)
    return calls


def _recording():
    doc = ('<?xml version="1.0"?><gpx version="1.1" creator="t" '
           'xmlns="http://www.topografix.com/GPX/1/1"><trk><trkseg>'
           '<trkpt lat="42.97" lon="-0.095"/><trkpt lat="42.93" lon="-0.10"/>'
           '<trkpt lat="42.89" lon="-0.113"/></trkseg></trk></gpx>')
    return base64.b64encode(doc.encode()).decode()


def doc():
    return {
        "travel_description": {"title": "Drive", "start_date": "2026-06-08"},
        "days": [{
            "title": "Up the valley",
            "city": "Lourdes",
            "activities": [
                {"type": "point_of_interest", "name": "Sanctuary",
                 "coordinate": A, "duration": "1h"},
                {"type": "road", "legs": [
                    {"start_location": "Lourdes", "start_coordinate": A,
                     "end_location": "Argelès", "end_coordinate": B,
                     "duration": "30min"},
                    {"end_location": "Cauterets", "end_coordinate": C,
                     "duration": "25min"},
                ]},
            ],
        }],
    }


def legs_of(data):
    return [a for a in data["days"][0]["activities"] if a["type"] == "road"][0]["legs"]


def route_points(b64):
    root = ET.fromstring(gzip.decompress(base64.b64decode(b64)))
    assert root.find("g:trk", GPX_NS) is None, "a computed line must not be a track"
    return [(round(float(p.get("lat")), 6), round(float(p.get("lon")), 6))
            for p in root.findall("g:rte/g:rtept", GPX_NS)]


def rounded(line):
    return [(round(lat, 6), round(long, 6)) for lat, long in line]


def test_every_leg_gets_its_routed_line_marked_generated():
    data = doc()
    assert fill_routes(data, _FakeCache()) == (2, 0, 0)
    first, second = legs_of(data)
    for leg in (first, second):
        assert leg["gpx_generated"] is True
    a, b, c = ((p["lat"], p["long"]) for p in (A, B, C))
    assert route_points(first["gpx"]) == rounded(_bent(a, b))
    # The second leg inherits its departure from the first's arrival.
    assert route_points(second["gpx"]) == rounded(_bent(b, c))


def test_a_users_recording_is_left_alone():
    data = doc()
    legs_of(data)[1]["gpx"] = original = _recording()
    assert fill_routes(data, _FakeCache()) == (1, 1, 0)
    assert legs_of(data)[1]["gpx"] == original
    assert "gpx_generated" not in legs_of(data)[1]


def test_a_rerun_is_byte_stable_and_follows_a_moved_endpoint():
    data = doc()
    fill_routes(data, _FakeCache())
    once = json.dumps(data)
    fill_routes(data, _FakeCache())
    assert json.dumps(data) == once

    legs_of(data)[1]["end_coordinate"] = moved = {"lat": 42.80, "long": -0.15}
    fill_routes(data, _FakeCache())
    assert route_points(legs_of(data)[1]["gpx"])[-1] == (
        moved["lat"], moved["long"])


def test_the_stored_line_never_feeds_the_next_run(routed):
    """The model is rebuilt without the generated files, so a re-run routes
    again rather than reading back its own previous answer."""
    data = doc()
    fill_routes(data, _FakeCache())
    routed.clear()
    fill_routes(data, _FakeCache())
    assert len(routed) == 2


def test_an_unroutable_leg_keeps_its_previous_line(monkeypatch):
    import odysseyra_travelbook.maps.build as build

    data = doc()
    fill_routes(data, _FakeCache())
    before = copy.deepcopy(legs_of(data))
    monkeypatch.setattr(build, "route",
                        lambda a, b, cache, fallback=True: None if not fallback else [a, b])
    assert fill_routes(data, _FakeCache()) == (0, 0, 2)
    assert legs_of(data) == before

    fresh = doc()
    assert fill_routes(fresh, _FakeCache()) == (0, 0, 2)
    assert all("gpx" not in leg for leg in legs_of(fresh))


def test_a_hidden_drive_is_not_routed(routed):
    data = doc()
    data["days"][0]["activities"][1]["hide_on_map"] = True
    assert fill_routes(data, _FakeCache()) == (0, 0, 0)
    assert routed == []


def test_the_stored_line_is_drawn_without_routing(monkeypatch):
    import odysseyra_travelbook.maps.build as build

    data = doc()
    fill_routes(data, _FakeCache())

    def boom(*_a, **_k):
        raise AssertionError("a stored route must not be routed again")

    monkeypatch.setattr(build, "route", boom)
    itin = Itinerary.from_dict(data)
    road = next(a for a in itin.days[0].activities if a.kind == "road")
    named = [wp for wp in road.waypoints if wp.location]
    assert all(wp.gpx_generated for wp in named)
    lines = road_leg_lines(road, (A["lat"], A["long"]), _FakeCache())
    assert [len(seg) for _wp, seg in lines] == [3, 3]


def test_downstream_it_still_reads_as_computed():
    data = doc()
    fill_routes(data, _FakeCache())
    itin = Itinerary.from_dict(data)

    resolved = to_dict(itin)
    road = next(a for a in resolved["days"][0]["activities"] if a["type"] == "road")
    waypoints = road["waypoints"]
    assert [w["gpx_generated"] for w in waypoints if w["location"]] == [True, True]

    files = dict(gpx_files(itin, _FakeCache()))
    day = ET.fromstring(files["drive-day-01.gpx"])
    assert len(day.findall("g:rte", GPX_NS)) == 2
    assert day.findall("g:trk", GPX_NS) == []


def test_the_cli_writes_the_routes_back(tmp_path, capsys):
    path = tmp_path / "trip.json"
    path.write_text(json.dumps(doc()), encoding="utf-8")
    assert main(["route", str(path), "--cache-dir", str(tmp_path / "cache")]) == 0
    assert "Routed 2 drive leg(s)" in capsys.readouterr().out
    written = json.loads(path.read_text(encoding="utf-8"))
    assert all(leg["gpx_generated"] for leg in legs_of(written))


def _messages(data):
    return [f.message for f in validate_text(json.dumps(data, indent=1))]


def test_the_validator_flags_a_stale_generated_route():
    data = doc()
    fill_routes(data, _FakeCache())
    assert not [m for m in _messages(data) if "generated" in m]
    legs_of(data)[1]["end_coordinate"] = {"lat": 42.50, "long": -0.40}
    stale = [m for m in _messages(data) if "generated route" in m]
    assert len(stale) == 1 and "ends" in stale[0] and "re-run `route`" in stale[0]


def test_the_validator_checks_the_flag_itself():
    data = doc()
    legs_of(data)[0]["gpx_generated"] = True
    assert any("has no 'gpx'" in m for m in _messages(data))
    legs_of(data)[0]["gpx_generated"] = "maybe"
    assert any("'gpx_generated' must be true or false" in m for m in _messages(data))
