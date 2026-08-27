"""Validaciones de arranque para producción."""

from __future__ import annotations

import logging
import os

logger = logging.getLogger("vigiepp.startup")


def on_cloud() -> bool:
    return bool(os.getenv("RENDER") or os.getenv("RENDER_SERVICE_ID"))


def run_startup_security_checks() -> dict[str, bool]:
    from . import auth as auth_mod

    warnings: list[str] = []
    ok = True

    if auth_mod.auth_enabled() and on_cloud() and auth_mod.using_default_pins():
        allow = os.getenv("VIGIEPP_ALLOW_DEFAULT_PINS", "").strip().lower() in ("1", "true", "yes")
        if not allow:
            warnings.append(
                "PIN por defecto activo en cloud — configura VIGIEPP_ADMIN_PIN y VIGIEPP_OPERATOR_PIN"
            )
            ok = False

    if on_cloud() and not os.getenv("VIGIEPP_SECRETS_KEY", "").strip():
        warnings.append("VIGIEPP_SECRETS_KEY no configurada — credenciales NVR en disco local")

    cors = os.getenv("VIGIEPP_CORS_ORIGINS", "").strip()
    if cors == "*":
        warnings.append("VIGIEPP_CORS_ORIGINS=* inseguro con credenciales — usa orígenes explícitos")

    for msg in warnings:
        logger.warning("Startup security: %s", msg)

    return {"ok": ok, "warnings": warnings}
