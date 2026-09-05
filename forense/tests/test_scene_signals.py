"""Tests señales de escena y timeline de visión."""

from __future__ import annotations

import numpy as np

from forense.app.scene_signals import detect_fire_smoke, fire_smoke_events
from forense.app.vision_timeline import events_from_vision_parsed, merge_vision_timeline


def test_detect_fire_on_orange_frame():
    frame = np.zeros((120, 160, 3), dtype=np.uint8)
    frame[40:90, 50:110] = (30, 60, 255)
    sig = detect_fire_smoke(frame)
    assert sig["fire"] is True
    ev = fire_smoke_events(12.0, "00:00:12", sig)
    assert ev and ev[0]["type"] == "fire"


def test_vision_parsed_legacy_and_general():
    parsed = {
        "fuego_contenedor": "Contenedor con llamas visibles",
        "epp_y_ropa": "Sin chaleco",
    }
    events = events_from_vision_parsed(parsed, frames_used=[{"time_sec": 5.0, "time_label": "00:00:05"}])
    types = {e["type"] for e in events}
    assert "fire" in types
    assert "epp_non_compliant" in types


def test_merge_vision_timeline_dedupes():
    base = [{"time_sec": 1.0, "type": "proximity", "message": "x"}]
    extra = [{"time_sec": 2.0, "type": "zone", "message": "y"}]
    merged = merge_vision_timeline(base, extra)
    assert len(merged) == 2
