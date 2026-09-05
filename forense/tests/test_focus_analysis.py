"""Tests re-análisis por ventana de enfoque."""

from __future__ import annotations

import cv2
import numpy as np

from forense.app.focus_analysis import merge_focus_keyframes, merge_focus_timeline
from forense.app.sampler import sample_window_frames


def test_merge_focus_timeline_replaces_window_per_camera():
    existing = [
        {"time_sec": 5.0, "message": "cam1 old", "camera": "Cám. 1"},
        {"time_sec": 5.0, "message": "cam2 keep", "camera": "Cám. 2"},
    ]
    new_events = [{"time_sec": 5.5, "message": "cam1 new", "camera": "Cám. 1"}]
    merged = merge_focus_timeline(
        existing, new_events, from_sec=4.0, until_sec=6.0, camera_label="Cám. 1"
    )
    msgs = [e["message"] for e in merged]
    assert msgs == ["cam2 keep", "cam1 new"]


def test_merge_focus_timeline_replaces_window():
    existing = [
        {"time_sec": 1.0, "message": "a"},
        {"time_sec": 5.0, "message": "old"},
        {"time_sec": 10.0, "message": "b"},
    ]
    new_events = [{"time_sec": 5.5, "message": "new"}]
    merged = merge_focus_timeline(existing, new_events, from_sec=4.0, until_sec=6.0)
    msgs = [e["message"] for e in merged]
    assert msgs == ["a", "new", "b"]


def test_merge_focus_keyframes_replaces_window():
    existing = [
        {"time_sec": 2.0, "image": "kf_000.jpg"},
        {"time_sec": 8.0, "image": "kf_001.jpg"},
    ]
    new_items = [{"time_sec": 8.2, "image": "kf_002.jpg"}]
    merged = merge_focus_keyframes(existing, new_items, from_sec=7.0, until_sec=9.0)
    assert len(merged) == 2
    assert merged[1]["image"] == "kf_002.jpg"


def test_sample_window_frames(tmp_path):
    path = tmp_path / "win.mp4"
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    w = cv2.VideoWriter(str(path), fourcc, 10.0, (64, 64))
    for _ in range(40):
        w.write(np.full((64, 64, 3), 200, dtype=np.uint8))
    w.release()
    frames = sample_window_frames(str(path), focus_from_sec=1.0, focus_until_sec=2.0, interval_sec=0.25)
    assert len(frames) >= 3
    assert all(1.0 <= f.time_sec <= 2.0 for f in frames)
