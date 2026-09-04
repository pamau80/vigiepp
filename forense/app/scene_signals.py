"""Señales de escena por visión clásica — complemento al detector YOLO."""

from __future__ import annotations

from typing import Any

import cv2
import numpy as np


def detect_fire_smoke(frame_bgr: np.ndarray) -> dict[str, Any]:
    """Heurística HSV para llamas (naranjo/rojo) y humo (gris de baja saturación)."""
    if frame_bgr is None or frame_bgr.size == 0:
        return {"fire": False, "smoke": False, "fire_ratio": 0.0, "smoke_ratio": 0.0}

    h, w = frame_bgr.shape[:2]
    small = cv2.resize(frame_bgr, (320, max(1, int(320 * h / max(w, 1)))))
    hsv = cv2.cvtColor(small, cv2.COLOR_BGR2HSV)

    m1 = cv2.inRange(hsv, (0, 120, 140), (18, 255, 255))
    m2 = cv2.inRange(hsv, (165, 120, 140), (180, 255, 255))
    fire_mask = cv2.bitwise_or(m1, m2)
    fire_ratio = float(np.count_nonzero(fire_mask)) / fire_mask.size

    s = hsv[:, :, 1]
    v = hsv[:, :, 2]
    smoke_mask = ((s < 55) & (v > 95) & (v < 220)).astype(np.uint8) * 255
    smoke_ratio = float(np.count_nonzero(smoke_mask)) / smoke_mask.size

    fire = fire_ratio >= 0.012
    smoke = smoke_ratio >= 0.08 and not fire
    return {
        "fire": fire,
        "smoke": smoke,
        "fire_ratio": round(fire_ratio, 5),
        "smoke_ratio": round(smoke_ratio, 5),
    }


def fire_smoke_events(
    time_sec: float,
    time_label: str,
    signal: dict[str, Any],
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    if signal.get("fire"):
        out.append(
            {
                "time_sec": time_sec,
                "time_label": time_label,
                "type": "fire",
                "severity": "critical",
                "message": "Llamas o fuego visible en escena",
                "source": "scene_cv",
            }
        )
    elif signal.get("smoke"):
        out.append(
            {
                "time_sec": time_sec,
                "time_label": time_label,
                "type": "smoke",
                "severity": "high",
                "message": "Humo denso visible en escena",
                "source": "scene_cv",
            }
        )
    return out
