"""Autenticación simple por PIN + sesión (cookie / header) con roles."""

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
ROLE_ADMIN = "admin"
ROLE_OPERATOR = "operator"

_lock = threading.Lock()
# token -> {expires_at, role}
_sessions: dict[str, dict[str, Any]] = {}


def auth_enabled() -> bool:
    return os.getenv("VIGIEPP_AUTH", "1").strip().lower() not in ("0", "false", "off", "no")


def docs_enabled() -> bool:
    return os.getenv("VIGIEPP_DOCS", "0").strip().lower() in ("1", "true", "yes", "on")


def admin_pin() -> str:
    pin = os.getenv("VIGIEPP_ADMIN_PIN", "vigiepp").strip()
    return pin or "vigiepp"


def operator_pin() -> str:
    pin = os.getenv("VIGIEPP_OPERATOR_PIN", "porteria").strip()
    return pin or "porteria"


def api_key() -> str | None:
    key = os.getenv("VIGIEPP_API_KEY", "").strip()
    return key or None


def _purge_expired() -> None:
    now = time.time()
    dead = [t for t, meta in _sessions.items() if float(meta.get("expires_at") or 0) <= now]
    for t in dead:
        _sessions.pop(t, None)


def create_session(role: str = ROLE_ADMIN) -> str:
    token = secrets.token_urlsafe(32)
    with _lock:
        _purge_expired()
        _sessions[token] = {
            "expires_at": time.time() + SESSION_HOURS * 3600,
            "role": role if role in (ROLE_ADMIN, ROLE_OPERATOR) else ROLE_ADMIN,
        }
    return token


def revoke_session(token: str | None) -> None:
    if not token:
        return
    with _lock:
        _sessions.pop(token, None)


def session_valid(token: str | None) -> bool:
    return session_meta(token) is not None


def session_meta(token: str | None) -> dict[str, Any] | None:
    if not token:
        return None
    with _lock:
        _purge_expired()
        meta = _sessions.get(token)
        if not meta:
            return None
        if float(meta.get("expires_at") or 0) <= time.time():
            _sessions.pop(token, None)
            return None
        return dict(meta)


def session_role(token: str | None) -> str | None:
    meta = session_meta(token)
    if meta:
        return str(meta.get("role") or ROLE_ADMIN)
    if token and credentials_ok(token):
        # PIN/API key en header: admin salvo que coincida solo operador
        if resolve_pin_role(token) == ROLE_OPERATOR:
            return ROLE_OPERATOR
        return ROLE_ADMIN
    return None


def resolve_pin_role(pin_or_key: str) -> str | None:
    candidate = (pin_or_key or "").strip()
    if not candidate:
        return None
    if hmac.compare_digest(candidate, admin_pin()):
        return ROLE_ADMIN
    key = api_key()
    if key and hmac.compare_digest(candidate, key):
        return ROLE_ADMIN
    # operador: solo si es distinto del admin
    op = operator_pin()
    if op and not hmac.compare_digest(op, admin_pin()) and hmac.compare_digest(candidate, op):
        return ROLE_OPERATOR
    return None


def credentials_ok(pin_or_key: str) -> bool:
    return resolve_pin_role(pin_or_key) is not None


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


def is_admin_only(method: str, path: str) -> bool:
    """Rutas que el operador (portería) no puede usar."""
    m = method.upper()
    # Lecturas permitidas al operador
    if m in ("GET", "HEAD", "OPTIONS"):
        if path.startswith("/api/identity/backup"):
            return True
        if path.startswith("/api/identity/workers") and path.endswith("/photo"):
            return True
        if path == "/api/identity/workers":
            return True
        if path.startswith("/api/notifications/config") or path.startswith("/api/notifications/log"):
            return True
        if path.startswith("/api/teach/"):
            return True
        return False

    # Mutaciones / posts
    if path in ("/api/detect", "/api/identity/identify"):
        return False
    if path.startswith("/api/rtsp/"):
        return False
    if path.startswith("/api/auth/"):
        return False

    if path.startswith("/api/identity/"):
        return True
    if path.startswith("/api/zones"):
        return True
    if path.startswith("/api/teach/"):
        return True
    if path.startswith("/api/notifications/"):
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
    if not auth_enabled():
        return "auth-disabled"
    token = extract_token(request)
    if session_valid(token):
        return token or ""
    if token and credentials_ok(token):
        return token
    raise HTTPException(status_code=401, detail="No autorizado. Iniciá sesión.")


def require_admin(request: Request) -> str:
    token = require_auth(request)
    if not auth_enabled():
        return token
    role = session_role(token)
    if role != ROLE_ADMIN:
        raise HTTPException(status_code=403, detail="Requiere rol administrador")
    return token


class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if not auth_enabled():
            return await call_next(request)

        path = request.url.path
        if is_public_path(path):
            return await call_next(request)

        if request.scope.get("type") == "websocket":
            return await call_next(request)

        if path.startswith("/api/") or path.startswith("/ws/"):
            token = extract_token(request)
            ok = session_valid(token) or (bool(token) and credentials_ok(token))
            if not ok:
                return JSONResponse({"detail": "No autorizado. Iniciá sesión."}, status_code=401)
            role = session_role(token)
            if role == ROLE_OPERATOR and is_admin_only(request.method, path):
                return JSONResponse(
                    {"detail": "Rol operador: solo monitoreo / portería."},
                    status_code=403,
                )

        return await call_next(request)


def auth_status() -> dict[str, Any]:
    return {
        "auth_enabled": auth_enabled(),
        "docs_enabled": docs_enabled(),
        "roles": [ROLE_ADMIN, ROLE_OPERATOR],
        "hint": "PIN admin (VIGIEPP_ADMIN_PIN) o PIN operador/portería (VIGIEPP_OPERATOR_PIN).",
    }
