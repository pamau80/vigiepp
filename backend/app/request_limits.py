"""Límites de tamaño de petición (anti-DoS)."""

from __future__ import annotations

import os

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

_DEFAULT_MAX = int(os.getenv("VIGIEPP_MAX_BODY_MB", "12")) * 1024 * 1024


class MaxBodySizeMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, max_bytes: int | None = None):
        super().__init__(app)
        self._max = max_bytes or _DEFAULT_MAX

    async def dispatch(self, request: Request, call_next):
        if request.method in ("POST", "PUT", "PATCH"):
            cl = request.headers.get("content-length")
            if cl:
                try:
                    if int(cl) > self._max:
                        return JSONResponse(
                            {"detail": f"Payload demasiado grande (máx. {self._max // (1024 * 1024)} MB)"},
                            status_code=413,
                        )
                except ValueError:
                    pass
        return await call_next(request)
