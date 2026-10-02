"""Validaciones de arranque para producción."""

from __future__ import annotations

import logging
import os

logger = logging.getLogger("vigiepp.startup")


def on_cloud() -> bool:
    return bool(os.getenv("RENDER") or os.getenv("RENDER_SERVICE_ID"))


def run_startup_security_checks() -> dict[str, object]:
    from . import auth as auth_mod
    from .paths import is_persistent

    warnings: list[str] = []
    ok = True

    if auth_mod.auth_enabled() and auth_mod.default_pins_blocked():
        warnings.append(
            "PIN por defecto activo — configura VIGIEPP_ADMIN_PIN y VIGIEPP_OPERATOR_PIN "
            "(o VIGIEPP_ALLOW_DEFAULT_PINS=1 solo en dev)"
        )
        ok = False

    if not auth_mod.auth_enabled() and is_persistent():
        warnings.append(
            "VIGIEPP_AUTH=0 con datos persistentes — cualquiera en LAN tiene acceso admin"
        )

    if on_cloud() and not os.getenv("VIGIEPP_SECRETS_KEY", "").strip():
        warnings.append("VIGIEPP_SECRETS_KEY no configurada — credenciales NVR en disco local")

    cors = os.getenv("VIGIEPP_CORS_ORIGINS", "").strip()
    if cors == "*":
        warnings.append("VIGIEPP_CORS_ORIGINS=* inseguro con credenciales — usa orígenes explícitos")

    forense_on = os.getenv("VIGIEPP_FORENSE", "").strip().lower() in ("1", "true", "yes")
    forense_lic = os.getenv("VIGIEPP_FORENSE_LICENSE", "").strip()
    forense_sign = os.getenv("VIGIEPP_FORENSE_SIGNING_KEY", "").strip()
    if forense_on and forense_lic and forense_lic != "dev" and not forense_sign:
        warnings.append(
            "VIGIEPP_FORENSE_SIGNING_KEY no configurada — licencias Forense pueden falsificarse"
        )
        ok = False

    for msg in warnings:
        logger.warning("Startup security: %s", msg)

    return {"ok": ok, "warnings": warnings}


def strict_startup_required() -> bool:
    raw = os.getenv("VIGIEPP_STRICT_STARTUP", "").strip().lower()
    if raw in ("0", "false", "off", "no"):
        return False
    if raw in ("1", "true", "yes", "on"):
        return True
    from .paths import is_persistent

    return is_persistent() or on_cloud()
