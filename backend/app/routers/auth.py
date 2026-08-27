from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel, Field

from .. import auth as auth_mod
from .. import oidc as oidc_mod
from .. import rbac as rbac_mod

logger = logging.getLogger("vigiepp.auth")

router = APIRouter(prefix="/api/auth", tags=["auth"])


class AuthLoginRequest(BaseModel):
    pin: str = Field(..., min_length=1, max_length=128)


class UserCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=80)
    pin: str = Field(..., min_length=4, max_length=64)
    role: str = Field(default=rbac_mod.ROLE_GUARD)
    extra_permissions: list[str] = Field(default_factory=list)
    revoked_permissions: list[str] = Field(default_factory=list)
    site_ids: list[str] = Field(default_factory=list)


class UserUpdateRequest(BaseModel):
    name: str | None = None
    pin: str | None = Field(default=None, min_length=4, max_length=64)
    role: str | None = None
    active: bool | None = None
    extra_permissions: list[str] | None = None
    revoked_permissions: list[str] | None = None
    site_ids: list[str] | None = None


@router.get("/status")
def auth_status() -> dict[str, Any]:
    data = auth_mod.auth_status()
    data["catalog"] = rbac_mod.catalog()
    return data


@router.get("/permissions")
def permissions_catalog() -> dict[str, Any]:
    return {"ok": True, **rbac_mod.catalog()}


@router.post("/login")
def auth_login(body: AuthLoginRequest, request: Request, response: Response) -> dict[str, Any]:
    if auth_mod.default_pins_blocked_on_cloud():
        raise HTTPException(
            503,
            "PIN por defecto bloqueado en cloud. Configura VIGIEPP_ADMIN_PIN y VIGIEPP_GUARD_PIN.",
        )
    if not auth_mod.auth_enabled():
        return {"ok": True, "auth_enabled": False, "role": auth_mod.ROLE_ADMIN, "message": "Auth desactivada"}
    ip = auth_mod.client_ip(request)
    auth_mod.check_login_rate(ip)
    payload = auth_mod.resolve_login(body.pin)
    if not payload:
        raise HTTPException(401, "PIN incorrecto")
    auth_mod.clear_login_rate(ip)
    token = auth_mod.create_session(payload)
    auth_mod.set_session_cookie(response, token)
    return {
        "ok": True,
        "auth_enabled": True,
        "token": token,
        "role": payload.get("role"),
        "display_name": payload.get("display_name"),
        "permissions": payload.get("permissions"),
        "site_ids": payload.get("site_ids"),
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
        return {
            "ok": True,
            "authenticated": True,
            "auth_enabled": False,
            "role": auth_mod.ROLE_ADMIN,
            "permissions": [rbac_mod.PERM_ALL],
        }
    token = auth_mod.extract_token(request)
    profile = auth_mod.session_profile(token)
    if not profile:
        raise HTTPException(401, "No autorizado")
    return {"ok": True, "authenticated": True, "auth_enabled": True, **profile}


@router.get("/users")
def list_users(request: Request) -> dict[str, Any]:
    auth_mod.require_permission(request, "users.manage")
    return {"ok": True, "users": rbac_mod.list_users(include_inactive=True)}


@router.post("/users")
def create_user(body: UserCreateRequest, request: Request) -> dict[str, Any]:
    auth_mod.require_permission(request, "users.manage")
    try:
        user = rbac_mod.create_user(
            name=body.name,
            pin=body.pin,
            role=body.role,
            extra_permissions=body.extra_permissions,
            revoked_permissions=body.revoked_permissions,
            site_ids=body.site_ids,
        )
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    return {"ok": True, "user": user}


@router.patch("/users/{user_id}")
def update_user(user_id: str, body: UserUpdateRequest, request: Request) -> dict[str, Any]:
    auth_mod.require_permission(request, "users.manage")
    patch = body.model_dump(exclude_unset=True)
    try:
        user = rbac_mod.update_user(user_id, patch)
    except ValueError as exc:
        raise HTTPException(404, str(exc)) from exc
    return {"ok": True, "user": user}


@router.delete("/users/{user_id}")
def deactivate_user(user_id: str, request: Request) -> dict[str, Any]:
    auth_mod.require_permission(request, "users.manage")
    try:
        rbac_mod.delete_user(user_id)
    except ValueError as exc:
        raise HTTPException(404, str(exc)) from exc
    return {"ok": True}


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
        name = user.get("name") or user.get("preferred_username") or "OIDC"
        payload = rbac_mod.session_payload_env(role, str(name))
        token = auth_mod.create_session(payload)
        auth_mod.set_session_cookie(response, token)
        return {
            "ok": True,
            "role": role,
            "token": token,
            "permissions": payload.get("permissions"),
            "user": {
                "email": user.get("email"),
                "name": name,
            },
        }
    except Exception as exc:
        logger.exception("OIDC callback falló")
        raise HTTPException(401, "OIDC falló") from exc
