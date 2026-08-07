"""Rutas de datos: volumen persistente vía VIGIEPP_DATA_DIR."""

from __future__ import annotations

import os
from pathlib import Path

_BUNDLE_DATA = Path(__file__).resolve().parents[1] / "data"


def data_dir() -> Path:
    """Datos mutables (workers, faces, zones, scans, notifs, teach)."""
    raw = os.getenv("VIGIEPP_DATA_DIR", "").strip()
    path = Path(raw) if raw else _BUNDLE_DATA
    path.mkdir(parents=True, exist_ok=True)
    (path / "faces").mkdir(parents=True, exist_ok=True)
    return path


def face_models_dir() -> Path:
    """ONNX YuNet/SFace: viven en la imagen, no en el volumen."""
    raw = os.getenv("VIGIEPP_MODELS_DIR", "").strip()
    path = Path(raw) if raw else (_BUNDLE_DATA / "models")
    path.mkdir(parents=True, exist_ok=True)
    return path


def teach_dataset_dir() -> Path:
    path = data_dir() / "datasets" / "custom_ppe"
    path.mkdir(parents=True, exist_ok=True)
    return path


def teach_runs_dir() -> Path:
    path = data_dir() / "runs" / "custom_ppe"
    path.mkdir(parents=True, exist_ok=True)
    return path


def custom_weights_path() -> Path:
    return teach_runs_dir() / "run" / "weights" / "best.pt"


def is_persistent() -> bool:
    return bool(os.getenv("VIGIEPP_DATA_DIR", "").strip())
