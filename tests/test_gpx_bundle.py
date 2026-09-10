"""The GPX export: one file per day plus one for the whole trip.

The decisions pinned here (see `gpx_bundle`'s module docstring for the why):

* a located **stop** is a `<wpt>`, a **computed** drive leg a `<rte>`, a
  **recorded** line (a hike's GPX, a road leg's) a `<trk>`;
* a transport leg gives its two endpoints and **no line** — a crow-flight line
  is fine to draw and wrong to export;
* the map switches (`show_map`, `include_maps_in_render`, `include_hike_maps`)
  don't reach it, but `coordinate.hide_on_map` does;
* the trip file is the day files' geometry in one document, duplicate waypoints
  collapsed;
* the days keep their position in the numbering, so a missing `day-03` means
  that day had nothing.
"""

import base64
import gzip
import io
import re
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

import pytest

from odysseyra_travelbook import Itinerary
from odysseyra_travelbook.gpx_bundle import (
    gpx_files,
    gpx_zip,
    slug_for,
    write_gpx_files,
)
from odysseyra_travelbook.models.gpx_export import (
    GpxLine,
    GpxPoint,
    gpx_document,
    route_gpx,
)

GPX_NS = {"g": "http://www.topografix.com/GPX/1/1"}


@pytest.fixture
def no_network(monkeypatch):
    """Fail loudly on any HTTP call: every fixture below is fully coordinated,
    so nothing here should geocode or route."""
    import odysseyra_travelbook.maps as maps

    def boom(url, timeout=20):  # noqa: ARG001
        raise AssertionError(f"unexpected network call: {url}")

    monkeypatch.setattr(maps, "http_get", boom)


def _gpx(points, name="trail"):
    """A tiny GPX file, base64-encoded as the JSON carries it."""
    rows = "".join(
        f'<trkpt lat="{lat}" lon="{long}"><ele>{ele}</ele></trkpt>'
        for lat, long, ele in points
    )
    doc = (
        '<?xml version="1.0"?><gpx version="1.1" creator="t" '
        'xmlns="http://www.topografix.com/GPX/1/1">'
        f"<trk><name>{name}</name><trkseg>{rows}</trkseg></trk></gpx>"
    )
    return base64.b64encode(doc.encode()).decode()


HIKE_GPX = _gpx([(42.85, 0.14, 1740), (42.86, 0.15, 1800), (42.87, 0.16, 1860)])


def doc(**over):
    """A two-day trip: a stop, a two-leg drive, a hike with a recording, a
    transport leg and a hotel — one of each kind of geometry."""
    data = {
        "travel_description": {"title": "Le Grand Tour", "start_date": "2026-06-08"},
        "defaults": {"timezone": 120},
        "days": [
            {
                "title": "Arrival",
                "city": "Lourdes",
                "activities": [
                    {
                        "type": "point_of_interest",
                        "name": "Sanctuary",
                        "coordinate": {"lat": 43.0974, "long": -0.0583},
                        "duration": "1h",
                    },
                    {
                        "type": "road",
                        "legs": [
                            {
                                "start_location": "Lourdes",
                                "start_coordinate": {"lat": 43.0974, "long": -0.0583},
                                "end_location": "Argelès",
                                "end_coordinate": {"lat": 42.9700, "long": -0.0950},
                                "duration": "30min",
                            },
                            {
                                "end_location": "Cauterets",
                                "end_coordinate": {"lat": 42.8900, "long": -0.1130},
                                "duration": "25min",
                            },
                        ],
                    },
                ],
            },
            {
                "title": "The lake",
                "city": "Cauterets",
                "activities": [
                    {
                        "type": "hike",
                        "name": "Lac de Gaube",
                        "gpx": HIKE_GPX,
                        "duration": "3h",
                    },
                    {
                        "type": "place",
                        "name": "Cauterets",
                        "coordinate": {"lat": 42.8900, "long": -0.1130},
                        "activities": [
                            {
                                "type": "point_of_interest",
                                "name": "The thermal baths",
                                "coordinate": {"lat": 42.8890, "long": -0.1120},
                            },
                        ],
                    },
                ],
            },
        ],
        "transport": [
            {
                "type": "plane",
                "legs": [
                    {
                        "start": "Paris CDG",
                        "end": "Toulouse",
                        "start_date": "2026-06-08",
                        "start_time": "07:00",
                        "duration": "1h20",
                        "start_coordinate": {"lat": 49.0097, "long": 2.5479},
                        "end_coordinate": {"lat": 43.6350, "long": 1.3678},
                    },
                ],
            },
        ],
        "accommodations": [
            {
                "name": "Hôtel du Lac",
                "arrival": "2026-06-08",
                "departure": "2026-06-10",
                "city": "Cauterets",
                "coordinate": {"lat": 42.8880, "long": -0.1140},
            },
        ],
    }
    data.update(over)
    return data


