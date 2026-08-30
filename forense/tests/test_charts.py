"""Tests series de velocidad."""

from __future__ import annotations

from forense.app.charts import build_speed_series
from forense.app.tracker import Track, TrackPoint


def test_build_speed_series():
    tr = Track(1, "machinery", "forklift", [])
    tr.points = [
        TrackPoint(0.0, 0, 0, "forklift", 0.9),
        TrackPoint(1.0, 80, 0, "forklift", 0.9),
    ]
    series = build_speed_series([tr], meters_per_pixel=0.05)
    assert len(series) == 1
    assert series[0]["track_id"] == 1
    assert series[0]["max_kmh"] > 0
    assert len(series[0]["points"]) == 1
