"""Validación de URLs salientes (anti-SSRF) y hosts LAN."""

from __future__ import annotations

import ipaddress
import os
from urllib.parse import urlparse

from .paths import is_persistent


def is_private_hostname(host: str) -> bool:
    h = (host or "").strip().lower().split("%")[0]
    if not h:
        return False
    if h in ("localhost", "127.0.0.1", "::1") or h.endswith(".local"):
        return True
    try:
        ip = ipaddress.ip_address(h)
        return bool(ip.is_private or ip.is_loopback or ip.is_link_local)
    except ValueError:
        return h.endswith(".lan") or h.endswith(".home")


def is_blocked_host(host: str) -> bool:
    h = (host or "").strip().lower().split("%")[0]
    if h in ("localhost", "127.0.0.1", "::1", "0.0.0.0"):
        return True
    if h in ("metadata.google.internal", "metadata.goog"):
        return True
    try:
        ip = ipaddress.ip_address(h)
        if ip.is_loopback or ip.is_link_local:
            return True
        if ip == ipaddress.ip_address("169.254.169.254"):
            return True
    except ValueError:
        pass
    return False


def edge_outbound_allowed() -> bool:
    raw = os.getenv("VIGIEPP_ALLOW_LAN", "").strip().lower()
    if raw in ("1", "true", "yes", "on"):
        return True
    return is_persistent() or not bool(os.getenv("RENDER") or os.getenv("RENDER_SERVICE_ID"))


def validate_outbound_url(url: str, *, allow_public: bool = True) -> tuple[bool, str]:
    u = (url or "").strip()
    if not u:
        return False, "URL vacía"
    parsed = urlparse(u)
    if parsed.scheme not in ("http", "https"):
        return False, "Solo http/https"
    host = parsed.hostname
    if not host:
        return False, "Host inválido"
    if is_blocked_host(host):
        return False, "Host bloqueado"
    private = is_private_hostname(host)
    if private and not edge_outbound_allowed():
        return False, "LAN bloqueado en cloud — despliega edge o VIGIEPP_ALLOW_LAN=1"
    if not private and not allow_public:
        return False, "URL pública no permitida"
    return True, "ok"


def validate_lan_http_host(host: str) -> tuple[bool, str]:
    h = (host or "").strip()
    if not h:
        return False, "Host vacío"
    if is_blocked_host(h):
        return False, "Host bloqueado"
    if is_private_hostname(h) and not edge_outbound_allowed():
        return False, "LAN bloqueado en cloud — edge o VIGIEPP_ALLOW_LAN=1"
    return True, "ok"
