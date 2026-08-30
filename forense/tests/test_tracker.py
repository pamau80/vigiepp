"""Tests tracker IoU."""

from __future__ import annotations

from forense.app.tracker import IoUTracker, _classify


def test_classify_person_and_machinery():
    assert _classify("person") == "person"
    assert _classify("forklift") == "machinery"
    assert _classify("casco") == "other"


def test_tracker_assigns_ids():
    tr = IoUTracker()
    dets = [{"label": "person", "box": [10, 10, 50, 90], "confidence": 0.9}]
    tracks = tr.update(0.0, dets)
    assert len(tracks) == 1
    dets2 = [{"label": "person", "box": [12, 12, 52, 92], "confidence": 0.88}]
    tr.update(0.5, dets2)
    assert len(tr.all_tracks()) == 1
    assert len(tr.all_tracks()[0].points) == 2
