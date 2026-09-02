"""Puente de autenticación — reutiliza PIN VigiEPP sin modificarlo."""

from __future__ import annotations

from fastapi import HTTPException, Request, Response

from app import auth as auth_mod


def require_forense_admin(request: Request) -> str:
    """Solo admin con sesión válida."""
    if not auth_mod.auth_enabled():
        return auth_mod.ROLE_ADMIN
    token = auth_mod.extract_token(request)
    role = auth_mod.session_role(token)
    if not role:
        raise HTTPException(401, "No autorizado")
    if role != auth_mod.ROLE_ADMIN:
        raise HTTPException(403, "Forense requiere rol administrador")
    return role


def login_pin(request: Request, response: Response, pin: str) -> dict:
    if auth_mod.default_pins_blocked_on_cloud():
        raise HTTPException(503, "PIN por defecto bloqueado en cloud")
    if not auth_mod.auth_enabled():
        return {"ok": True, "role": "admin", "auth_enabled": False, "token": ""}
    ip = auth_mod.client_ip(request)
    auth_mod.check_login_rate(ip)
    role = auth_mod.resolve_pin_role(pin)
    if not role:
        raise HTTPException(401, "PIN incorrecto")
    if role != auth_mod.ROLE_ADMIN:
        raise HTTPException(403, "Forense requiere PIN de administrador")
    auth_mod.clear_login_rate(ip)
    token = auth_mod.create_session(role)
    auth_mod.set_session_cookie(response, token)
    return {"ok": True, "token": token, "role": role}


def auth_status_payload(request: Request) -> dict:
    """Estado de sesión sin 401 — evita ruido en consola del navegador."""
    if not auth_mod.auth_enabled():
        return {
            "ok": True,
            "auth_enabled": False,
            "authenticated": True,
            "role": auth_mod.ROLE_ADMIN,
            "can_access": True,
            "token": None,
        }
    token = auth_mod.extract_token(request)
    role = auth_mod.session_role(token)
    is_admin = role == auth_mod.ROLE_ADMIN
    return {
        "ok": True,
        "auth_enabled": True,
        "authenticated": bool(role),
        "role": role if is_admin else None,
        "can_access": is_admin,
        "token": token if is_admin else None,
    }


def logout_session(request: Request, response: Response) -> dict:
    if auth_mod.auth_enabled():
        token = auth_mod.extract_token(request)
        if token:
            auth_mod.revoke_session(token)
        auth_mod.clear_session_cookie(response)
    return {"ok": True}
