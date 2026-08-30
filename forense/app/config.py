"""Configuración aislada de VigiEPP Forense."""

from __future__ import annotations

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FORENSE_DATA = Path(os.getenv("VIGIEPP_FORENSE_DATA_DIR", str(ROOT / "forense" / "data")))
JOBS_DIR = FORENSE_DATA / "jobs"
WEB_DIR = ROOT / "forense" / "web"
BUILD = "forense-p0"
DEFAULT_PROFILE = os.getenv("VIGIEPP_FORENSE_PROFILE", "epp_completo")
MAX_UPLOAD_MB = int(os.getenv("VIGIEPP_FORENSE_MAX_MB", "512"))


def ensure_dirs() -> None:
    JOBS_DIR.mkdir(parents=True, exist_ok=True)
