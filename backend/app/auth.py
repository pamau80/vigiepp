"""Autenticación simple por PIN + sesión (cookie / header) con roles."""

from __future__ import annotations

import hmac
import json
import logging
import os
import secrets
import threading
import time
from pathlib import Path
from typing import Any

from fastapi import HTTPException, Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

COOKIE_NAME = "vigiepp_session"
HEADER_NAME = "X-VigiEPP-Key"
SESSION_HOURS = 12
ROLE_ADMIN = "admin"
ROLE_OPERATOR = "operator"
LOGIN_WINDOW_S = 300
LOGIN_MAX_ATTEMPTS = 8

logger = logging.getLogger("vigiepp.auth")

_lock = threading.Lock()
# token -> {expires_at, role}
_sessions: dict[str, dict[str, Any]] = {}
# ip -> [timestamps]
_login_attempts: dict[str, list[float]] = {}
_sessions_loaded = False


def _sessions_path() -> Path:
    try:
        from .paths import data_dir

        return data_dir() / "sessions.json"
    except Exception:  # noqa: BLE001
        return Path("sessions.json")


def _load_sessions() -> None:
    global _sessions_loaded
    if _sessions_loaded:
        return
    path = _sessions_path()
    try:
        if path.is_file():
            raw = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(raw, dict):
                now = time.time()
                for tok, meta in raw.items():
                    if isinstance(meta, dict) and float(meta.get("expires_at") or 0) > now:
                        _sessions[str(tok)] = {
                            "expires_at": float(meta["expires_at"]),
                            "role": meta.get("role") or ROLE_ADMIN,
                        }
    except Exception:
        logger.warning("No se pudieron cargar sesiones persistidas", exc_info=True)
    _sessions_loaded = True


def _persist_sessions() -> None:
    path = _sessions_path()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(_sessions, ensure_ascii=False), encoding="utf-8")
    except Exception:
        logger.warning("No se pudieron guardar sesiones", exc_info=True)


def auth_enabled() -> bool:
    return os.getenv("VIGIEPP_AUTH", "1").strip().lower() not in ("0", "false", "off", "no")


def docs_enabled() -> bool:
    return os.getenv("VIGIEPP_DOCS", "0").strip().lower() in ("1", "true", "yes", "on")


def admin_pin() -> str:
    pin = os.getenv("VIGIEPP_ADMIN_PIN", "").strip()
    if pin:
        return pin
    # Solo local/dev si no hay env; nunca en producción sin rotar
    return "vigiepp"


def operator_pin() -> str:
    pin = os.getenv("VIGIEPP_OPERATOR_PIN", "").strip()
    if pin:
        return pin
    return "porteria"


def using_default_pins() -> bool:
    admin_set = bool(os.getenv("VIGIEPP_ADMIN_PIN", "").strip())
    op_set = bool(os.getenv("VIGIEPP_OPERATOR_PIN", "").strip())
    return not admin_set or not op_set


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
        _load_sessions()
        _purge_expired()
        _sessions[token] = {
            "expires_at": time.time() + SESSION_HOURS * 3600,
            "role": role if role in (ROLE_ADMIN, ROLE_OPERATOR) else ROLE_ADMIN,
        }
        _persist_sessions()
    return token


def revoke_session(token: str | None) -> None:
    if not token:
        return
    with _lock:
        _load_sessions()
        _sessions.pop(token, None)
        _persist_sessions()


def session_valid(token: str | None) -> bool:
    return session_meta(token) is not None


def session_meta(token: str | None) -> dict[str, Any] | None:
    if not token:
        return None
    with _lock:
        _load_sessions()
        _purge_expired()
        meta = _sessions.get(token)
        if not meta:
            return None
        return dict(meta)


def session_role(token: str | None) -> str | None:
    meta = session_meta(token)
    if meta:
        return str(meta.get("role") or ROLE_ADMIN)
    if token and api_key() and hmac.compare_digest(token, api_key() or ""):
        return ROLE_ADMIN
    return None


def resolve_pin_role(pin_or_key: str) -> str | None:
    """Solo para POST /api/auth/login — no usar como bearer permanente."""
    candidate = (pin_or_key or "").strip()
    if not candidate:
        return None
    if hmac.compare_digest(candidate, admin_pin()):
        return ROLE_ADMIN
    key = api_key()
    if key and hmac.compare_digest(candidate, key):
        return ROLE_ADMIN
    op = operator_pin()
    if op and not hmac.compare_digest(op, admin_pin()) and hmac.compare_digest(candidate, op):
        return ROLE_OPERATOR
    return None


def credentials_ok(pin_or_key: str) -> bool:
    return resolve_pin_role(pin_or_key) is not None


def client_ip(request: Request) -> str:
    trust_proxy = os.getenv("VIGIEPP_TRUST_PROXY", "").strip().lower() in ("1", "true", "yes")
    if trust_proxy:
        forwarded = (request.headers.get("x-forwarded-for") or "").split(",")[0].strip()
        if forwarded:
            return forwarded[:64]
    if request.client and request.client.host:
        return request.client.host[:64]
    return "unknown"


