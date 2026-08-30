"""Multi-sitio / multi-faena (tenant) con datos aislados por organización."""

from __future__ import annotations

import json
import re
import threading
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .paths import _bundle_data_root

_lock = threading.Lock()


def _sites_file() -> Path:
    return _bundle_data_root() / "sites.json"

DEFAULT_SITE = {
    "id": "default",
    "name": "Faena principal",
    "slug": "default",
    "active": True,
}


def _load() -> dict[str, Any]:
    path = _sites_file()
    if not path.exists():
        return {"sites": [dict(DEFAULT_SITE)], "active_site_id": "default", "updated_at": None}
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(raw, dict) and isinstance(raw.get("sites"), list):
            return raw
    except json.JSONDecodeError:
        pass
    return {"sites": [dict(DEFAULT_SITE)], "active_site_id": "default", "updated_at": None}


def _save(payload: dict[str, Any]) -> None:
    path = _sites_file()
    payload["updated_at"] = datetime.now(UTC).isoformat()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _slugify(name: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", (name or "").lower()).strip("-")
    return s[:40] or "site"


def list_sites() -> list[dict[str, Any]]:
    with _lock:
        return list(_load().get("sites") or [])


def get_active_site_id() -> str:
    with _lock:
        data = _load()
        active = str(data.get("active_site_id") or "default")
        sites = data.get("sites") or []
        if not any(s.get("id") == active for s in sites):
            return "default"
        return active


def set_active_site(site_id: str) -> dict[str, Any]:
    with _lock:
        data = _load()
        sites = data.get("sites") or []
        if not any(s.get("id") == site_id for s in sites):
            raise ValueError("Sitio no encontrado")
        data["active_site_id"] = site_id
        _save(data)
        site = next(s for s in sites if s.get("id") == site_id)
        return site


def site_data_dir(site_id: str | None = None) -> Path:
    sid = (site_id or get_active_site_id() or "default").strip()
    if sid == "default":
        root = _bundle_data_root()
        (root / "faces").mkdir(parents=True, exist_ok=True)
        return root
    root = _bundle_data_root() / "sites" / sid
    root.mkdir(parents=True, exist_ok=True)
    (root / "faces").mkdir(parents=True, exist_ok=True)
    return root


def create_site(name: str) -> dict[str, Any]:
    name = (name or "").strip()[:80] or "Nueva faena"
    slug = _slugify(name)
    with _lock:
        data = _load()
        sites: list[dict[str, Any]] = list(data.get("sites") or [])
        if any(s.get("slug") == slug for s in sites):
            slug = f"{slug}-{uuid.uuid4().hex[:4]}"
        site = {
            "id": uuid.uuid4().hex[:10],
            "name": name,
            "slug": slug,
            "active": True,
            "created_at": datetime.now(UTC).isoformat(),
        }
        sites.append(site)
        data["sites"] = sites
        _save(data)
        site_data_dir(site["id"])
        return site


def get_site(site_id: str) -> dict[str, Any] | None:
    for s in list_sites():
        if s.get("id") == site_id:
            return s
    return None
