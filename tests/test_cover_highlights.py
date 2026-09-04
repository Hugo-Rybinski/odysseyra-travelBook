"""The cover's day-by-day HIGHLIGHTS cell: which of a day's items it advertises.

A drive is how you got to the day's stops rather than what the day is for, so it
is dropped once there are two other stops to name — the cell is a few words on a
table row. The viewer's `Cover.tsx`'s `highlightsOf` implements the same rule
from the resolved document; there is no JS test runner, so this is the contract
both sides answer to.
"""

from odysseyra_travelbook.models import Itinerary
from odysseyra_travelbook.pdf import TravelPDF


def _poi(name, **kw):
    return {"type": "point_of_interest", "name": name, "duration": "1h", **kw}


def _road(start, end, duration):
    # A road's title is its route, and the arrival is a point on the drawn line,
    # so it has to be located.
    return {"type": "road", "duration": duration,
            "legs": [{"start_location": start, "end_location": end,
                      "end_coordinate": {"lat": 43.0, "long": 0.0}}]}


def _highlights(activities, transport=None, lang="en"):
    doc = {
        "travel_description": {"title": "T", "cover_color": "#2f6b4f"},
        "days": [{"title": "d", "date": "2026-06-01", "city": "X",
                  "activities": activities}],
    }
    if transport:
        doc["transport"] = transport
    it = Itinerary.from_dict(doc)
    return TravelPDF(it, lang, False, "google")._day_highlights(it.days[0])


def test_one_stop_keeps_the_long_drive():
    # Below two stops the drive is part of what the day is: a single visit and a
    # three-hour transfer reads as both.
    assert _highlights([_road("Amboise", "Sarlat", "3h"), _poi("Château")]) == (
        "Road Amboise → Sarlat, Château")


def test_two_stops_drop_the_drive():
    assert _highlights([_road("Amboise", "Sarlat", "3h"),
                        _poi("Château"), _poi("Village")]) == "Château, Village"


def test_a_short_drive_was_never_a_highlight_anyway():
    # The >60 min rule predates this one and still applies first.
    assert _highlights([_road("Sarlat", "Domme", "20 min"), _poi("Château")]) == "Château"


def test_a_transport_leg_does_not_count_toward_the_two():
    """A leg isn't an activity, and a flight day is exactly when the drive to
    the airport is worth naming — so one stop plus a flight keeps the drive."""
    out = _highlights(
        [_road("Paris", "CDG", "1h30"), _poi("Louvre")],
        transport=[{"type": "plane", "legs": [
            {"start": "CDG", "end": "Rome", "start_date": "2026-06-01",
             "start_time": "18:00", "duration": "2h"}]}])
    assert "Road Paris → CDG" in out and "Louvre" in out and "Plane" in out


def test_a_detour_stop_does_not_count_toward_the_two():
    # A detour is never a highlight, so it can't crowd the drive out either.
    assert _highlights([_road("Amboise", "Sarlat", "3h"),
                        _poi("Château"), _poi("Maybe", detour=True)]) == (
        "Road Amboise → Sarlat, Château")


def test_a_pure_driving_day_still_falls_back_to_its_drives():
    # Nothing else to advertise at all, so the day's drives are all there is —
    # short ones included, which is what the fallback is for.
    assert _highlights([_road("Amboise", "Blois", "20 min"),
                        _road("Blois", "Sarlat", "40 min")]) == (
        "Road Amboise → Blois, Road Blois → Sarlat")


def test_the_rule_counts_places_and_hikes_too():
    acts = [_road("Amboise", "Sarlat", "3h"),
            {"type": "place", "name": "Old town", "duration": "2h"},
            {"type": "hike", "name": "Ridge loop", "duration": "3h"}]
    assert _highlights(acts) == "Old town, Ridge loop"
