"""Tests muestreo adaptivo."""

from __future__ import annotations

import cv2
import numpy as np

from forense.app.sampler import adaptive_sample_video, enrich_focus_window


def test_sampler_on_synthetic_video(tmp_path):
    path = tmp_path / "test.mp4"
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    w = cv2.VideoWriter(str(path), fourcc, 10.0, (64, 64))
    for i in range(30):
        frame = np.zeros((64, 64, 3), dtype=np.uint8)
        frame[:, :] = (i * 8, 0, 0)
        w.write(frame)
    w.release()

    samples, meta = adaptive_sample_video(str(path), base_interval_sec=0.2, max_frames=50)
    assert len(samples) >= 3
    assert meta["total_frames"] == 30
    assert meta["sampled_frames"] == len(samples)


def test_enrich_focus_window(tmp_path):
    path = tmp_path / "focus.mp4"
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    w = cv2.VideoWriter(str(path), fourcc, 10.0, (64, 64))
    for _ in range(50):
        w.write(np.full((64, 64, 3), 128, dtype=np.uint8))
    w.release()
    base, _ = adaptive_sample_video(str(path), base_interval_sec=1.0, max_frames=20)
    merged = enrich_focus_window(base, str(path), focus_from_sec=2.0, focus_until_sec=3.0, interval_sec=0.25)
    assert len(merged) >= len(base)
    assert any(2.0 <= s.time_sec <= 3.0 for s in merged)
