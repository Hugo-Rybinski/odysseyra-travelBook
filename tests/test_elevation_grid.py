"""The elevation profile's horizontal scale.

A curve drawn between a low and a high mark says how much you climb; it does not
say how high you are anywhere in between, which on a mountain day is the
question. So both renderers rule the band at round altitudes, and the step is
chosen by ``models/parsers.py``'s ``elevation_grid``. The viewer computes the
same thing in ``web/src/render/format.ts`` (``elevationGrid``); there is no JS
test runner in this repo, so these are the tests that pin the contract both
sides implement — the two figures must be ruled identically or the book and the
screen disagree about the same walk.
"""

import pytest

from odysseyra_travelbook.models import elevation_grid
from odysseyra_travelbook.models.parsers import MAX_GRID_LINES


def test_the_asked_for_example():
    # a Kyrgyz day: 2432 m to 3245 m gets a line every 100 m
    assert elevation_grid(2432, 3245) == [2500, 2600, 2700, 2800, 2900,
                                          3000, 3100, 3200]


@pytest.mark.parametrize("low, high, lines", [
    # a 300 m Pyrenean climb — fifties
    (400, 700, [450, 500, 550, 600, 650]),
    # a 1100 m range coarsens past 100 m, which would want ten lines
    (1000, 2100, [1200, 1400, 1600, 1800, 2000]),
    # a stroll along a river: a 12 m range still gets the 5 m ladder's foot
    (100, 112, [105, 110]),
    # sea level to the roof of the world, on kilometres
    (0, 8848, [1000, 2000, 3000, 4000, 5000, 6000, 7000, 8000]),
    # floats, as a resolved profile's samples really are
    (1200.4, 1207.9, [1205]),
])
def test_the_step_is_the_coarsest_that_fits(low, high, lines):
    assert elevation_grid(low, high) == lines


@pytest.mark.parametrize("low, high", [
    (100, 103),      # too flat to hold a round line at all
    (2400.5, 2404),  # ditto, between two multiples of five
    (500, 500),      # a profile with one elevation in it
    (700, 400),      # inverted — nothing to rule
])
def test_a_flat_walk_is_ruled_by_its_low_and_high_marks_alone(low, high):
    assert elevation_grid(low, high) == []


@pytest.mark.parametrize("low", [0, 37, 812.5, 2432, 6000])
@pytest.mark.parametrize("climb", [8, 25, 140, 813, 1600, 4200])
def test_a_line_never_falls_outside_the_walk(low, climb):
    """Lines are drawn strictly between the two marks: the band's padding above
    and below them is air the walk never reached, and a line there would be
    ruling it."""
    lines = elevation_grid(low, low + climb)
    assert len(lines) <= MAX_GRID_LINES
    assert all(low < m < low + climb for m in lines)
    # one step throughout, so the band reads as a scale rather than a guess
    steps = {b - a for a, b in zip(lines, lines[1:])}
    assert len(steps) <= 1
