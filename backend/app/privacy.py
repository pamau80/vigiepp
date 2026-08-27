"""Privacidad: retención de evidencia, modo QR-only (Ley 21.719)."""

from __future__ import annotations

import json
import logging
import threading
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from .paths import data_dir

logger = logging.getLogger("vigiepp.privacy")

_lock = threading.Lock()
DEFAULT: dict[str, Any] = {
    "qr_only_mode": False,
    "retention_days": 90,
    "updated_at": None,
}


def _config_path() -> Path:
    return data_dir() / "privacy.json"


def get_config() -> dict[str, Any]:
    path = _config_path()
    with _lock:
        if not path.exists():
            cfg = dict(DEFAULT)
        else:
            try:
                raw = json.loads(path.read_text(encoding="utf-8"))
                cfg = dict(DEFAULT)
                if isinstance(raw, dict):
                    cfg.update({k: raw[k] for k in DEFAULT if k in raw})
            except json.JSONDecodeError:
                cfg = dict(DEFAULT)
        cfg["retention_days"] = max(7, min(365, int(cfg.get("retention_days") or 90)))
        cfg["qr_only_mode"] = bool(cfg.get("qr_only_mode"))
        return cfg


def save_config(patch: dict[str, Any]) -> dict[str, Any]:
    cfg = get_config()
    if "qr_only_mode" in patch:
        cfg["qr_only_mode"] = bool(patch["qr_only_mode"])
    if "retention_days" in patch:
        cfg["retention_days"] = max(7, min(365, int(patch["retention_days"] or 90)))
    cfg["updated_at"] = datetime.now(UTC).isoformat()
    path = _config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with _lock:
        path.write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")
    apply_retention(cfg["retention_days"])
    return cfg


def qr_only_enabled() -> bool:
    return bool(get_config().get("qr_only_mode"))


def apply_retention(days: int | None = None) -> dict[str, Any]:
    days = max(7, min(365, int(days or get_config().get("retention_days") or 90)))
    cutoff = datetime.now(UTC) - timedelta(days=days)
    evidence_removed = 0
    scans_removed = 0

    from .evidence import evidence_dir

    ev_dir = evidence_dir()
    if ev_dir.is_dir():
        for p in ev_dir.glob("*.jpg"):
            try:
                mtime = datetime.fromtimestamp(p.stat().st_mtime, tz=UTC)
                if mtime < cutoff:
                    p.unlink(missing_ok=True)
                    evidence_removed += 1
            except OSError:
                pass

    from .scanlog import purge_older_than

    scans_removed = purge_older_than(cutoff)

    return {
        "retention_days": days,
        "cutoff": cutoff.isoformat(),
        "evidence_removed": evidence_removed,
        "scans_removed": scans_removed,
    }