def files_of(data, lang="en"):
    """``{filename: parsed XML}`` for an itinerary dict, with routing stubbed to
    a straight two-point line so no network is involved."""
    return gpx_files(Itinerary.from_dict(data), _FakeCache(), lang)


class _FakeCache:
    """Stands in for ``maps.Cache``: routes are answered from memory (the two
    endpoints, which is all these tests need of a drive's shape)."""

    def __init__(self):
        self.geocode = {}
        self.routes = {}
        self.dir = Path("/nonexistent")

    @property
    def tiles(self):
        return self.dir / "tiles"

    def save(self):
        pass


@pytest.fixture(autouse=True)
def straight_routes(monkeypatch):
    """Answer every routing request with the straight pair. `_road_route` and
    `road_leg_lines` are the only callers here, and what they do with the line
    is what's under test — not OSRM's shape of it."""
    import odysseyra_travelbook.maps.build as build

    monkeypatch.setattr(build, "route", lambda a, b, cache, fallback=True: [a, b])


def parse(text):
    return ET.fromstring(text)


def names(tree, tag):
    return [e.findtext("g:name", "", GPX_NS) for e in tree.findall(f"g:{tag}", GPX_NS)]


# --- the file set -----------------------------------------------------------

def test_one_file_per_day_plus_the_whole_trip(no_network):
    got = [name for name, _ in files_of(doc())]
    assert got == [
        "le-grand-tour.gpx",
        "le-grand-tour-day-01.gpx",
        "le-grand-tour-day-02.gpx",
    ]


def test_a_day_with_nothing_located_gets_no_file_and_keeps_its_number(no_network):
    """A missing `day-02` says that day had nothing — the numbering is the day's
    position in the trip, not its position in the output."""
    data = doc()
    data["days"].insert(1, {"title": "A rest day"})
    data["accommodations"] = []  # the hotel would otherwise locate every day
    got = [name for name, _ in files_of(data)]
    assert got == [
        "le-grand-tour.gpx",
        "le-grand-tour-day-01.gpx",
        "le-grand-tour-day-03.gpx",
    ]


def test_a_trip_with_no_geometry_exports_nothing(no_network):
    """Not an empty file per day: there is nothing to put in one."""
    data = {"travel_description": {"title": "Nowhere"},
            "days": [{"title": "A day", "activities": [
                {"type": "point_of_interest", "name": "Somewhere"}]}]}
    assert files_of(data) == []
    with pytest.raises(ValueError):
        gpx_zip(Itinerary.from_dict(data), _FakeCache())


def test_the_trip_file_is_the_days_geometry_in_one_document(no_network):
    files = dict(files_of(doc()))
    trip = parse(files["le-grand-tour.gpx"])
    days = [parse(t) for n, t in files.items() if "day-" in n]
    for tag in ("rte", "trk"):
        assert len(trip.findall(f"g:{tag}", GPX_NS)) == sum(
            len(d.findall(f"g:{tag}", GPX_NS)) for d in days)
    # Waypoints are deduped across the trip, so they are a *subset*: the hotel
    # is the same place on both nights.
    day_points = {(e.get("lat"), e.get("lon"), e.findtext("g:name", "", GPX_NS))
                  for d in days for e in d.findall("g:wpt", GPX_NS)}
    trip_points = {(e.get("lat"), e.get("lon"), e.findtext("g:name", "", GPX_NS))
                   for e in trip.findall("g:wpt", GPX_NS)}
    assert trip_points == day_points
    assert len(trip.findall("g:wpt", GPX_NS)) < sum(
        len(d.findall("g:wpt", GPX_NS)) for d in days)


def test_the_schema_order_is_metadata_waypoints_routes_tracks(no_network):
    """A file that lists them otherwise is rejected by strict readers."""
    trip = parse(dict(files_of(doc()))["le-grand-tour.gpx"])
    tags = [re.sub(r"\{.*\}", "", child.tag) for child in trip]
    assert tags == sorted(tags, key=["metadata", "wpt", "rte", "trk"].index)


# --- what each kind of geometry becomes -------------------------------------

def test_a_drive_is_one_route_per_leg_named_for_its_two_ends(no_network):
    """Per leg, so a junction is named as the end of one route and the start of
    the next — which is why a drive's own map pins aren't exported."""
    day1 = parse(dict(files_of(doc()))["le-grand-tour-day-01.gpx"])
    assert names(day1, "rte") == ["Lourdes → Argelès", "Argelès → Cauterets"]


def test_a_recorded_line_is_a_track_not_a_route(no_network):
    day2 = parse(dict(files_of(doc()))["le-grand-tour-day-02.gpx"])
    assert names(day2, "trk") == ["Lac de Gaube"]
    assert day2.findall("g:rte", GPX_NS) == []
    assert len(day2.findall("g:trk/g:trkseg/g:trkpt", GPX_NS)) == 3


