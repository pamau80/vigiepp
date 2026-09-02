"""Tests cinemática."""

from __future__ import annotations

from forense.app.kinematics import compute_track_speeds, find_speed_violations
from forense.app.tracker import Track, TrackPoint


def test_speed_computation():
    tr = Track(1, "machinery", "forklift", [])
    tr.points = [
        TrackPoint(0.0, 0, 0, "forklift", 0.9),
        TrackPoint(1.0, 100, 0, "forklift", 0.9),
    ]
    speeds = compute_track_speeds([tr], meters_per_pixel=0.05)
    assert len(speeds) == 1
    assert speeds[0]["max_kmh"] > 0


def test_speed_violation():
    speeds = [{"track_id": 1, "kind": "machinery", "label": "forklift", "max_kmh": 25.0, "avg_kmh": 20.0}]
    v = find_speed_violations(speeds, max_machinery_kmh=15, max_person_kmh=8)
    assert len(v) == 1


def test_snapshot_track_speeds():
    from forense.app.kinematics import snapshot_proximity, snapshot_track_speeds

    p = Track(1, "person", "person", [TrackPoint(0.5, 0, 0, "person", 0.9), TrackPoint(1.0, 50, 0, "person", 0.9)])
    m = Track(2, "machinery", "truck", [TrackPoint(0.5, 200, 0, "truck", 0.9), TrackPoint(1.0, 200, 0, "truck", 0.9)])
    speeds = snapshot_track_speeds([p, m], 1.0, meters_per_pixel=0.05)
    assert any(s["track_id"] == 1 and s["speed_kmh"] > 0 for s in speeds)
    prox = snapshot_proximity([p, m], 1.0, meters_per_pixel=0.05, min_distance_m=5.0)
    assert len(prox) == 1
    assert prox[0]["distance_m"] > 0
