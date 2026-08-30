"""RBAC granular por sección API — operador vs administrador edge."""

from __future__ import annotations

ROLE_ADMIN = "admin"
ROLE_OPERATOR = "operator"

# Lecturas bloqueadas para operador (portería / monitoreo).
_OPERATOR_READ_DENY_PREFIXES: tuple[str, ...] = (
    "/api/identity/backup",
    "/api/identity/consent",
    "/api/identity/workers",
    "/api/teach/",
    "/api/audit",
    "/api/reports/",
    "/api/evidence/",
    "/api/scans/",
    "/api/notifications/config",
    "/api/notifications/log",
    "/api/cameras",
    "/api/nvr/",
    "/api/watchlist",
    "/api/sites",
    "/api/privacy/",
    "/api/ehs/config",
    "/api/surveillance/",
)

# Escrituras permitidas para operador (portería en vivo).
_OPERATOR_WRITE_ALLOW: frozenset[tuple[str, str]] = frozenset(
    {
        ("POST", "/api/detect"),
        ("POST", "/api/identity/identify"),
        ("POST", "/api/ehs/push"),
        ("POST", "/api/auth/logout"),
    }
)

_OPERATOR_WRITE_ALLOW_PREFIXES: tuple[str, ...] = (
    "/api/rtsp/",
)


def operator_allowed(method: str, path: str) -> bool:
    """True si el rol operador puede usar method+path."""
    m = method.upper()
    if m in ("GET", "HEAD", "OPTIONS"):
        if path.startswith("/api/identity/workers") and path.endswith("/photo"):
            return False
        return not any(path.startswith(p) for p in _OPERATOR_READ_DENY_PREFIXES)

    if (m, path) in _OPERATOR_WRITE_ALLOW:
        return True
    if any(path.startswith(p) for p in _OPERATOR_WRITE_ALLOW_PREFIXES):
        return True
    if path.startswith("/api/auth/"):
        return path in ("/api/auth/logout", "/api/auth/me")
    return False


def is_admin_only(method: str, path: str) -> bool:
    """Compatibilidad con AuthMiddleware — True si operador no puede acceder."""
    return not operator_allowed(method, path)


def rbac_summary() -> dict[str, object]:
    """Resumen factual para /api/health.excellence."""
    return {
        "granular": True,
        "roles": [ROLE_ADMIN, ROLE_OPERATOR],
        "operator_sections": {
            "porteria": ["detect", "identify", "rtsp"],
            "monitoreo": ["zones_read", "actions_read", "ehs_incidents_read", "ehs_push"],
            "bloqueado": [
                "identity_admin",
                "teach",
                "cameras_nvr",
                "ehs_config",
                "audit_reports",
                "actions_write",
            ],
        },
    }
