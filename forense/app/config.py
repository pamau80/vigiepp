"""Configuración aislada de VigiEPP Forense."""

from __future__ import annotations

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FORENSE_DATA = Path(os.getenv("VIGIEPP_FORENSE_DATA_DIR", str(ROOT / "forense" / "data")))
JOBS_DIR = FORENSE_DATA / "jobs"
KNOWLEDGE_DIR = FORENSE_DATA / "knowledge"
WEB_DIR = ROOT / "forense" / "web"
BUILD = "forense-p5"
DEFAULT_PROFILE = os.getenv("VIGIEPP_FORENSE_PROFILE", "epp_completo")
DEFAULT_MAX_MACHINERY_KMH = float(os.getenv("VIGIEPP_FORENSE_MAX_MACHINERY_KMH", "15"))
DEFAULT_MAX_PERSON_KMH = float(os.getenv("VIGIEPP_FORENSE_MAX_PERSON_KMH", "8"))
DEFAULT_MIN_DISTANCE_M = float(os.getenv("VIGIEPP_FORENSE_MIN_DISTANCE_M", "2.0"))
MAX_UPLOAD_MB = int(os.getenv("VIGIEPP_FORENSE_MAX_MB", "512"))


def ensure_dirs() -> None:
    JOBS_DIR.mkdir(parents=True, exist_ok=True)
    KNOWLEDGE_DIR.mkdir(parents=True, exist_ok=True)
