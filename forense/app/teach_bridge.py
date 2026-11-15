"""Puente Forense ↔ Teach (YOLO personalizado de la faena)."""

from __future__ import annotations

import logging
from typing import Any

import cv2

logger = logging.getLogger("vigiepp.forense.teach_bridge")

VIGIEPP_TEACH_URL = "http://127.0.0.1:8000/#teach"


def teach_status() -> dict[str, Any]:
    from app.detector import PPEDetector
    from app.paths import custom_weights_path
    from app.teach import TeachStore

    weights = custom_weights_path()
    det = PPEDetector.peek()
    if det is None:
        try:
            det = PPEDetector.get()
        except Exception:
            det = None

    stats = TeachStore.get().stats()
    training = stats.get("training") or {}
    return {
        "custom_weights_exist": weights.is_file(),
        "custom_weights_path": str(weights) if weights.is_file() else None,
        "custom_active": bool(det and det.using_custom),
        "model_name": det.model_name if det and det.ready else "Modelo base",
        "detector_ready": bool(det and det.ready),
        "total_samples": stats.get("total_samples", 0),
        "ready_to_train": stats.get("ready_to_train", False),
        "training_running": training.get("running", False),
        "custom_model_ready": training.get("custom_model_ready", False),
        "per_class": stats.get("per_class") or {},
        "min_recommended": stats.get("min_recommended", 30),
        "teach_classes": TeachStore.get().list_classes(),
        "vigiepp_teach_url": VIGIEPP_TEACH_URL,
    }


def activate_custom_model() -> dict[str, Any]:
    from app.detector import PPEDetector

    result = PPEDetector.get().load_custom_model()
    if not result.get("ok"):
        return result
    return {
        **result,
        "message": "Modelo personalizado Teach activo para análisis Forense.",
    }


def ensure_custom_model_if_available() -> dict[str, Any]:
    """Carga pesos Teach al arrancar Forense si existen."""
    from app.paths import custom_weights_path

    path = custom_weights_path()
    if not path.is_file():
        return {"ok": False, "reason": "no_custom_weights"}
    try:
        return activate_custom_model()
    except Exception as exc:
        logger.warning("No se pudo activar modelo Teach: %s", exc)
        return {"ok": False, "error": str(exc)}


def promote_keyframe_to_teach(
    job_id: str,
    keyframe_name: str,
    class_id: str,
) -> dict[str, Any]:
    from app.teach import TeachStore

    from .jobs import keyframe_path

    path = keyframe_path(job_id, keyframe_name)
    if not path or not path.is_file():
        return {"ok": False, "error": "Captura no encontrada"}
    img = cv2.imread(str(path))
    if img is None:
        return {"ok": False, "error": "No se pudo leer la imagen"}
    result = TeachStore.get().add_sample(img, class_id=class_id)
    if result.get("ok"):
        result["message"] = (
            f"Captura enviada a Teach ({class_id}). "
            f"Total clase: {result.get('count')}. Entrená en VigiEPP → modo Teach."
        )
    return result


def start_training(epochs: int = 40) -> dict[str, Any]:
    from app.teach import TeachStore

    return TeachStore.get().start_training(epochs=epochs)
