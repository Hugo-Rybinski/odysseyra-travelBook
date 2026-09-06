"""Ink-saver prints the coordinates where the "(Navigate)" link would have gone.

``--ink-saver`` drops every hyperlink — a link is accent emphasis, which is what
the mode exists to stop spending — which used to leave the *printed* book, the
one most likely to be read away from a screen, with no way at all to get from an
address to the point it means. The bare ``lat, long`` now stands in for the link.
"""

import json
from pathlib import Path

import pytest

from odysseyra_travelbook import Itinerary, build_pdf
from odysseyra_travelbook.models import Coordinate, format_coordinate
from odysseyra_travelbook.pdf import TravelPDF
from odysseyra_travelbook.pdf.base import FAINT

EXAMPLES = Path(__file__).resolve().parent.parent / "examples"
EXAMPLE = EXAMPLES / "pyrenees.json"

# Somewhere in Lourdes, to 5 decimals and beyond.
POINT = Coordinate(43.09742, -0.05828)


def _pdf(ink_saver: bool) -> TravelPDF:
    """A page-ready renderer over the example trip, maps left alone."""
    pdf = TravelPDF(Itinerary.from_json_file(str(EXAMPLE)), "en", ink_saver,
                    "google")
    pdf.add_page()
    return pdf


# -- the formatter ---------------------------------------------------------

def test_five_decimals_each_way():
    # ~1 m — finer than a hand-written travel coordinate is meant to be.
    assert format_coordinate(POINT) == "43.09742, -0.05828"


def test_trailing_zeros_are_kept():
    # Every pair then reads at the same width down a page, and the fixed number
    # of decimals states the precision rather than implying an exact value.
    assert format_coordinate(Coordinate(43.1, -0.5)) == "43.10000, -0.50000"


def test_more_precision_than_we_print_is_rounded():
    assert format_coordinate(Coordinate(43.0974249, -0.0582751)) == \
        "43.09742, -0.05828"


def test_no_coordinate_formats_to_nothing():
    assert format_coordinate(None) == ""


# -- the affordance --------------------------------------------------------

def test_normal_mode_still_links():
    label, url = _pdf(False)._nav_affordance(POINT, "Lourdes")
    assert label == "(Navigate)"
    assert url.startswith("https://")


def test_ink_saver_prints_the_point_and_links_nothing():
    label, url = _pdf(True)._nav_affordance(POINT, "Lourdes")
    assert label == "43.09742, -0.05828"
    assert url == ""


def test_show_on_map_false_still_prints_them():
    # That flag hides the point's *pin* on a map something else draws; this is
    # the text beside its address, so the two don't interact.
    hidden = Coordinate(43.09742, -0.05828, show_on_map=False)
    assert _pdf(True)._nav_affordance(hidden, "Lourdes")[0] == \
        "43.09742, -0.05828"


def test_an_address_only_target_prints_nothing():
    # There is no point to print, and the address is already on the row the
    # label would trail.
    assert _pdf(True)._nav_affordance(None, "Lourdes")[0] == ""


def test_nothing_locatable_prints_nothing_either_way():
    assert _pdf(True)._nav_affordance(None)[0] == ""
    assert _pdf(False)._nav_affordance(None)[0] == ""


def test_the_label_is_faint_not_accent():
    # The colour is the mode's whole point: an unclickable coordinate is
    # secondary data, not emphasis. FAINT is lighter than the row it trails.
    pdf = _pdf(True)
    assert FAINT != pdf.accent


# -- the rows that draw it -------------------------------------------------

@pytest.mark.parametrize("text", [
    "3h30  ·  1 Av. Mgr Théas, Lourdes",   # the usual meta line
    "",                                     # no meta: the label owns the line
    "A stated address long enough that the trailing coordinates cannot share "
    "its last line and have to drop below it, which is the case the reserved "
    "height has to get right",
])
@pytest.mark.parametrize("ink_saver", [False, True])
def test_the_reserved_height_is_the_height_drawn(text, ink_saver):
    """``_nav_block_h`` is what every card reserves space by, so it has to
    agree with ``_line_with_nav`` under *both* labels — the coordinates are
    wider than "(Navigate)", hence likelier to take a line of their own."""
    pdf = _pdf(ink_saver)
    w = pdf.content_width
    reserved = pdf._nav_block_h(text, POINT, "Lourdes", w=w)
    before = pdf.get_y()
    pdf._line_with_nav(pdf.l_margin, w, text, POINT, "Lourdes")
    assert pdf.get_y() - before == pytest.approx(reserved)


def test_a_road_leg_row_draws_the_point_of_its_arrival():
    # The VIA list measures its route and tail before drawing anything (the
    # row's height decides whether it starts on the page at all), so the wider
    # label has to leave it laying out and advancing.
    pdf = _pdf(True)
    day = pdf.itinerary.days[3]            # the 3-leg drive out of Gavarnie
    road = next(a for a in day.activities if a.kind == "road")
    y = pdf.get_y()
    pdf._road_waypoints(pdf.l_margin, pdf.content_width, road)
    assert pdf.get_y() > y


def test_the_stay_bar_keeps_its_height():
    # The bar is pinned near the page foot and truncates its address line to
    # leave room for the label, so a wider label must not grow it.
    heights = []
    for ink_saver in (False, True):
        pdf = _pdf(ink_saver)
        pdf.set_y(20)
        pdf._day_stay(pdf.itinerary.days[0])
        heights.append(pdf.get_y())
    assert heights[0] == pytest.approx(heights[1])


# -- the whole book --------------------------------------------------------

def _text(path: Path) -> str:
    pypdf = pytest.importorskip("pypdf")
    return "\n".join(p.extract_text() for p in pypdf.PdfReader(str(path)).pages)


def test_an_ink_saver_book_prints_points_a_normal_one_links(tmp_path):
    doc = json.loads(EXAMPLE.read_text(encoding="utf-8"))
    doc.setdefault("defaults", {})["include_maps_in_render"] = False
    it = Itinerary.from_dict(doc)
    ink = _text(build_pdf(it, tmp_path / "ink.pdf", ink_saver=True))
    plain = _text(build_pdf(it, tmp_path / "plain.pdf"))
    for point in (
        "43.09742, -0.05828",   # a visit's own coordinate (the sanctuary)
        "42.87220, -0.00330",   # a drive's junction, on its VIA row
        "43.09680, -0.05750",   # the night's stay, in the bottom bar
    ):
        assert point in ink
        assert point not in plain
    # Nothing is clickable in that book — the point *is* the affordance.
    assert "(Navigate)" not in ink and "(Navigate)" in plain
