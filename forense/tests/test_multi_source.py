"""Tests fusión multi-cámara."""

from __future__ import annotations

from forense.app.multi_source import merge_analyses


def test_merge_analyses():
    parts = [
        {
            "timeline": [{"time_sec": 2, "type": "action"}],
            "keyframes": [{"time_sec": 2}],
            "kinematics": {"track_speeds": [{"track_id": 1}], "speed_violations": [], "proximity_events": []},
            "speed_series": [{"track_id": 1, "points": []}],
            "tracks": [{"track_id": 1}],
            "heatmap": True,
            "frame_size": {"w": 640, "h": 480},
        },
        {
            "timeline": [{"time_sec": 1, "type": "zone"}],
            "keyframes": [],
            "kinematics": {"track_speeds": [{"track_id": 2}], "speed_violations": [{"x": 1}], "proximity_events": []},
            "speed_series": [],
            "tracks": [],
            "heatmap": False,
            "frame_size": {"w": 800, "h": 600},
        },
    ]
    merged = merge_analyses(parts)
    assert merged["event_count"] == 2
    assert merged["sources_count"] == 2
    assert merged["frame_size"]["w"] == 800
    assert len(merged["kinematics"]["track_speeds"]) == 2
    assert merged["timeline"][0]["time_sec"] == 1
