"""Validación RTSP unificada (anti-SSRF)."""

from __future__ import annotations

import os
from urllib.parse import urlparse

from .security_urls import edge_outbound_allowed, is_blocked_host, is_private_hostname


def validate_rtsp_url(url: str) -> str:
    raw = (url or "").strip()
    if not raw:
        raise ValueError("URL RTSP requerida")
    parsed = urlparse(raw)
    if parsed.scheme not in ("rtsp", "rtsps"):
        raise ValueError("Solo se permiten URLs rtsp:// o rtsps://")
    host = (parsed.hostname or "").lower()
    if not host:
        raise ValueError("URL sin host")
    if is_blocked_host(host):
        raise ValueError("Host RTSP no permitido")
    if is_private_hostname(host) and not edge_outbound_allowed():
        raise ValueError("RTSP LAN bloqueado en cloud — despliega edge o VIGIEPP_ALLOW_LAN=1")
    allow = os.getenv("VIGIEPP_RTSP_ALLOW", "").strip()
    if allow and allow != "*":
        allowed_hosts = {h.strip().lower() for h in allow.split(",") if h.strip()}
        if host not in allowed_hosts:
            raise ValueError("Host RTSP fuera de la lista permitida")
    return raw
