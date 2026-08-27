"""RBAC — roles, permisos granulares y cuentas de guardias (base SaaS)."""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
import os
import secrets
import threading
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .paths import _bundle_data_root

logger = logging.getLogger("vigiepp.rbac")

ROLE_ADMIN = "admin"
ROLE_GUARD = "guard"
ROLE_OPERATOR = "operator"

PERM_ALL = "*"

PERMISSIONS: dict[str, str] = {
    "live.view": "Ver monitoreo en vivo",
    "live.detect": "Ejecutar detección EPP",
    "live.identify": "Identificar rostros",
    "live.rtsp": "Streams RTSP / cámara IP",
    "mass.view": "Vigilancia masiva NVR",
    "mass.scan": "Escanear masivo",
    "devices.view": "Ver NVR y cámaras",
    "devices.manage": "Administrar NVR y cámaras",
    "identity.view": "Ver personas enroladas",
    "identity.enroll": "Enrolar personas",
    "identity.manage": "Gestionar personas y backup",
    "teach.use": "Entrenar ropa / EPP",
    "config.view": "Ver configuración",
    "config.manage": "Modificar zonas, privacidad y guías",
    "reports.view": "Ver informes",
    "reports.manage": "Configurar notificaciones",
    "enterprise.manage": "Faenas, EHS y enterprise",
    "audit.view": "Bitácora administrativa",
    "users.manage": "Gestionar guardias y permisos",
}

DEFAULT_ROLE_PERMISSIONS: dict[str, list[str]] = {
    ROLE_ADMIN: [PERM_ALL],
    ROLE_GUARD: [
        "live.view",
        "live.detect",
        "live.identify",
        "live.rtsp",
        "mass.view",
        "mass.scan",
        "devices.view",
        "identity.view",
        "reports.view",
    ],
    ROLE_OPERATOR: [
        "live.view",
        "live.detect",
        "live.identify",
    ],
}

_lock = threading.Lock()


def _users_path() -> Path:
    return Path(_bundle_data_root() / "users.json")


def _pepper() -> bytes:
    key = os.getenv("VIGIEPP_SECRETS_KEY", "").strip()
    if key:
        return key.encode()
    return b"vigiepp-rbac-pepper-dev"


def hash_pin(pin: str, salt: str | None = None) -> tuple[str, str]:
    salt = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", (pin or "").encode(), salt.encode() + _pepper(), 120_000)
    return salt, digest.hex()


def verify_pin(pin: str, salt: str, pin_hash: str) -> bool:
    if not pin or not salt or not pin_hash:
        return False
    _, candidate = hash_pin(pin, salt)
    return hmac.compare_digest(candidate, pin_hash)


def _load_store() -> dict[str, Any]:
    path = _users_path()
    if not path.is_file():
        return {"users": [], "updated_at": None}
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(raw, dict) and isinstance(raw.get("users"), list):
            return raw
    except json.JSONDecodeError:
        logger.warning("users.json corrupto", exc_info=True)
    return {"users": [], "updated_at": None}


def _save_store(payload: dict[str, Any]) -> None:
    path = _users_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    payload["updated_at"] = datetime.now(UTC).isoformat()
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def list_users(include_inactive: bool = False) -> list[dict[str, Any]]:
    with _lock:
        users = list(_load_store().get("users") or [])
    out: list[dict[str, Any]] = []
    for row in users:
        if not include_inactive and not row.get("active", True):
            continue
        out.append(public_user(row))
    return out


def get_user(user_id: str) -> dict[str, Any] | None:
    with _lock:
        for row in _load_store().get("users") or []:
            if row.get("id") == user_id:
                return dict(row)
    return None


def effective_permissions(user: dict[str, Any]) -> list[str]:
    role = str(user.get("role") or ROLE_GUARD)
    base = list(DEFAULT_ROLE_PERMISSIONS.get(role, DEFAULT_ROLE_PERMISSIONS[ROLE_GUARD]))
    if PERM_ALL in base:
        return [PERM_ALL]
    extra = [p for p in (user.get("extra_permissions") or []) if p in PERMISSIONS]
    revoked = set(user.get("revoked_permissions") or [])
    merged = sorted(set(base + extra) - revoked)
    return merged


