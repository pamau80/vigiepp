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
    "http_errors_total": 0,
}
_gauges: dict[str, float] = {
    "detect_last_ms": 0.0,
}
_http_latency: dict[str, float] = {}
_start = time.time()


def inc(name: str, delta: float = 1.0) -> None:
    with _lock:
        _counters[name] = _counters.get(name, 0.0) + delta


def set_gauge(name: str, value: float) -> None:
    with _lock:
        _gauges[name] = float(value)


def observe_detect_ms(ms: float) -> None:
    set_gauge("detect_last_ms", ms)


def observe_http_ms(bucket: str, ms: float) -> None:
    with _lock:
        _http_latency[bucket] = float(ms)


def prometheus_text(extra: dict[str, Any] | None = None) -> str:
    lines: list[str] = []
    with _lock:
        uptime = time.time() - _start
        lines.append("# HELP vigiepp_uptime_seconds Process uptime")
        lines.append("# TYPE vigiepp_uptime_seconds gauge")
        lines.append(f"vigiepp_uptime_seconds {uptime:.3f}")
        for k, v in _counters.items():
            safe = k.replace("-", "_")
            lines.append(f"# TYPE vigiepp_{safe} counter")
            lines.append(f"vigiepp_{safe} {v}")
        for k, v in _gauges.items():
            safe = k.replace("-", "_")
            lines.append(f"# TYPE vigiepp_{safe} gauge")
            lines.append(f"vigiepp_{safe} {v}")
        for k, v in _http_latency.items():
            safe = k.replace("-", "_")
            lines.append(f"# TYPE vigiepp_http_last_ms_{safe} gauge")
            lines.append(f"vigiepp_http_last_ms_{safe} {v:.3f}")
    if extra:
        for k, v in extra.items():
            lines.append(f"vigiepp_{k} {v}")
    return "\n".join(lines) + "\n"
