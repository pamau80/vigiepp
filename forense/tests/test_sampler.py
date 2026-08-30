"""Tests muestreo adaptivo."""

from __future__ import annotations

import cv2
import numpy as np
import pytest

from forense.app.sampler import adaptive_sample_video


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
