"""Bitácora de acciones administrativas (JSONL)."""

from __future__ import annotations

import json
import threading
from contextvars import ContextVar
from datetime import datetime, timezone
from typing import Any

from .paths import data_dir

_lock = threading.Lock()
_audit_actor: ContextVar[str] = ContextVar("audit_actor", default="system")


def set_actor(actor: str) -> None:
    _audit_actor.set((actor or "system")[:64])


def current_actor() -> str:
    return _audit_actor.get()


def _audit_file() -> Any:
    return data_dir() / "audit.jsonl"


def log(action: str, *, actor: str | None = None, detail: str = "", extra: dict[str, Any] | None = None) -> None:
    who = (actor or current_actor() or "system")[:64]
    row = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "action": action,
        "actor": who,
        "detail": (detail or "")[:400],
        **(extra or {}),
    }
    line = json.dumps(row, ensure_ascii=False) + "\n"
    path = _audit_file()
    with _lock:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as fh:
            fh.write(line)
    try:
        from . import cloud_persist as cloud_mod

        cloud_mod.schedule_push(8.0)
    except Exception:  # noqa: BLE001
        pass


def recent(limit: int = 80) -> list[dict[str, Any]]:
    path = _audit_file()
    if not path.exists():
        return []
    n = max(1, min(500, int(limit or 80)))
    with _lock:
        lines = path.read_text(encoding="utf-8").splitlines()
    out: list[dict[str, Any]] = []
    for line in lines[-n:]:
        try:
            item = json.loads(line)
            if isinstance(item, dict):
                out.append(item)
        except json.JSONDecodeError:
            continue
    out.reverse()
    return out
