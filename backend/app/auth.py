"""Autenticación simple por PIN + sesión (cookie / header)."""

from __future__ import annotations

import hmac
import os
import secrets
import threading
import time
from typing import Any

from fastapi import HTTPException, Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

COOKIE_NAME = "vigiepp_session"
HEADER_NAME = "X-VigiEPP-Key"
SESSION_HOURS = 12

_lock = threading.Lock()
_sessions: dict[str, float] = {}  # token -> expires_at epoch


def auth_enabled() -> bool:
    return os.getenv("VIGIEPP_AUTH", "1").strip().lower() not in ("0", "false", "off", "no")


def docs_enabled() -> bool:
    return os.getenv("VIGIEPP_DOCS", "0").strip().lower() in ("1", "true", "yes", "on")


def admin_pin() -> str:
    pin = os.getenv("VIGIEPP_ADMIN_PIN", "vigiepp").strip()
    return pin or "vigiepp"


def api_key() -> str | None:
    key = os.getenv("VIGIEPP_API_KEY", "").strip()
    return key or None


def _purge_expired() -> None:
    now = time.time()
    dead = [t for t, exp in _sessions.items() if exp <= now]
    for t in dead:
        _sessions.pop(t, None)


def create_session() -> str:
    token = secrets.token_urlsafe(32)
    with _lock:
        _purge_expired()
        _sessions[token] = time.time() + SESSION_HOURS * 3600
    return token


def revoke_session(token: str | None) -> None:
    if not token:
        return
    with _lock:
        _sessions.pop(token, None)


def session_valid(token: str | None) -> bool:
    if not token:
        return False
    with _lock:
        _purge_expired()
        exp = _sessions.get(token)
        if exp is None:
            return False
        if exp <= time.time():
            _sessions.pop(token, None)
            return False
        return True


def credentials_ok(pin_or_key: str) -> bool:
    candidate = (pin_or_key or "").strip()
    if not candidate:
        return False
    if hmac.compare_digest(candidate, admin_pin()):
        return True
    key = api_key()
    if key and hmac.compare_digest(candidate, key):
        return True
    return False


def extract_token(request: Request) -> str | None:
    cookie = request.cookies.get(COOKIE_NAME)
    if cookie:
        return cookie
    header = request.headers.get(HEADER_NAME) or request.headers.get("Authorization")
    if not header:
        return None
    if header.lower().startswith("bearer "):
        return header[7:].strip()
    return header.strip()


def is_public_path(path: str) -> bool:
    if path in (
        "/",
        "/favicon.ico",
        "/api/health",
        "/api/auth/status",
        "/api/auth/login",
        "/api/auth/logout",
    ):
        return True
    if path.startswith("/assets/"):
        return True
    return False


def set_session_cookie(response: Response, token: str) -> None:
    secure = os.getenv("VIGIEPP_COOKIE_SECURE", "0").strip().lower() not in ("0", "false", "off")
    response.set_cookie(
        key=COOKIE_NAME,
        value=token,
        httponly=True,
        secure=secure,
        samesite="lax",
        max_age=SESSION_HOURS * 3600,
        path="/",
    )


def clear_session_cookie(response: Response) -> None:
    response.delete_cookie(COOKIE_NAME, path="/")


def require_auth(request: Request) -> str:
    """Devuelve token de sesión o API key válida; 401 si no."""
    if not auth_enabled():
        return "auth-disabled"
    token = extract_token(request)
    if session_valid(token):
        return token or ""
    # API key / PIN directo en header (integraciones)
    if token and credentials_ok(token):
        return token
    raise HTTPException(status_code=401, detail="No autorizado. Iniciá sesión.")


class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if not auth_enabled():
            return await call_next(request)

        path = request.url.path
        if is_public_path(path):
            return await call_next(request)

        # WebSocket: se valida en el handler (middleware HTTP no aplica igual)
        if request.scope.get("type") == "websocket":
            return await call_next(request)

        if path.startswith("/api/") or path.startswith("/ws/"):
            token = extract_token(request)
            ok = session_valid(token) or (bool(token) and credentials_ok(token))
            if not ok:
                return JSONResponse({"detail": "No autorizado. Iniciá sesión."}, status_code=401)

        return await call_next(request)


def auth_status() -> dict[str, Any]:
    return {
        "auth_enabled": auth_enabled(),
        "docs_enabled": docs_enabled(),
        "hint": "Usá el PIN de administrador (variable VIGIEPP_ADMIN_PIN).",
    }
