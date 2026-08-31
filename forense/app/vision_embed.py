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
_clip_tokenizer: Any = None
_clip_device = "cpu"


def clip_available() -> bool:
    try:
        import open_clip  # noqa: F401

        return True
    except ImportError:
        return False


def _ensure_clip() -> bool:
    global _clip_ready, _clip_model, _clip_preprocess, _clip_tokenizer, _clip_device
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
            _clip_tokenizer = open_clip.get_tokenizer("ViT-B-32")
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


def embed_text(text: str) -> tuple[list[float], str]:
    """Embedding CLIP de texto (título + descripción de situación)."""
    text = (text or "").strip()
    if not text:
        return [], "none"
    if _ensure_clip() and _clip_tokenizer is not None:
        try:
            import torch

            tokens = _clip_tokenizer([text[:500]]).to(_clip_device)
            with torch.no_grad():
                feats = _clip_model.encode_text(tokens)
                feats = feats / feats.norm(dim=-1, keepdim=True)
            return feats.cpu().numpy().flatten().tolist(), "clip_text"
        except Exception as exc:
            logger.warning("Fallo embedding texto CLIP: %s", exc)
    return _keyword_vector(text), "keywords"


def _keyword_vector(text: str) -> list[float]:
    """Fallback: bolsa de palabras normalizada para similitud léxica."""
    import re

    words = re.findall(r"[a-záéíóúñ0-9]+", text.lower())
    vocab = sorted(set(words))
    if not vocab:
        return []
    vec = [1.0 if w in words else 0.0 for w in vocab]
    norm = float(np.linalg.norm(vec))
    return [v / norm for v in vec] if norm > 0 else vec


def text_similarity(a: list[float], b: list[float]) -> float:
    return cosine_similarity(a, b)


def sample_video_signatures(video_path: str, *, max_frames: int = 12) -> list[list[float]]:
    """Muestrea frames del video para comparación visual."""
    import cv2

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        return []
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    if total <= 0:
        cap.release()
        return []
    indices = [int(i * (total - 1) / max(1, max_frames - 1)) for i in range(max_frames)]
    sigs: list[list[float]] = []
    for idx in indices:
        cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
        ok, frame = cap.read()
        if not ok or frame is None:
            continue
        vec, _ = embed_image_bgr(frame)
        if vec:
            sigs.append(vec)
    cap.release()
    return sigs


def max_visual_similarity(job_sigs: list[list[float]], entry_sigs: list[list[float]]) -> float:
    best = 0.0
    for js in job_sigs:
        for es in entry_sigs:
            best = max(best, cosine_similarity(js, es))
    return best


def cosine_similarity(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    va, vb = np.array(a, dtype=np.float32), np.array(b, dtype=np.float32)
    denom = float(np.linalg.norm(va) * np.linalg.norm(vb))
    if denom <= 1e-9:
        return 0.0
    return float(np.clip(np.dot(va, vb) / denom, 0.0, 1.0))
