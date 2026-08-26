"""Inferencia combinada EPP + identidad en un mismo frame."""

from __future__ import annotations

import os
from typing import Any

import numpy as np

from . import paths as paths_mod
from .detector import PPEDetector
from .identity import IdentityRegistry, IdentityService


def combined_inference_enabled() -> bool:
    raw = os.getenv("VIGIEPP_COMBINED_INFERENCE", "auto").strip().lower()
    if raw in ("0", "false", "no", "off"):
        return False
    if raw in ("1", "true", "yes", "on"):
        return True
    # auto: edge con volumen persistente (faena)
    return paths_mod.is_persistent()


def analyze_frame(
    frame: np.ndarray,
    *,
    conf: float = 0.35,
    imgsz: int = 256,
    threshold: float = 0.33,
    identify: bool = False,
    annotate: bool = False,
) -> tuple[list, np.ndarray, dict[str, Any] | None]:
    """EPP + identidad opcional en el mismo frame (secuencial, un solo lock externo)."""
    identity: dict[str, Any] | None = None
    detections: list = []
    annotated = frame

    run_both = identify and combined_inference_enabled()
    run_id_only = identify and not combined_inference_enabled()

    if run_id_only or run_both:
        reg = IdentityRegistry.peek()
        if reg is None:
            IdentityRegistry.get()
            identity = {
                "known": False,
                "booting": True,
                "name": None,
                "rut": None,
                "method": None,
                "faces_detected": 0,
                "reject_reason": "identity_loading",
            }
        else:
            thr = max(0.25, min(0.7, float(threshold or 0.33)))
            try:
                result = IdentityService().identify(frame, threshold=thr)
                identity = {
                    "known": bool(result.get("identified")),
                    "id": (result.get("identified") or {}).get("id"),
                    "name": (result.get("identified") or {}).get("name"),
                    "rut": (result.get("identified") or {}).get("rut"),
                    "score": (result.get("matches") or [{}])[0].get("score"),
                    "method": "face",
                    "faces_detected": result.get("faces_detected") or 0,
                    "face_box": (result.get("matches") or [{}])[0].get("box"),
                }
            except Exception:  # noqa: BLE001
                identity = {"known": False, "faces_detected": 0, "reject_reason": "identity_error"}

    if not identify or run_both:
        det = PPEDetector.peek() or PPEDetector.get()
        if not det.ready:
            if run_id_only:
                return detections, annotated, identity
            raise RuntimeError("Modelo EPP cargando")
        imgsz_use = max(224, min(int(imgsz or 256), 512))
        detections, annotated = det.predict(frame, conf=conf, imgsz=imgsz_use, annotate=annotate)

    return detections, annotated, identity
