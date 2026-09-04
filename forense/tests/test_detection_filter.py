"""Tests filtro de detecciones."""

from __future__ import annotations

from forense.app.detection_filter import filter_detections, strict_inference_overrides


def test_filter_low_confidence():
    dets = [
        {"label": "Person", "box": [10, 10, 100, 200], "confidence": 0.9},
        {"label": "Person", "box": [200, 200, 240, 280], "confidence": 0.2},
    ]
    out = filter_detections(dets, 640, 480, min_confidence=0.42)
    assert len(out) == 1
    assert out[0]["confidence"] == 0.9


def test_filter_tiny_boxes():
    dets = [{"label": "Person", "box": [1, 1, 3, 3], "confidence": 0.95}]
    out = filter_detections(dets, 1920, 1080, min_area_ratio=0.001)
    assert out == []


def test_strict_overrides():
    o = strict_inference_overrides(True)
    assert o["min_detection_confidence"] >= 0.5