def test_a_road_legs_recording_is_a_track_while_its_sibling_stays_a_route(no_network):
    """The same distinction inside one drive: the leg with a GPX was really
    driven, the routed one is a computed way to go."""
    data = doc()
    data["days"][0]["activities"][1]["legs"][1]["gpx"] = HIKE_GPX
    day1 = parse(dict(files_of(data))["le-grand-tour-day-01.gpx"])
    assert names(day1, "rte") == ["Lourdes → Argelès"]
    assert names(day1, "trk") == ["Argelès → Cauterets"]


def test_a_transport_leg_gives_its_endpoints_and_no_line(no_network):
    """A crow-flight line is fine to draw (the map's dotted leg) and wrong to
    export — a flight has no path on the ground at all."""
    day1 = parse(dict(files_of(doc()))["le-grand-tour-day-01.gpx"])
    assert {"Paris CDG", "Toulouse"} <= set(names(day1, "wpt"))
    assert names(day1, "rte") == ["Lourdes → Argelès", "Argelès → Cauterets"]


def test_the_nights_stay_and_a_places_nested_stops_are_waypoints(no_network):
    day2 = parse(dict(files_of(doc()))["le-grand-tour-day-02.gpx"])
    assert set(names(day2, "wpt")) >= {
        "Cauterets", "The thermal baths", "Hôtel du Lac"}


def test_a_hikes_named_points_come_along(no_network):
    """The recording's own `<wpt name=…>`s — the col, the lake you turn at.

    Placed mid-trail on purpose: one within `_TERMINAL_MERGE_KM` of either
    trailhead is dropped by the model, the start/finish marker saying it
    already."""
    data = doc()
    gpx = (
        '<?xml version="1.0"?><gpx version="1.1" creator="t" '
        'xmlns="http://www.topografix.com/GPX/1/1">'
        '<wpt lat="42.90" lon="0.20"><name>Le col</name></wpt>'
        '<trk><trkseg>'
        '<trkpt lat="42.85" lon="0.14"/><trkpt lat="42.90" lon="0.20"/>'
        '<trkpt lat="42.95" lon="0.26"/>'
        "</trkseg></trk></gpx>"
    )
    data["days"][1]["activities"][0]["gpx"] = base64.b64encode(gpx.encode()).decode()
    day2 = parse(dict(files_of(data))["le-grand-tour-day-02.gpx"])
    assert "Le col" in names(day2, "wpt")


def test_every_waypoint_says_which_day_it_belongs_to(no_network):
    """The `<desc>` is the one place the day is named — which is what lets the
    trip file stay readable with 40 waypoints in it."""
    trip = parse(dict(files_of(doc()))["le-grand-tour.gpx"])
    descs = {e.findtext("g:desc", "", GPX_NS) for e in trip.findall("g:wpt", GPX_NS)}
    assert descs == {"Day 1 · Jun 08, 2026 · Arrival",
                     "Day 2 · Jun 09, 2026 · The lake"}


def test_the_day_label_is_localized(no_network):
    trip = parse(dict(files_of(doc(), "fr"))["le-grand-tour.gpx"])
    descs = {e.findtext("g:desc", "", GPX_NS) for e in trip.findall("g:wpt", GPX_NS)}
    assert "Jour 1 · 08 juin 2026 · Arrival" in descs


# --- which switches reach it ------------------------------------------------

def test_hide_on_map_hides_a_point(no_network):
    """The nearest thing the format has to "leave this out" — and honouring it
    is what keeps the export from drifting from the maps."""
    data = doc()
    data["days"][0]["activities"][0]["coordinate"]["hide_on_map"] = True
    day1 = parse(dict(files_of(data))["le-grand-tour-day-01.gpx"])
    assert "Sanctuary" not in names(day1, "wpt")


def test_hide_on_map_on_a_road_drops_its_route(no_network):
    data = doc()
    data["days"][0]["activities"][1]["hide_on_map"] = True
    day1 = parse(dict(files_of(data))["le-grand-tour-day-01.gpx"])
    assert day1.findall("g:rte", GPX_NS) == []


@pytest.mark.parametrize("switch", [
    {"days": "show_map"},                     # the day's own overview map
    {"place": "show_map"},                    # a place's zoom map
    {"defaults": "include_maps_in_render"},   # the whole trip's printed maps
    {"defaults": "include_hike_maps"},        # the hike figures
])
def test_a_map_switch_does_not_reach_the_export(no_network, switch):
    """A GPX file is not a map: `show_map` drops the map an object *draws*, and
    the two `defaults` switches decide what a **book** carries. Asking for this
    export is itself the opt-in for the geometry."""
    data = doc()
    (where, key), = switch.items()
    if where == "days":
        for day in data["days"]:
            day[key] = False
    elif where == "place":
        data["days"][1]["activities"][1][key] = False
        data["days"][1]["activities"][0][key] = False  # the hike's trail map
    else:
        data["defaults"][key] = False
    assert dict(files_of(data)) == dict(files_of(doc()))


