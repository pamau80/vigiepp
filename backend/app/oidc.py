"""OIDC / SSO opcional (Azure AD, Google Workspace, Okta-compatible)."""

from __future__ import annotations

import json
import logging
import os
import secrets
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

logger = logging.getLogger("vigiepp.oidc")

_pending: dict[str, float] = {}
_STATE_TTL = 600.0


def configured() -> bool:
    return bool(
        os.getenv("VIGIEPP_OIDC_ISSUER", "").strip()
        and os.getenv("VIGIEPP_OIDC_CLIENT_ID", "").strip()
        and os.getenv("VIGIEPP_OIDC_CLIENT_SECRET", "").strip()
    )


def public_config() -> dict[str, Any]:
    issuer = os.getenv("VIGIEPP_OIDC_ISSUER", "").strip().rstrip("/")
    return {
        "enabled": configured(),
        "issuer": issuer,
        "client_id": os.getenv("VIGIEPP_OIDC_CLIENT_ID", "").strip(),
        "redirect_uri": os.getenv("VIGIEPP_OIDC_REDIRECT_URI", "").strip(),
        "scopes": os.getenv("VIGIEPP_OIDC_SCOPES", "openid profile email").strip(),
    }


def _redirect_uri() -> str:
    return os.getenv("VIGIEPP_OIDC_REDIRECT_URI", "").strip()


def _purge_pending() -> None:
    now = time.time()
    for k, ts in list(_pending.items()):
        if now - ts > _STATE_TTL:
            _pending.pop(k, None)


def authorize_url(state: str | None = None) -> str:
    if not configured():
        raise ValueError("OIDC no configurado")
    state = state or secrets.token_urlsafe(16)
    _purge_pending()
    _pending[state] = time.time()
    issuer = os.getenv("VIGIEPP_OIDC_ISSUER", "").strip().rstrip("/")
    params = {
        "client_id": os.getenv("VIGIEPP_OIDC_CLIENT_ID", "").strip(),
        "response_type": "code",
        "redirect_uri": _redirect_uri(),
        "scope": os.getenv("VIGIEPP_OIDC_SCOPES", "openid profile email"),
        "state": state,
    }
    return f"{issuer}/authorize?{urllib.parse.urlencode(params)}"


def validate_state(state: str) -> bool:
    if not state:
        return False
    _purge_pending()
    ts = _pending.get(state)
    if ts is None:
        return False
    if time.time() - ts > _STATE_TTL:
        _pending.pop(state, None)
        return False
    _pending.pop(state, None)
    return True


def _groups_from_userinfo(user: dict[str, Any]) -> set[str]:
    groups: set[str] = set()
    for key in ("groups", "roles"):
        raw = user.get(key)
        if isinstance(raw, list):
            groups.update(str(g).strip().lower() for g in raw if g)
        elif isinstance(raw, str) and raw.strip():
            groups.add(raw.strip().lower())
    return groups


def resolve_role(userinfo: dict[str, Any]) -> str:
    from .auth import ROLE_ADMIN, ROLE_OPERATOR

    groups = _groups_from_userinfo(userinfo)
    admin_raw = os.getenv("VIGIEPP_OIDC_ADMIN_GROUPS", "").strip()
    op_raw = os.getenv("VIGIEPP_OIDC_OPERATOR_GROUPS", "").strip()
    admin_groups = {g.strip().lower() for g in admin_raw.split(",") if g.strip()}
    op_groups = {g.strip().lower() for g in op_raw.split(",") if g.strip()}
    if admin_groups and groups.intersection(admin_groups):
        return ROLE_ADMIN
    if op_groups and groups.intersection(op_groups):
        return ROLE_OPERATOR
    default = os.getenv("VIGIEPP_OIDC_DEFAULT_ROLE", ROLE_OPERATOR).strip().lower()
    if default == ROLE_ADMIN:
        return ROLE_ADMIN
    return ROLE_OPERATOR


def exchange_code(code: str) -> dict[str, Any]:
    if not configured():
        raise ValueError("OIDC no configurado")
    issuer = os.getenv("VIGIEPP_OIDC_ISSUER", "").strip().rstrip("/")
    token_url = f"{issuer}/token"
    body = urllib.parse.urlencode(
        {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": _redirect_uri(),
            "client_id": os.getenv("VIGIEPP_OIDC_CLIENT_ID", "").strip(),
            "client_secret": os.getenv("VIGIEPP_OIDC_CLIENT_SECRET", "").strip(),
        }
    ).encode()
    req = urllib.request.Request(
        token_url,
        data=body,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read().decode())


def userinfo(access_token: str) -> dict[str, Any]:
    issuer = os.getenv("VIGIEPP_OIDC_ISSUER", "").strip().rstrip("/")
    url = f"{issuer}/userinfo"
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {access_token}"})
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read().decode())
