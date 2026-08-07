"""Acumulador de tiempo sin EPP (exposición) por identidad / sesión."""

from __future__ import annotations

import threading
import time
from typing import Any

_lock = threading.Lock()
# key -> {open_at, closed_total}
_state: dict[str, dict[str, float]] = {}


def _key(identity: dict[str, Any] | None) -> str:
    if identity and identity.get("id"):
        return f"id:{identity['id']}"
    if identity and identity.get("name"):
        return f"name:{identity['name']}"
    return "anon"


def _fmt(seconds: float) -> str:
    s = int(max(0, seconds))
    if s < 60:
        return f"{s}s"
    m, sec = divmod(s, 60)
    if m < 60:
        return f"{m}m {sec}s"
    h, m = divmod(m, 60)
    return f"{h}h {m}m"


def update_exposure(compliant: bool, identity: dict[str, Any] | None = None) -> dict[str, Any]:
    """Si no cumple, acumula segundos de exposición; si cumple, cierra la racha abierta."""
    now = time.time()
    k = _key(identity)
    with _lock:
        st = _state.setdefault(k, {"open_at": 0.0, "closed_total": 0.0})
        if not compliant:
            if st["open_at"] <= 0:
                st["open_at"] = now
            current = st["closed_total"] + (now - st["open_at"])
            return {
                "active": True,
                "seconds": int(current),
                "label": _fmt(current),
                "key": k,
            }
        if st["open_at"] > 0:
            st["closed_total"] += max(0.0, now - st["open_at"])
            st["open_at"] = 0.0
        total = st["closed_total"]
        return {
            "active": False,
            "seconds": int(total),
            "label": _fmt(total) if total else "0s",
            "key": k,
            "session_total": int(total),
        }