_auth_fail_attempts: dict[str, list[float]] = {}
_AUTH_FAIL_WINDOW_S = 300
_AUTH_FAIL_MAX = 20


def check_auth_fail_rate(ip: str) -> None:
    now = time.time()
    with _lock:
        stamps = [t for t in _auth_fail_attempts.get(ip, []) if now - t < _AUTH_FAIL_WINDOW_S]
        if len(stamps) >= _AUTH_FAIL_MAX:
            raise HTTPException(429, "Demasiados intentos no autorizados. Esperá unos minutos.")
        stamps.append(now)
        _auth_fail_attempts[ip] = stamps


def clear_auth_fail_rate(ip: str) -> None:
    with _lock:
        _auth_fail_attempts.pop(ip, None)


def check_login_rate(ip: str) -> None:
    """Bloquea fuerza bruta: máx. LOGIN_MAX_ATTEMPTS en LOGIN_WINDOW_S."""
    now = time.time()
    with _lock:
        stamps = [t for t in _login_attempts.get(ip, []) if now - t < LOGIN_WINDOW_S]
        if len(stamps) >= LOGIN_MAX_ATTEMPTS:
            _login_attempts[ip] = stamps
            raise HTTPException(
                429,
                f"Demasiados intentos. Esperá {LOGIN_WINDOW_S // 60} minutos.",
            )
        stamps.append(now)
        _login_attempts[ip] = stamps


def clear_login_rate(ip: str) -> None:
    with _lock:
        _login_attempts.pop(ip, None)


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


def metrics_public() -> bool:
    if os.getenv("VIGIEPP_METRICS_PUBLIC", "").strip().lower() in ("1", "true", "yes"):
        return True
    if on_cloud():
        return False
    return os.getenv("VIGIEPP_METRICS_PUBLIC", "1").strip().lower() not in ("0", "false", "no")


def on_cloud() -> bool:
    return bool(os.getenv("RENDER") or os.getenv("RENDER_SERVICE_ID"))


def is_public_path(path: str) -> bool:
    if path in (
        "/",
        "/favicon.ico",
        "/api/health",
        "/api/auth/status",
        "/api/auth/login",
        "/api/auth/logout",
        "/api/auth/oidc/callback",
        "/api/auth/oidc/config",
    ):
        return True
    if path == "/metrics" and metrics_public():
        return True
    return bool(path.startswith("/assets/"))


def is_admin_only(method: str, path: str) -> bool:
    """Rutas que el operador (portería) no puede usar — delegado a rbac granular."""
    from .rbac import is_admin_only as rbac_admin_only

    return rbac_admin_only(method, path)


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
    if token and api_key() and hmac.compare_digest(token, api_key() or ""):
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

        needs_auth = path.startswith(("/api/", "/ws/")) or path == "/metrics"
        if needs_auth:
            token = extract_token(request)
            ok = session_valid(token) or (
                bool(token) and api_key() and hmac.compare_digest(token, api_key() or "")
            )
            if not ok:
                try:
                    check_auth_fail_rate(client_ip(request))
                except HTTPException as exc:
                    return JSONResponse({"detail": exc.detail}, status_code=exc.status_code)
                return JSONResponse({"detail": "No autorizado. Iniciá sesión."}, status_code=401)
            clear_auth_fail_rate(client_ip(request))
            role = session_role(token)
            try:
                from . import audit as audit_mod

                audit_mod.set_actor(role or "operator")
            except Exception:  # noqa: BLE001
                pass
            if role == ROLE_OPERATOR and is_admin_only(request.method, path):
                return JSONResponse(
                    {"detail": "Rol operador: solo monitoreo / portería."},
                    status_code=403,
                )

        return await call_next(request)


def default_pins_blocked_on_cloud() -> bool:
    return (
        auth_enabled()
        and on_cloud()
        and using_default_pins()
        and os.getenv("VIGIEPP_ALLOW_DEFAULT_PINS", "").strip().lower() not in ("1", "true", "yes")
    )


def auth_status() -> dict[str, Any]:
    defaults = using_default_pins()
    cloud = on_cloud()
    deny_defaults = cloud and defaults and os.getenv("VIGIEPP_ALLOW_DEFAULT_PINS", "").strip().lower() not in (
        "1",
        "true",
        "yes",
    )
    return {
        "auth_enabled": auth_enabled(),
        "docs_enabled": docs_enabled(),
        "roles": [ROLE_ADMIN, ROLE_OPERATOR],
        "default_pins_active": defaults,
        "production_pin_warning": bool(defaults and cloud),
        "auth_blocked_default_pins": deny_defaults,
        "hint": "Configura VIGIEPP_ADMIN_PIN y VIGIEPP_OPERATOR_PIN en producción.",
    }
