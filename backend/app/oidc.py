"""OIDC / SSO opcional (Azure AD, Google Workspace, Okta-compatible)."""

from __future__ import annotations

import json
import logging
import os
import secrets
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

logger = logging.getLogger("vigiepp.oidc")

_pending: dict[str, float] = {}


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


def authorize_url(state: str | None = None) -> str:
    if not configured():
        raise ValueError("OIDC no configurado")
    state = state or secrets.token_urlsafe(16)
    _pending[state] = __import__("time").time()
    issuer = os.getenv("VIGIEPP_OIDC_ISSUER", "").strip().rstrip("/")
    params = {
        "client_id": os.getenv("VIGIEPP_OIDC_CLIENT_ID", "").strip(),
        "response_type": "code",
        "redirect_uri": _redirect_uri(),
        "scope": os.getenv("VIGIEPP_OIDC_SCOPES", "openid profile email"),
        "state": state,
    }
    return f"{issuer}/authorize?{urllib.parse.urlencode(params)}"


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
