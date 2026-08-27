"""Registro de cámaras IP / NVR (hasta 4 streams RTSP)."""

from __future__ import annotations

import json
import threading
import uuid
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlparse

from .paths import data_dir

_lock = threading.Lock()
CAMERAS_FILE = data_dir() / "cameras.json"
MAX_CAMERAS = 4


def _load() -> dict[str, Any]:
    if not CAMERAS_FILE.exists():
        return {"cameras": [], "updated_at": None}
    try:
        raw = json.loads(CAMERAS_FILE.read_text(encoding="utf-8"))
        if isinstance(raw, dict) and isinstance(raw.get("cameras"), list):
            return raw
    except json.JSONDecodeError:
        pass
    return {"cameras": [], "updated_at": None}


def _save(payload: dict[str, Any]) -> None:
    payload["updated_at"] = datetime.now(timezone.utc).isoformat()
    CAMERAS_FILE.parent.mkdir(parents=True, exist_ok=True)
    CAMERAS_FILE.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    try:
        from . import cloud_persist as cloud_mod

        cloud_mod.schedule_push()
    except Exception:  # noqa: BLE001
        pass


from .rtsp_security import validate_rtsp_url as _validate_rtsp


def validate_rtsp(url: str) -> str:
    return _validate_rtsp(url)


def list_cameras() -> list[dict[str, Any]]:
    with _lock:
        return list(_load().get("cameras") or [])


def upsert(name: str, url: str, camera_id: str | None = None) -> dict[str, Any]:
    url = validate_rtsp(url)
    name = (name or "").strip()[:60] or f"Cámara {urlparse(url).hostname}"
    with _lock:
        data = _load()
        cams: list[dict[str, Any]] = list(data.get("cameras") or [])
        if camera_id:
            for cam in cams:
                if cam.get("id") == camera_id:
                    cam["name"] = name
                    cam["url"] = url
                    _save({"cameras": cams})
                    return cam
        if len(cams) >= MAX_CAMERAS:
            raise ValueError(f"Máximo {MAX_CAMERAS} cámaras. Eliminá una para agregar otra.")
        cam = {
            "id": uuid.uuid4().hex[:10],
            "name": name,
            "url": url,
            "enabled": True,
        }
        cams.append(cam)
        _save({"cameras": cams})
        return cam


def delete(camera_id: str) -> bool:
    with _lock:
        data = _load()
        cams = [c for c in (data.get("cameras") or []) if c.get("id") != camera_id]
        if len(cams) == len(data.get("cameras") or []):
            return False
        _save({"cameras": cams})
        return True
