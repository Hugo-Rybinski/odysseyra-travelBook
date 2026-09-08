"""``coordinate.hide_on_map`` — keep the point, drop its pin.

Three things this pins down:

* the flag is **default false**, so a coordinate that says nothing is plotted;
* it hides the *pin only* — the ``(Navigate)`` link, the printed coordinates and
  the sunrise/sunset reference all still use the point (those live in
  ``test_ink_saver_coordinates.py`` and ``test_sun.py``); and
* the retired spelling ``show_on_map`` is still **read**, negated, because it was
  reversed rather than moved: dropping it would plot the pin the file asked to
  hide. ``validate`` warns about it, and the viewer's ``edit/migrate.ts``
  rewrites it on load.

No example sets ``hide_on_map``: the example PDFs are the review artifact and
should show every pin they can, so the behaviour lives here instead.
"""

from PIL import Image
import json
import pytest

from odysseyra_travelbook.maps import build as mapbuild
from odysseyra_travelbook.maps.build import day_legs, resolve_day, resolve_trip
from odysseyra_travelbook.models import Itinerary
from odysseyra_travelbook.validate import validate_text


@pytest.fixture
def drawn(monkeypatch):
    """Render the day maps offline, capturing what each one was handed."""
    calls = []

    def fake_render_map(all_coords, routes, points, accent, tiles_dir, **kw):
        calls.append({"points": list(points), "labels": list(kw.get("labels") or [])})
        return Image.new("RGB", (10, 10))

    monkeypatch.setattr(mapbuild, "render_map", fake_render_map)
    return calls


class _NoCache:
    """Enough of a `Cache` for the stubbed renderer: nothing is fetched."""
    tiles = None


def _itin(days, **extra):
    return Itinerary.from_dict({
        "travel_description": {"title": "T", "start_date": "2026-06-01"},
        "defaults": {"include_maps_in_render": True},
        "days": days,
        **extra,
    })


def _poi(name, lat, long, **coord):
    return {"type": "point_of_interest", "name": name,
            "coordinate": {"lat": lat, "long": long, **coord}}


# -- the flag itself ---------------------------------------------------------

def test_a_hidden_point_keeps_its_coordinate_but_loses_its_pin():
    it = _itin([{"title": "D", "city": "Pau", "activities": [
        _poi("Shown", 43.29, -0.36),
        _poi("Hidden", 43.30, -0.37, hide_on_map=True),
    ]}])
    shown, hidden = it.days[0].activities[:2]
    assert hidden.coordinate is not None          # still on the object
    assert hidden.coordinate.hide_on_map is True
    assert shown.coordinate.hide_on_map is False  # the default

    points, _routes, _nodes, _areas = resolve_day(it.days[0], it, cache=None)
    assert [p.label for p in points] == ["Shown"]


def test_a_hidden_point_takes_no_number_from_the_sequence(drawn):
    """The 1..N discs are the map's legend, so a hidden stop must not consume a
    number and leave a gap in what the itinerary prints."""
    it = _itin([{"title": "D", "city": "Pau", "activities": [
        _poi("First", 43.29, -0.36),
        _poi("Hidden", 43.30, -0.37, hide_on_map=True),
        _poi("Second", 43.31, -0.38),
    ]}])
    maps = mapbuild.render_day_maps(it.days[0], it, cache=_NoCache())
    first, hidden, second = it.days[0].activities[:3]
    assert maps.numbers[id(first)] == "1"
    assert maps.numbers[id(second)] == "2"
    assert id(hidden) not in maps.numbers
    assert [c["labels"] for c in drawn] == [["1", "2"]]


def test_a_hidden_stay_is_not_pinned_on_the_day_or_the_trip_map(drawn):
    days = [{"title": "D", "city": "Pau", "date": "2026-06-01",
             "activities": [_poi("Shown", 43.29, -0.36)]}]
    stay = {"name": "Hotel", "city": "Pau",
            "arrival": "2026-06-01", "departure": "2026-06-02",
            "coordinate": {"lat": 43.28, "long": -0.35, "hide_on_map": True}}
    it = _itin(days, accommodations=[stay])
    maps = mapbuild.render_day_maps(it.days[0], it, cache=_NoCache())
    assert id(it.accommodations[0]) not in maps.numbers
    assert [c["labels"] for c in drawn] == [["1"]]      # no ★ handed to the map
    _points, labels, _routes, _legs = resolve_trip(it, cache=None)
    assert labels == ["1"]                              # the day's pin, not the stay's


def test_a_hidden_leg_endpoint_drops_the_dotted_line():
    it = _itin(
        [{"title": "D", "date": "2026-06-01", "activities": []}],
        transport=[{"type": "plane", "legs": [{
            "start": "A", "end": "B",
            "start_date": "2026-06-01", "start_time": "10:00", "duration": "2h",
            "start_coordinate": {"lat": 40.0, "long": -70.0, "hide_on_map": True},
            "end_coordinate": {"lat": 48.0, "long": 2.0}}]}],
    )
    assert day_legs(it.days[0], it) == []


# -- the retired spelling ---------------------------------------------------

def test_show_on_map_false_still_hides_the_pin():
    """A file on the older shape renders as it always did — the key was
    reversed, not moved, so ignoring it would *show* the hidden pin."""
    it = _itin([{"title": "D", "city": "Pau", "activities": [
        _poi("Shown", 43.29, -0.36),
        _poi("Hidden", 43.30, -0.37, show_on_map=False),
    ]}])
    points, _routes, _nodes, _areas = resolve_day(it.days[0], it, cache=None)
    assert [p.label for p in points] == ["Shown"]


def test_the_validator_names_the_retired_spelling():
    doc = {
        "travel_description": {"title": "T", "start_date": "2026-06-01"},
        "days": [{"title": "D", "activities": [_poi("P", 43.29, -0.36,
                                                    show_on_map=False)]}],
    }
    findings = validate_text(json.dumps(doc, indent=2))
    hits = [f for f in findings if "show_on_map" in f.message]
    assert len(hits) == 1
    assert hits[0].level == "warning"          # nothing is lost: the model reads it
    assert "'hide_on_map': true" in hits[0].message
    # and it says nothing about a file already on the current shape
    current = json.dumps({**doc, "days": [{"title": "D", "activities": [
        _poi("P", 43.29, -0.36, hide_on_map=True)]}]}, indent=2)
    assert not [f for f in validate_text(current) if "show_on_map" in f.message]
