"""Zonas por fuente (cámara NVR)."""

from __future__ import annotations

import pytest

from app import zones as zones_mod


@pytest.fixture(autouse=True)
def isolated_zones(tmp_path, monkeypatch):
    monkeypatch.setenv("VIGIEPP_DATA_DIR", str(tmp_path))
    zones_mod.ZONES_FILE = tmp_path / "zones.json"
    zones_mod.DATA_DIR = tmp_path
    zones_mod._ensure()
    yield


def test_zones_for_source_fallback_global():
    global_zones = zones_mod.get_zones()["zones"]
    assert zones_mod.zones_for_source("live") == [z for z in global_zones if z.get("enabled", True)]


def test_zones_by_source_override():
    custom = [
        {
            "id": "nvr-z1",
            "name": "Pasillo NVR",
            "type": "vehicle_lane",
            "enabled": True,
            "x": 0.1,
            "y": 0.1,
            "w": 0.3,
            "h": 0.4,
            "color": "#d62828",
        }
    ]
    zones_mod.save_zones(custom, source_id="watchlist:cam-a")
    live = zones_mod.zones_for_source("live")
    nvr = zones_mod.zones_for_source("watchlist:cam-a")
    assert len(live) >= 1
    assert len(nvr) == 1
    assert nvr[0]["id"] == "nvr-z1"


def test_evaluate_zones_respects_source():
    zones_mod.save_zones([])
    custom = [
        {
            "id": "solo-nvr",
            "name": "Zona NVR",
            "type": "restricted",
            "enabled": True,
            "x": 0.0,
            "y": 0.0,
            "w": 0.5,
            "h": 0.5,
            "color": "#e85d04",
        }
    ]
    zones_mod.save_zones(custom, source_id="watchlist:x")
    person = {"label": "Person", "box": [10, 10, 200, 400], "confidence": 0.9}
    live_out = zones_mod.evaluate_zones([person], 640, 480, source_id="live")
    nvr_out = zones_mod.evaluate_zones([person], 640, 480, source_id="watchlist:x")
    assert not live_out["hits"]
    assert len(nvr_out["hits"]) == 1
