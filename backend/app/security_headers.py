"""Cabeceras de seguridad (SOC2 / hardening) con CSP nonce por petición."""

from __future__ import annotations

import os
import secrets
import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

CSP_NONCE_STATE = "csp_nonce"


def new_csp_nonce() -> str:
    return secrets.token_urlsafe(16)


def get_csp_nonce(request: Request) -> str | None:
    return getattr(request.state, CSP_NONCE_STATE, None)


def ensure_csp_nonce(request: Request) -> str:
    nonce = get_csp_nonce(request)
    if not nonce:
        nonce = new_csp_nonce()
        setattr(request.state, CSP_NONCE_STATE, nonce)
    return nonce


def build_csp(nonce: str) -> str:
    return (
        "default-src 'self'; "
        f"script-src 'self' 'nonce-{nonce}'; "
        "style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data: blob:; "
        "media-src 'self' blob:; "
        "connect-src 'self'; "
        "font-src 'self'; "
        "object-src 'none'; "
        "base-uri 'self'; "
        "frame-ancestors 'none'"
    )


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        request_id = request.headers.get("x-request-id") or uuid.uuid4().hex[:16]
        nonce = ensure_csp_nonce(request)
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "camera=(self), microphone=(self), geolocation=()"
        response.headers["X-Permitted-Cross-Domain-Policies"] = "none"
        response.headers["Content-Security-Policy"] = build_csp(nonce)
        if os.getenv("VIGIEPP_HSTS", "").strip().lower() in ("1", "true", "yes"):
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        return response
