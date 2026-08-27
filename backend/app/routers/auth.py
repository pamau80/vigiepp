from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel, Field

from .. import auth as auth_mod
from .. import oidc as oidc_mod

logger = logging.getLogger("vigiepp.auth")

router = APIRouter(prefix="/api/auth", tags=["auth"])


class AuthLoginRequest(BaseModel):
    pin: str = Field(..., min_length=1, max_length=128)

@router.get("/status")
def auth_status() -> dict[str, Any]:
    return auth_mod.auth_status()


@router.post("/login")
def auth_login(body: AuthLoginRequest, request: Request, response: Response) -> dict[str, Any]:
    if auth_mod.default_pins_blocked_on_cloud():
        raise HTTPException(
            503,
            "PIN por defecto bloqueado en cloud. Configura VIGIEPP_ADMIN_PIN y VIGIEPP_OPERATOR_PIN.",
        )
    if not auth_mod.auth_enabled():
        return {"ok": True, "auth_enabled": False, "role": "admin", "message": "Auth desactivada"}
    ip = auth_mod.client_ip(request)
    auth_mod.check_login_rate(ip)
    role = auth_mod.resolve_pin_role(body.pin)
    if not role:
        raise HTTPException(401, "PIN incorrecto")
    auth_mod.clear_login_rate(ip)
    token = auth_mod.create_session(role)
    auth_mod.set_session_cookie(response, token)
    return {
        "ok": True,
        "auth_enabled": True,
        "token": token,
        "role": role,
        "expires_hours": auth_mod.SESSION_HOURS,
    }


@router.post("/logout")
def auth_logout(request: Request, response: Response) -> dict[str, Any]:
    token = auth_mod.extract_token(request)
    auth_mod.revoke_session(token)
    auth_mod.clear_session_cookie(response)
    return {"ok": True}


@router.get("/me")
def auth_me(request: Request) -> dict[str, Any]:
    if not auth_mod.auth_enabled():
        return {"ok": True, "authenticated": True, "auth_enabled": False, "role": "admin"}
    token = auth_mod.extract_token(request)
    role = auth_mod.session_role(token)
    if not role:
        raise HTTPException(401, "No autorizado")
    return {"ok": True, "authenticated": True, "auth_enabled": True, "role": role}


@router.get("/oidc/config")
def oidc_config() -> dict[str, Any]:
    return oidc_mod.public_config()


@router.get("/oidc/login")
def oidc_login() -> dict[str, Any]:
    try:
        return {"ok": True, "url": oidc_mod.authorize_url()}
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc


@router.get("/oidc/callback")
def oidc_callback(response: Response, code: str = "", state: str = "") -> dict[str, Any]:
    if not code:
        raise HTTPException(400, "Falta code")
    if not oidc_mod.validate_state(state):
        raise HTTPException(400, "State OIDC inválido o expirado")
    try:
        tokens = oidc_mod.exchange_code(code)
        access = str(tokens.get("access_token") or "")
        user = oidc_mod.userinfo(access) if access else {}
        role = oidc_mod.resolve_role(user)
        token = auth_mod.create_session(role)
        auth_mod.set_session_cookie(response, token)
        return {
            "ok": True,
            "role": role,
            "token": token,
            "user": {
                "email": user.get("email"),
                "name": user.get("name") or user.get("preferred_username"),
            },
        }
    except Exception as exc:
        logger.exception("OIDC callback falló")
        raise HTTPException(401, "OIDC falló") from exc


