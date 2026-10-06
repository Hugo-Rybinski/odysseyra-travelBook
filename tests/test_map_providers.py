"""``maps_url`` per provider — the PDF's (Navigate) links. Mirrored by the
viewer's ``navUrl`` in ``web/src/render/nav.ts``; keep the two in step."""

import pytest

from odysseyra_travelbook.models import MAP_PROVIDERS, Coordinate
from odysseyra_travelbook.models.geo import maps_url

POINT = Coordinate(lat=42.87, long=74.59)


@pytest.mark.parametrize("provider", MAP_PROVIDERS)
def test_every_provider_links_a_point_and_a_name(provider):
    assert maps_url(POINT, provider=provider)
    assert maps_url(None, "Bishkek", provider=provider)
    assert maps_url(None, "", "  ", provider=provider) == ""


def test_yandex_takes_long_then_lat():
    url = maps_url(POINT, provider="yandex")
    assert url == "https://yandex.com/maps/?ll=74.59,42.87&pt=74.59,42.87&z=16"


def test_yandex_searches_a_name():
    assert maps_url(None, "Ala-Archa", provider="yandex") == "https://yandex.com/maps/?text=Ala-Archa"
