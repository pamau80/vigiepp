"""Utilidades de fixtures faciales para tests (sin dependencia de Playwright)."""

from __future__ import annotations

import urllib.request
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
LENA = ROOT / "tests" / "fixtures" / "lena.jpg"
LENA_URL = "https://raw.githubusercontent.com/opencv/opencv/4.x/samples/data/lena.jpg"


def ensure_lena() -> Path:
    LENA.parent.mkdir(parents=True, exist_ok=True)
    if not LENA.exists() or LENA.stat().st_size < 1000:
        urllib.request.urlretrieve(LENA_URL, LENA)
    return LENA


def face_jpeg_variants(face_path: Path, count: int = 4) -> list[bytes]:
    img = cv2.imread(str(face_path))
    if img is None:
        raise RuntimeError(f"No se pudo leer {face_path}")
    out: list[bytes] = []
    h, w = img.shape[:2]
    cx, cy = w / 2, h / 2

    def rot(m: np.ndarray, deg: float) -> np.ndarray:
        return cv2.warpAffine(
            m,
            cv2.getRotationMatrix2D((cx, cy), deg, 1.0),
            (w, h),
        )

    ops = [
        lambda m: m,
        lambda m: cv2.flip(m, 1),
        lambda m: rot(m, 14),
        lambda m: rot(m, -11),
        lambda m: rot(m, 22),
        lambda m: cv2.convertScaleAbs(m, alpha=1.12, beta=18),
        lambda m: cv2.convertScaleAbs(rot(m, 8), alpha=0.92, beta=-8),
        lambda m: cv2.warpAffine(
            m,
            np.float32([[1, 0, 12], [0, 1, -8]]),
            (w, h),
        ),
    ]
    for i in range(count):
        variant = ops[i % len(ops)](img.copy())
        ok, buf = cv2.imencode(".jpg", variant, [int(cv2.IMWRITE_JPEG_QUALITY), 92])
        if not ok:
            raise RuntimeError("imencode falló")
        out.append(buf.tobytes())
    return out
