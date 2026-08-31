"""Embeddings visuales CLIP para biblioteca Forense (con fallback histograma)."""

from __future__ import annotations

import logging
import threading
from typing import Any

import cv2
import numpy as np

logger = logging.getLogger("vigiepp.forense.vision_embed")

_clip_lock = threading.Lock()
_clip_ready = False
_clip_model: Any = None
_clip_preprocess: Any = None
_clip_device = "cpu"


def clip_available() -> bool:
    try:
        import open_clip  # noqa: F401

        return True
    except ImportError:
        return False


def _ensure_clip() -> bool:
    global _clip_ready, _clip_model, _clip_preprocess, _clip_device
    if _clip_ready:
        return _clip_model is not None
    with _clip_lock:
        if _clip_ready:
            return _clip_model is not None
        try:
            import open_clip
            import torch

            _clip_device = "cuda" if torch.cuda.is_available() else "cpu"
            model, _, preprocess = open_clip.create_model_and_transforms(
                "ViT-B-32",
                pretrained="openai",
                device=_clip_device,
            )
            model.eval()
            _clip_model = model
            _clip_preprocess = preprocess
            _clip_ready = True
            logger.info("CLIP ViT-B-32 cargado en %s para biblioteca Forense", _clip_device)
            return True
        except Exception as exc:
            logger.warning("CLIP no disponible, usando histograma: %s", exc)
            _clip_ready = True
            return False


def histogram_signature(image_bgr: np.ndarray) -> list[float]:
    hsv = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2HSV)
    hist = cv2.calcHist([hsv], [0, 1], None, [16, 16], [0, 180, 0, 256])
    cv2.normalize(hist, hist)
    return hist.flatten().tolist()


def embed_image_bgr(image_bgr: np.ndarray) -> tuple[list[float], str]:
    """Retorna (vector, backend) donde backend es 'clip' o 'histogram'."""
    if _ensure_clip():
        try:
            import torch
            from PIL import Image

            rgb = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)
            pil = Image.fromarray(rgb)
            tensor = _clip_preprocess(pil).unsqueeze(0).to(_clip_device)
            with torch.no_grad():
                feats = _clip_model.encode_image(tensor)
                feats = feats / feats.norm(dim=-1, keepdim=True)
            vec = feats.cpu().numpy().flatten().tolist()
            return vec, "clip"
        except Exception as exc:
            logger.warning("Fallo embedding CLIP: %s", exc)
    return histogram_signature(image_bgr), "histogram"


def cosine_similarity(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    va, vb = np.array(a, dtype=np.float32), np.array(b, dtype=np.float32)
    denom = float(np.linalg.norm(va) * np.linalg.norm(vb))
    if denom <= 1e-9:
        return 0.0
    return float(np.clip(np.dot(va, vb) / denom, 0.0, 1.0))