def has_permission(grants: list[str] | None, perm: str) -> bool:
    if not grants:
        return False
    if PERM_ALL in grants:
        return True
    return perm in grants


def has_any_permission(grants: list[str] | None, perms: list[str]) -> bool:
    return any(has_permission(grants, p) for p in perms)


def public_user(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": row.get("id"),
        "name": row.get("name"),
        "role": row.get("role"),
        "active": bool(row.get("active", True)),
        "site_ids": list(row.get("site_ids") or []),
        "extra_permissions": list(row.get("extra_permissions") or []),
        "revoked_permissions": list(row.get("revoked_permissions") or []),
        "permissions": effective_permissions(row),
        "created_at": row.get("created_at"),
        "updated_at": row.get("updated_at"),
    }


def authenticate_pin(pin: str) -> dict[str, Any] | None:
    candidate = (pin or "").strip()
    if not candidate:
        return None
    with _lock:
        for row in _load_store().get("users") or []:
            if not row.get("active", True):
                continue
            if verify_pin(candidate, str(row.get("pin_salt") or ""), str(row.get("pin_hash") or "")):
                return dict(row)
    return None


def session_payload_from_user(user: dict[str, Any]) -> dict[str, Any]:
    perms = effective_permissions(user)
    site_ids = list(user.get("site_ids") or [])
    if not site_ids:
        site_ids = ["*"]
    return {
        "role": str(user.get("role") or ROLE_GUARD),
        "user_id": user.get("id"),
        "display_name": user.get("name") or "Usuario",
        "permissions": perms,
        "site_ids": site_ids,
    }


def session_payload_env(role: str, display_name: str) -> dict[str, Any]:
    perms = list(DEFAULT_ROLE_PERMISSIONS.get(role, [PERM_ALL]))
    return {
        "role": role,
        "user_id": None,
        "display_name": display_name,
        "permissions": perms,
        "site_ids": ["*"],
    }


def create_user(
    *,
    name: str,
    pin: str,
    role: str = ROLE_GUARD,
    extra_permissions: list[str] | None = None,
    revoked_permissions: list[str] | None = None,
    site_ids: list[str] | None = None,
) -> dict[str, Any]:
    name = (name or "").strip()[:80] or "Guardia"
    role = role if role in DEFAULT_ROLE_PERMISSIONS else ROLE_GUARD
    pin = (pin or "").strip()
    if len(pin) < 4:
        raise ValueError("PIN demasiado corto (mín. 4 caracteres)")
    salt, pin_hash = hash_pin(pin)
    now = datetime.now(UTC).isoformat()
    user = {
        "id": uuid.uuid4().hex[:12],
        "name": name,
        "role": role,
        "pin_salt": salt,
        "pin_hash": pin_hash,
        "active": True,
        "extra_permissions": [p for p in (extra_permissions or []) if p in PERMISSIONS],
        "revoked_permissions": [p for p in (revoked_permissions or []) if p in PERMISSIONS],
        "site_ids": list(site_ids or []),
        "created_at": now,
        "updated_at": now,
    }
    with _lock:
        data = _load_store()
        users: list[dict[str, Any]] = list(data.get("users") or [])
        users.append(user)
        data["users"] = users
        _save_store(data)
    return public_user(user)


def update_user(user_id: str, patch: dict[str, Any]) -> dict[str, Any]:
    with _lock:
        data = _load_store()
        users: list[dict[str, Any]] = list(data.get("users") or [])
        idx = next((i for i, u in enumerate(users) if u.get("id") == user_id), None)
        if idx is None:
            raise ValueError("Usuario no encontrado")
        row = dict(users[idx])
        if "name" in patch:
            row["name"] = str(patch["name"] or "").strip()[:80] or row.get("name")
        if "role" in patch:
            role = str(patch["role"])
            row["role"] = role if role in DEFAULT_ROLE_PERMISSIONS else row.get("role")
        if "active" in patch:
            row["active"] = bool(patch["active"])
        if "extra_permissions" in patch:
            row["extra_permissions"] = [p for p in patch["extra_permissions"] if p in PERMISSIONS]
        if "revoked_permissions" in patch:
            row["revoked_permissions"] = [p for p in patch["revoked_permissions"] if p in PERMISSIONS]
        if "site_ids" in patch:
            row["site_ids"] = list(patch["site_ids"] or [])
        if patch.get("pin"):
            salt, pin_hash = hash_pin(str(patch["pin"]))
            row["pin_salt"] = salt
            row["pin_hash"] = pin_hash
        row["updated_at"] = datetime.now(UTC).isoformat()
        users[idx] = row
        data["users"] = users
        _save_store(data)
        return public_user(row)


