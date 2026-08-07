"""Evidencia fotográfica de incumplimientos."""

from __future__ import annotations

import re
import uuid
from pathlib import Path

from .paths import data_dir

_SAFE = re.compile(r"[^a-zA-Z0-9._-]+")


def evidence_dir() -> Path:
    path = data_dir() / "evidence"
    path.mkdir(parents=True, exist_ok=True)
    return path


def save_evidence_jpeg(jpeg: bytes, *, prefix: str = "ev") -> str | None:
    if not jpeg:
        return None
    eid = f"{prefix}-{uuid.uuid4().hex[:12]}"
    path = evidence_dir() / f"{eid}.jpg"
    path.write_bytes(jpeg)
    return eid


def evidence_path(evidence_id: str) -> Path | None:
    eid = _SAFE.sub("", (evidence_id or "").strip())
    if not eid or ".." in eid:
        return None
    path = evidence_dir() / f"{eid}.jpg"
    if not path.exists() or not path.is_file():
        return None
    return path
