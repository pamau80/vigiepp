"""Bitácora de acciones administrativas (JSONL)."""

from __future__ import annotations

import json
import threading
from datetime import datetime, timezone
from typing import Any

from .paths import data_dir

_lock = threading.Lock()
AUDIT_FILE = data_dir() / "audit.jsonl"


def log(action: str, *, actor: str = "admin", detail: str = "", extra: dict[str, Any] | None = None) -> None:
    row = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "action": action,
        "actor": actor,
        "detail": (detail or "")[:400],
        **(extra or {}),
    }
    line = json.dumps(row, ensure_ascii=False) + "\n"
    with _lock:
        AUDIT_FILE.parent.mkdir(parents=True, exist_ok=True)
        with AUDIT_FILE.open("a", encoding="utf-8") as fh:
            fh.write(line)


def recent(limit: int = 80) -> list[dict[str, Any]]:
    if not AUDIT_FILE.exists():
        return []
    n = max(1, min(500, int(limit or 80)))
    with _lock:
        lines = AUDIT_FILE.read_text(encoding="utf-8").splitlines()
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
