"""Live, read-only tests against https://pindropped.app (GET only). Skip with PINDROPPED_OFFLINE=1."""
import os

import pytest

from pindropped_mcp import client as pd

pytestmark = pytest.mark.skipif(os.environ.get("PINDROPPED_OFFLINE") == "1", reason="offline")

CAPITOL_HILL = (38.889, -77.000)


def test_search_radius_live():
    pins = pd.search_pins(lat=CAPITOL_HILL[0], lng=CAPITOL_HILL[1], radius_m=3000)
    assert isinstance(pins, list)
    for p in pins:
        assert p["distance_m"] <= 3000
        assert p["url"] == f"https://pindropped.app/p/{p['id']}"
        assert p["category"] in pd.CATEGORIES
    assert [p["distance_m"] for p in pins] == sorted(p["distance_m"] for p in pins)


def test_search_bbox_and_category_live():
    pins = pd.search_pins(bbox="-77.2,38.8,-76.9,39.0", category="event")
    assert all(p["category"] == "event" for p in pins)


def test_get_pin_live():
    pins = pd.search_pins(bbox="-77.2,38.8,-76.9,39.0")
    if not pins:
        pytest.skip("no live pins right now")
    p = pd.get_pin(pins[0]["id"])
    assert p["id"] == pins[0]["id"]
    assert p["category_label"] == pd.CATEGORIES[p["category"]]


def test_get_pin_404_live():
    with pytest.raises(pd.PinDroppedError, match="404"):
        pd.get_pin("doesnotexist000")