def delete_user(user_id: str) -> None:
    update_user(user_id, {"active": False})


def route_required_permissions(method: str, path: str) -> list[str] | None:
    """Permisos requeridos (cualquiera). None = solo autenticación."""
    m = method.upper()

    if path.startswith("/api/auth/users"):
        return ["users.manage"]

    if path in ("/api/detect",):
        return ["live.detect"]
    if path.startswith("/api/identity/identify"):
        return ["live.identify"]
    if path.startswith("/api/rtsp/"):
        return ["live.rtsp"]

    if path.startswith("/api/surveillance/"):
        return ["mass.scan"] if m != "GET" else ["mass.view"]

    if path.startswith("/api/nvr/"):
        return ["devices.manage"] if m not in ("GET", "HEAD", "OPTIONS") else ["devices.view"]
    if path.startswith("/api/cameras"):
        return ["devices.manage"] if m not in ("GET", "HEAD", "OPTIONS") else ["devices.view"]
    if path.startswith("/api/watchlist"):
        return ["devices.manage"] if m not in ("GET", "HEAD", "OPTIONS") else ["devices.view"]

    if path.startswith("/api/identity/"):
        if path.startswith(("/api/identity/backup", "/api/identity/consent")):
            return ["identity.manage"]
        if m in ("GET", "HEAD", "OPTIONS"):
            if path.endswith("/photo"):
                return ["identity.view"]
            if path == "/api/identity/workers":
                return ["identity.view"]
            return ["identity.view"]
        if "enroll" in path:
            return ["identity.enroll"]
        return ["identity.manage"]

    if path.startswith("/api/teach/"):
        return ["teach.use"]

    if path.startswith("/api/zones"):
        return ["config.manage"] if m not in ("GET", "HEAD", "OPTIONS") else ["config.view", "live.view"]

    if path.startswith("/api/privacy"):
        return ["config.manage"] if m not in ("GET", "HEAD", "OPTIONS") else ["config.view"]

    if path.startswith(("/api/sites", "/api/ehs")):
        return ["enterprise.manage"]

    if path.startswith("/api/audit"):
        return ["audit.view"]

    if path.startswith("/api/reports/"):
        return ["reports.manage"] if m not in ("GET", "HEAD", "OPTIONS") else ["reports.view"]

    if path.startswith("/api/notifications/"):
        if path.endswith(("/config", "/send")) or m not in ("GET", "HEAD", "OPTIONS"):
            return ["reports.manage"]
        return ["reports.view"]

    if path.startswith("/api/evidence/"):
        return ["reports.view"]

    if path.startswith("/api/scans"):
        return ["identity.view", "reports.view"]

    return None


def check_route_access(grants: list[str] | None, method: str, path: str) -> bool:
    required = route_required_permissions(method, path)
    if required is None:
        return True
    return has_any_permission(grants, required)


def check_site_access(site_ids: list[str] | None, active_site_id: str) -> bool:
    if not site_ids or "*" in site_ids:
        return True
    return active_site_id in site_ids


def catalog() -> dict[str, Any]:
    return {
        "roles": [
            {"id": ROLE_ADMIN, "label": "Administrador", "permissions": DEFAULT_ROLE_PERMISSIONS[ROLE_ADMIN]},
            {"id": ROLE_GUARD, "label": "Guardia sala de cámaras", "permissions": DEFAULT_ROLE_PERMISSIONS[ROLE_GUARD]},
            {"id": ROLE_OPERATOR, "label": "Portería / kiosk", "permissions": DEFAULT_ROLE_PERMISSIONS[ROLE_OPERATOR]},
        ],
        "permissions": [{"id": k, "label": v} for k, v in PERMISSIONS.items()],
    }
