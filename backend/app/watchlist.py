"""Lista de vigilancia masiva — hasta 16 canales RTSP (NVR/DVR/cámaras IP)."""

from __future__ import annotations

import json
import threading
import uuid
from datetime import datetime, timezone
from typing import Any

from .cameras import validate_rtsp
from .paths import data_dir

_lock = threading.Lock()
WATCH_FILE = data_dir() / "watchlist.json"
MAX_WATCH = 16


def refresh_paths() -> None:
    global WATCH_FILE
    WATCH_FILE = data_dir() / "watchlist.json"


def _load() -> dict[str, Any]:
    if not WATCH_FILE.exists():
        return {"channels": [], "updated_at": None}
    try:
        raw = json.loads(WATCH_FILE.read_text(encoding="utf-8"))
        if isinstance(raw, dict) and isinstance(raw.get("channels"), list):
            return raw
    except json.JSONDecodeError:
        pass
    return {"channels": [], "updated_at": None}


def _save(payload: dict[str, Any]) -> None:
    payload["updated_at"] = datetime.now(timezone.utc).isoformat()
    WATCH_FILE.parent.mkdir(parents=True, exist_ok=True)
    WATCH_FILE.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    try:
        from . import cloud_persist as cloud_mod

        cloud_mod.schedule_push()
    except Exception:  # noqa: BLE001
        pass


def list_channels() -> list[dict[str, Any]]:
    with _lock:
        return list(_load().get("channels") or [])


def upsert(
    name: str,
    url: str,
    *,
    channel_id: str | None = None,
    vendor: str = "",
    nvr_id: str = "",
    channel_num: int | None = None,
    enabled: bool = True,
) -> dict[str, Any]:
    url = validate_rtsp(url)
    name = (name or "").strip()[:60] or "Canal"
    with _lock:
        data = _load()
        channels: list[dict[str, Any]] = list(data.get("channels") or [])
        if channel_id:
            for ch in channels:
                if ch.get("id") == channel_id:
                    ch["name"] = name
                    ch["url"] = url
                    ch["vendor"] = vendor or ch.get("vendor") or ""
                    ch["nvr_id"] = nvr_id or ch.get("nvr_id") or ""
                    if channel_num is not None:
                        ch["channel"] = channel_num
                    ch["enabled"] = enabled
                    _save({"channels": channels})
                    return ch
        if len(channels) >= MAX_WATCH:
            raise ValueError(f"Máximo {MAX_WATCH} canales en vigilancia masiva.")
        ch = {
            "id": uuid.uuid4().hex[:10],
            "name": name,
            "url": url,
            "vendor": vendor or "",
            "nvr_id": nvr_id or "",
            "channel": channel_num,
            "enabled": enabled,
        }
        channels.append(ch)
        _save({"channels": channels})
        return ch


def import_channels(entries: list[dict[str, Any]], *, replace: bool = False) -> list[dict[str, Any]]:
    with _lock:
        data = _load()
        current: list[dict[str, Any]] = [] if replace else list(data.get("channels") or [])
        for item in entries:
            if len(current) >= MAX_WATCH:
                break
            url = validate_rtsp(str(item.get("url") or ""))
            name = str(item.get("name") or "Canal").strip()[:60]
            current.append(
                {
                    "id": uuid.uuid4().hex[:10],
                    "name": name,
                    "url": url,
                    "vendor": str(item.get("vendor") or ""),
                    "nvr_id": str(item.get("nvr_id") or ""),
                    "channel": item.get("channel"),
                    "enabled": bool(item.get("enabled", True)),
                }
            )
        _save({"channels": current})
        return current


def delete(channel_id: str) -> bool:
    with _lock:
        data = _load()
        channels = [c for c in (data.get("channels") or []) if c.get("id") != channel_id]
        if len(channels) == len(data.get("channels") or []):
            return False
        _save({"channels": channels})
        return True


def set_enabled(channel_id: str, enabled: bool) -> bool:
    with _lock:
        data = _load()
        for ch in data.get("channels") or []:
            if ch.get("id") == channel_id:
                ch["enabled"] = enabled
                _save(data)
                return True
        return False
