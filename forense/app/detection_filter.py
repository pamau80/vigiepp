"""Filtros para reducir falsos positivos del detector YOLO en Forense."""

from __future__ import annotations

from typing import Any


def filter_detections(
    detections: list[dict[str, Any]],
    frame_w: int,
    frame_h: int,
    *,
    min_confidence: float = 0.42,
    min_area_ratio: float = 0.0008,
) -> list[dict[str, Any]]:
    """Descarta detecciones de baja confianza o cajas demasiado pequeñas (ruido lejano)."""
    if not detections or frame_w <= 0 or frame_h <= 0:
        return detections
    frame_area = float(frame_w * frame_h)
    min_area = frame_area * min_area_ratio
    out: list[dict[str, Any]] = []
    for det in detections:
        conf = float(det.get("confidence") or 0)
        if conf < min_confidence:
            continue
        box = det.get("box")
        if not box or len(box) != 4:
            continue
        x1, y1, x2, y2 = (float(v) for v in box)
        w = max(0.0, x2 - x1)
        h = max(0.0, y2 - y1)
        if w * h < min_area:
            continue
        out.append(det)
    return out


def strict_inference_overrides(enabled: bool) -> dict[str, float]:
    if not enabled:
        return {}
    return {
        "min_detection_confidence": 0.52,
        "min_box_area_ratio": 0.0012,
    }