# --- the archive ------------------------------------------------------------

def test_the_zip_holds_exactly_the_files_the_cli_writes(no_network, tmp_path):
    itinerary = Itinerary.from_dict(doc())
    written = write_gpx_files(itinerary, tmp_path, _FakeCache())
    archive = zipfile.ZipFile(io.BytesIO(gpx_zip(itinerary, _FakeCache())))
    assert archive.namelist() == [p.name for p in written]
    for path in written:
        assert archive.read(path.name).decode() == path.read_text(encoding="utf-8")


def test_the_zip_is_byte_identical_on_a_second_export(no_network):
    """No timestamps anywhere — in the archive or in the GPX — so an export is
    diffable against the last one."""
    itinerary = Itinerary.from_dict(doc())
    assert gpx_zip(itinerary, _FakeCache()) == gpx_zip(itinerary, _FakeCache())


def test_slug_for_matches_the_viewers_slugify():
    """The archive is named by the browser (`file/saveExport.ts`) and its
    contents here, so one trip must read as one name across the two."""
    assert slug_for("Grand Tour of France") == "grand-tour-of-france"
    # Accents are dropped rather than turned into separators — the naive
    # NFKD-then-strip-non-alnum reading spells "Pyrénées" `pyre-ne-es`.
    assert slug_for("Pyrénées & Cañón") == "pyrenees-canon"
    assert slug_for("  Trip (2026)!  ") == "trip-2026"
    assert slug_for("") == "odysseyra"


# --- the serializer ---------------------------------------------------------

def test_a_document_can_hold_all_three_kinds():
    text = gpx_document(
        "Trip",
        waypoints=[GpxPoint(1.5, 2.5, "A stop", "Day 1")],
        routes=[GpxLine([(1.0, 2.0), (1.1, 2.1)], "A → B")],
        tracks=[GpxLine([(3.0, 4.0), (3.1, 4.1)], "A walk")],
    )
    tree = parse(text)
    assert tree.findtext("g:metadata/g:name", "", GPX_NS) == "Trip"
    assert names(tree, "wpt") == ["A stop"]
    assert names(tree, "rte") == ["A → B"]
    assert names(tree, "trk") == ["A walk"]


def test_a_line_needs_two_points():
    with pytest.raises(ValueError):
        gpx_document(tracks=[GpxLine([(1.0, 2.0)], "nowhere")])


def test_a_bare_waypoint_is_self_closing():
    assert '<wpt lat="1.000000" lon="2.000000"/>' in gpx_document(
        waypoints=[GpxPoint(1, 2)])


def test_route_gpx_still_writes_one_route():
    """The viewer's (Build GPX file) link goes through this; it is now the
    single-line case of `gpx_document`."""
    text = route_gpx([(42.0, 1.0), (42.1, 1.1)], "A → B")
    assert parse(text).findall("g:trk", GPX_NS) == []
    assert names(parse(text), "rte") == ["A → B"]


# --- the flagship example ---------------------------------------------------

def test_the_example_trip_exports(no_network):
    """`france.json` is fully coordinated, so this needs no network — and it is
    the check that the whole pipeline holds on a real file."""
    itinerary = Itinerary.from_json_file(
        Path(__file__).parent.parent / "examples" / "france.json")
    files = gpx_files(itinerary, _FakeCache())
    assert [n for n, _ in files][0] == "grand-tour-of-france.gpx"
    assert len(files) == 1 + len(itinerary.days)
    trip = parse(files[0][1])
    assert trip.findall("g:wpt", GPX_NS)
    assert trip.findall("g:rte", GPX_NS)
    assert trip.findall("g:trk", GPX_NS)  # the Lac de Gaube recording


def test_gzipped_geometry_is_no_different(no_network):
    """A `gpx` may arrive gzipped (models/gpx.py inflates it); nothing here
    should notice."""
    plain = '<?xml version="1.0"?><gpx version="1.1" creator="t" xmlns="http://www.topografix.com/GPX/1/1"><trk><trkseg><trkpt lat="42.85" lon="0.14"/><trkpt lat="42.87" lon="0.16"/></trkseg></trk></gpx>'
    data = doc()
    data["days"][1]["activities"][0]["gpx"] = base64.b64encode(
        gzip.compress(plain.encode())).decode()
    day2 = parse(dict(files_of(data))["le-grand-tour-day-02.gpx"])
    assert len(day2.findall("g:trk/g:trkseg/g:trkpt", GPX_NS)) == 2
