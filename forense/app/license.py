"""Licencia plan Forense — sin tocar el core VigiEPP."""

from __future__ import annotations

import hashlib
import hmac
import os
import time


def _signing_secret() -> str:
    return os.getenv("VIGIEPP_FORENSE_SIGNING_KEY", "vigiepp-forense-dev-key-change-in-prod")


def sign_license(site_id: str, expires_unix: int, *, secret: str | None = None) -> str:
    """Genera licencia producción: site_id.unix_exp.sig_hex."""
    site = (site_id or "").strip()
    if not site or "." in site:
        raise ValueError("site_id inválido (sin puntos)")
    if expires_unix <= int(time.time()):
        raise ValueError("La expiración debe ser futura")
    key = (secret or _signing_secret()).encode()
    payload = f"{site}.{expires_unix}"
    sig = hmac.new(key, payload.encode(), hashlib.sha256).hexdigest()[:32]
    return f"{payload}.{sig}"


def parse_license_key(key: str) -> dict:
    """Parsea licencia sin validar firma (útil para inspección)."""
    raw = (key or "").strip()
    if raw == "dev":
        return {"mode": "dev", "site_id": "dev", "expires_unix": None, "valid": True}
    parts = raw.split(".")
    if len(parts) != 3:
        return {"mode": "invalid", "valid": False, "detail": "formato inválido"}
    site_id, exp_s, sig = parts
    try:
        exp = int(exp_s)
    except ValueError:
        return {"mode": "invalid", "valid": False, "detail": "expiración inválida"}
    return {
        "mode": "production",
        "site_id": site_id,
        "expires_unix": exp,
        "signature": sig,
        "expired": exp < int(time.time()),
    }


def license_enabled() -> bool:
    return os.getenv("VIGIEPP_FORENSE", "").strip().lower() in ("1", "true", "yes")


def verify_license(key: str | None = None) -> tuple[bool, str]:
    if not license_enabled():
        return False, "Módulo Forense no habilitado (VIGIEPP_FORENSE)"
    raw = (key or os.getenv("VIGIEPP_FORENSE_LICENSE", "")).strip()
    if not raw:
        return False, "Falta VIGIEPP_FORENSE_LICENSE"
    if raw == "dev":
        return True, "licencia desarrollo"
    # Formato producción: site_id.unix_exp.sig_hex
    parts = raw.split(".")
    if len(parts) != 3:
        return False, "Formato de licencia inválido"
    site_id, exp_s, sig = parts
    try:
        exp = int(exp_s)
    except ValueError:
        return False, "Expiración inválida"
    if exp < int(time.time()):
        return False, "Licencia expirada"
    payload = f"{site_id}.{exp}"
    expected = hmac.new(_signing_secret().encode(), payload.encode(), hashlib.sha256).hexdigest()[:32]
    if not hmac.compare_digest(expected, sig):
        return False, "Firma de licencia inválida"
    return True, f"licencia {site_id}"


def license_status() -> dict:
    ok, detail = verify_license()
    return {"enabled": license_enabled(), "valid": ok, "detail": detail}
