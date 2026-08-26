"""Métricas operativas simples (Prometheus text)."""

from __future__ import annotations

import threading
import time
from typing import Any

_lock = threading.Lock()
_counters: dict[str, float] = {
    "detect_requests_total": 0,
    "detect_errors_total": 0,
    "detect_busy_total": 0,
    "mass_scans_total": 0,
    "rtsp_streams_active": 0,
}
_gauges: dict[str, float] = {
    "detect_last_ms": 0.0,
}
_start = time.time()


def inc(name: str, delta: float = 1.0) -> None:
    with _lock:
        _counters[name] = _counters.get(name, 0.0) + delta


def set_gauge(name: str, value: float) -> None:
    with _lock:
        _gauges[name] = float(value)


def observe_detect_ms(ms: float) -> None:
    set_gauge("detect_last_ms", ms)


def prometheus_text(extra: dict[str, Any] | None = None) -> str:
    lines: list[str] = []
    with _lock:
        uptime = time.time() - _start
        lines.append("# HELP vigiepp_uptime_seconds Process uptime")
        lines.append("# TYPE vigiepp_uptime_seconds gauge")
        lines.append(f"vigiepp_uptime_seconds {uptime:.3f}")
        for k, v in _counters.items():
            lines.append(f"# TYPE vigiepp_{k} counter")
            lines.append(f"vigiepp_{k} {v}")
        for k, v in _gauges.items():
            lines.append(f"# TYPE vigiepp_{k} gauge")
            lines.append(f"vigiepp_{k} {v}")
    if extra:
        for k, v in extra.items():
            lines.append(f"vigiepp_{k} {v}")
    return "\n".join(lines) + "\n"
