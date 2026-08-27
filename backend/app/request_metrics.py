"""Middleware de métricas HTTP por prefijo de ruta."""

from __future__ import annotations

import time

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from . import metrics as metrics_mod


def _route_bucket(path: str) -> str:
    if path == "/metrics":
        return "metrics"
    if path == "/" or path.startswith("/assets/"):
        return "static"
    if path.startswith("/api/"):
        parts = path.split("/")
        if len(parts) >= 3:
            return f"api_{parts[2]}"
        return "api"
    if path.startswith("/ws/"):
        return "websocket"
    return "other"


class RequestMetricsMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        bucket = _route_bucket(request.url.path)
        from .otel_trace import span

        with span("http", route=bucket):
            metrics_mod.inc(f"http_requests_{bucket}_total")
            start = time.perf_counter()
            try:
                response = await call_next(request)
                if response.status_code >= 500:
                    metrics_mod.inc("http_errors_total")
                return response
            except Exception:
                metrics_mod.inc("http_errors_total")
                raise
            finally:
                ms = (time.perf_counter() - start) * 1000.0
                metrics_mod.observe_http_ms(bucket, ms)
