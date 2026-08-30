"""Workflow local de incidentes EHS — estados abierto / cerrado / verificado."""

from __future__ import annotations

import json
import threading
import uuid
from datetime import UTC, datetime
from typing import Any

from .paths import data_dir

_lock = threading.Lock()
_FILE = "ehs_incidents.json"
_VALID_STATES = frozenset({"open", "closed", "verified"})
_MAX_INCIDENTS = 500


def _path():
    return data_dir() / _FILE


def _load() -> list[dict[str, Any]]:
    path = _path()
    if not path.is_file():
        return []
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(raw, list):
            return raw
    except (json.JSONDecodeError, OSError):
        pass
    return []


def _save(items: list[dict[str, Any]]) -> None:
    path = _path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(items[-_MAX_INCIDENTS:], ensure_ascii=False, indent=2), encoding="utf-8")


def _now() -> str:
    return datetime.now(UTC).isoformat()


def create_incident(payload: dict[str, Any], *, source: str = "manual") -> dict[str, Any]:
    now = _now()
    incident = {
        "id": uuid.uuid4().hex[:12],
        "status": "open",
        "source": source,
        "created_at": now,
        "updated_at": now,
        "closed_at": None,
        "verified_at": None,
        "worker_name": payload.get("worker_name") or "—",
        "worker_rut": payload.get("worker_rut") or "",
        "worker_id": payload.get("worker_id") or "",
        "profile": payload.get("profile") or "general",
        "compliant": bool(payload.get("compliant")),
        "summary": (payload.get("summary") or "").strip() or "Incidente EPP",
        "missing": list(payload.get("missing") or []),
        "site": payload.get("site") or "",
        "evidence_id": payload.get("evidence_id"),
        "push_results": payload.get("push_results"),
        "note": (payload.get("note") or "").strip(),
    }
    with _lock:
        items = _load()
        items.append(incident)
        _save(items)
    return incident


def list_incidents(*, status: str | None = None, limit: int = 100) -> list[dict[str, Any]]:
    limit = max(1, min(500, int(limit)))
    with _lock:
        items = _load()
    if status:
        st = status.strip().lower()
        if st in _VALID_STATES:
            items = [i for i in items if i.get("status") == st]
    return list(reversed(items[-limit:]))


def get_incident(incident_id: str) -> dict[str, Any] | None:
    with _lock:
        for item in reversed(_load()):
            if item.get("id") == incident_id:
                return dict(item)
    return None


def update_incident_status(incident_id: str, status: str, *, note: str = "") -> dict[str, Any]:
    st = (status or "").strip().lower()
    if st not in _VALID_STATES:
        raise ValueError(f"Estado inválido: {status}")
    now = _now()
    with _lock:
        items = _load()
        for item in items:
            if item.get("id") != incident_id:
                continue
            item["status"] = st
            item["updated_at"] = now
            if note:
                item["note"] = note.strip()
            if st == "closed" and not item.get("closed_at"):
                item["closed_at"] = now
            if st == "verified":
                item["verified_at"] = now
                if not item.get("closed_at"):
                    item["closed_at"] = now
            _save(items)
            return dict(item)
    raise KeyError("Incidente no encontrado")
