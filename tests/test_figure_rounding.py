"""Display rounding for the book's two measured figures.

A distance is routed or copied off a guidebook and a climb is accumulated off a
GPS altimeter, so neither is exact — and the precision a reader can *use* falls
off with the magnitude. The step therefore coarsens as the number grows. The
viewer computes the same thing in ``web/src/render/format.ts`` (``roundKm`` /
``roundElevation``); there is no JS test runner in this repo, so these are the
tests that pin the contract both sides implement.
"""

import pytest

from odysseyra_travelbook.models import (format_elevation, format_km,
                                         round_elevation, round_km)


@pytest.mark.parametrize("value, shown", [
    # under 10 km — a tenth, the difference between two afternoons on foot
    (0.42, "0.4 km"),
    (3.44, "3.4 km"),
    (8.47, "8.5 km"),
    (9.96, "10 km"),      # snaps up over the band boundary, and drops the ".0"
    # 10 to 20 km inclusive — halves
    (10.0, "10 km"),
    (12.3, "12.5 km"),
    (12.7, "12.5 km"),
    (17.4, "17.5 km"),
    (20.0, "20 km"),
    # over 20 km — whole kilometres; 341 and 342 are the same day's driving
    (20.4, "20 km"),
    (21.6, "22 km"),
    (345.7, "346 km"),
])
def test_a_distance_coarsens_as_it_grows(value, shown):
    assert format_km(value) == shown


@pytest.mark.parametrize("value, shown", [
    (12, "10 m"),         # under 100 m — fives
    (47, "45 m"),
    (63, "65 m"),
    (99, "100 m"),        # snaps up over the band boundary
    (100, "100 m"),       # from 100 m — tens
    (128, "130 m"),
    (784, "780 m"),
    (1237, "1240 m"),
])
def test_a_climb_coarsens_at_a_hundred_metres(value, shown):
    assert format_elevation(value) == shown


def test_the_band_boundaries_sit_where_the_spec_puts_them():
    """10 km and 20 km belong to the *coarser* band below them, and 100 m to the
    finer band under it — so each boundary is named once, not twice."""
    assert round_km(10.04) == 10.0        # 0.1 step still, at exactly 10
    assert round_km(20.24) == 20.0        # 0.5 step still, at exactly 20
    assert round_km(20.6) == 21           # whole km from just above it
    assert round_elevation(99) == 100     # 5 step at 99
    assert round_elevation(104) == 100    # 10 step at 104, so it rounds down


def test_an_unset_figure_prints_nothing():
    """Both formatters are called straight into a `·`-joined parts list that
    filters falsy entries, so a missing figure has to come back empty rather
    than as "None"."""
    assert format_km(None) == ""
    assert format_elevation(None) == ""


def test_a_rounded_distance_never_shows_a_trailing_zero():
    """`12.0 km` reads as a measurement to the tenth that happens to land flat;
    the figure is only good to the half here, so it prints `12 km`."""
    assert format_km(12.1) == "12 km"
    assert format_km(11.9) == "12 km"
