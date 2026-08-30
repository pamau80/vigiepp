"""Adaptador VigiEPP ↔ ESP32 Alarm (endpoints /alarma y /ok)."""

from __future__ import annotations

import ipaddress
import threading
import time
import urllib.error
import urllib.request
from datetime import UTC, datetime
from typing import Any, Literal
from urllib.parse import urljoin, urlparse

Action = Literal["alarma", "ok"]

_lock = threading.Lock()
_last: dict[str, float] = {}


DEFAULT_HARDWARE: dict[str, Any] = {
    "enabled": False,
    "base_url": "",
    "alarma_path": "/alarma",
    "ok_path": "/ok",
    "method": "GET",
    "timeout_seconds": 4,
    "cooldown_seconds": 2,
    "on_non_compliant": True,
    "on_unknown_face": True,
    "on_zone_alert": False,
    "auto_ok": True,
    "require_identity_for_ok": False,
}


def merge_hardware(raw: dict[str, Any] | None) -> dict[str, Any]:
    hw = dict(DEFAULT_HARDWARE)
    if isinstance(raw, dict):
        for k, v in raw.items():
            if k in hw:
                hw[k] = v
    return hw


def _host_allowed(host: str) -> bool:
    """Evita SSRF: solo localhost / IPs privadas / .local."""
    h = (host or "").strip().lower().split("%")[0]
    if not h:
        return False
    if h in ("localhost", "127.0.0.1", "::1"):
        return True
    if h.endswith(".local"):
        return True
    try:
        ip = ipaddress.ip_address(h)
    except ValueError:
        # hostname LAN (ej. esp32-alarm.local ya cubierto; otros hostnames locales)
        return "." not in h or h.endswith((".lan", ".home"))
    return bool(ip.is_private or ip.is_loopback or ip.is_link_local)


def validate_base_url(url: str) -> tuple[bool, str]:
    u = (url or "").strip().rstrip("/")
    if not u:
        return False, "base_url vacío"
    parsed = urlparse(u)
    if parsed.scheme not in ("http", "https"):
        return False, "solo http/https"
    if not parsed.hostname:
        return False, "host inválido"
    if not _host_allowed(parsed.hostname):
        return False, "solo IPs privadas / localhost (el ESP32 debe estar en la misma red)"
    return True, u


def _build_url(base: str, path: str) -> str:
    base = base.rstrip("/") + "/"
    path = path if path.startswith("/") else f"/{path}"
    return urljoin(base, path.lstrip("/"))


def trigger(
    action: Action,
    *,
    base_url: str,
    alarma_path: str = "/alarma",
    ok_path: str = "/ok",
    method: str = "GET",
    timeout_seconds: float = 4.0,
    cooldown_seconds: float = 2.0,
    reason: str = "",
) -> dict[str, Any]:
    ok_url, detail = validate_base_url(base_url)
    if not ok_url:
        return {
            "ok": False,
            "action": action,
            "detail": detail,
            "ts": datetime.now(UTC).isoformat(),
        }

    path = alarma_path if action == "alarma" else ok_path
    url = _build_url(detail, path or ("/alarma" if action == "alarma" else "/ok"))
    now = time.time()
    with _lock:
        last = _last.get(action, 0.0)
        if cooldown_seconds > 0 and (now - last) < cooldown_seconds:
            return {
                "ok": True,
                "skipped": True,
                "action": action,
                "detail": "cooldown hardware",
                "url": url,
                "reason": reason,
                "ts": datetime.now(UTC).isoformat(),
            }
        _last[action] = now

    m = (method or "GET").upper()
    if m not in ("GET", "POST"):
        m = "GET"
    data = None
    headers = {"User-Agent": "VigiEPP/1.0", "Accept": "*/*"}
    if m == "POST":
        headers["Content-Type"] = "application/json"
        data = b'{"source":"VigiEPP","action":"' + action.encode() + b'"}'

    req = urllib.request.Request(url, data=data, headers=headers, method=m)
    try:
        with urllib.request.urlopen(req, timeout=float(timeout_seconds or 4)) as resp:
            body = resp.read(200).decode("utf-8", errors="ignore")
            return {
                "ok": True,
                "action": action,
                "url": url,
                "detail": f"HTTP {resp.status}",
                "body": body[:120],
                "reason": reason,
                "ts": datetime.now(UTC).isoformat(),
            }
    except urllib.error.HTTPError as exc:
        return {
            "ok": False,
            "action": action,
            "url": url,
            "detail": f"HTTP {exc.code}",
            "reason": reason,
            "ts": datetime.now(UTC).isoformat(),
        }
    except Exception as exc:  # noqa: BLE001
        return {
            "ok": False,
            "action": action,
            "url": url,
            "detail": str(exc),
            "reason": reason,
            "ts": datetime.now(UTC).isoformat(),
        }


def sync_from_scan(
    identity: dict[str, Any] | None,
    compliance: dict[str, Any],
    *,
    hardware: dict[str, Any],
    access_enabled: bool,
    require_identity: bool,
) -> dict[str, Any] | None:
    """Decide /alarma o /ok según EPP + identidad."""
    hw = merge_hardware(hardware)
    if not hw.get("enabled"):
        return None
    base = str(hw.get("base_url") or "").strip()
    if not base:
        return None

    known = bool((identity or {}).get("known") and (identity or {}).get("id"))
    ok_epp = bool(compliance.get("overall_compliant"))

    if access_enabled:
        allow = known and ok_epp
        if require_identity and not known:
            allow = False
        action: Action = "ok" if allow else "alarma"
        reason = "access_allow" if allow else "access_deny"
        return trigger(
            action,
            base_url=base,
            alarma_path=str(hw.get("alarma_path") or "/alarma"),
            ok_path=str(hw.get("ok_path") or "/ok"),
            method=str(hw.get("method") or "GET"),
            timeout_seconds=float(hw.get("timeout_seconds") or 4),
            cooldown_seconds=float(hw.get("cooldown_seconds") or 2),
            reason=reason,
        )

    if not ok_epp and hw.get("on_non_compliant", True):
        return trigger(
            "alarma",
            base_url=base,
            alarma_path=str(hw.get("alarma_path") or "/alarma"),
            ok_path=str(hw.get("ok_path") or "/ok"),
            method=str(hw.get("method") or "GET"),
            timeout_seconds=float(hw.get("timeout_seconds") or 4),
            cooldown_seconds=float(hw.get("cooldown_seconds") or 2),
            reason="non_compliant",
        )

    if ok_epp and hw.get("auto_ok", True):
        if hw.get("require_identity_for_ok") and not known:
            return None
        return trigger(
            "ok",
            base_url=base,
            alarma_path=str(hw.get("alarma_path") or "/alarma"),
            ok_path=str(hw.get("ok_path") or "/ok"),
            method=str(hw.get("method") or "GET"),
            timeout_seconds=float(hw.get("timeout_seconds") or 4),
            cooldown_seconds=float(hw.get("cooldown_seconds") or 2),
            reason="compliant",
        )
    return None


def trigger_unknown(hardware: dict[str, Any]) -> dict[str, Any] | None:
    hw = merge_hardware(hardware)
    if not hw.get("enabled") or not hw.get("on_unknown_face", True):
        return None
    base = str(hw.get("base_url") or "").strip()
    if not base:
        return None
    return trigger(
        "alarma",
        base_url=base,
        alarma_path=str(hw.get("alarma_path") or "/alarma"),
        ok_path=str(hw.get("ok_path") or "/ok"),
        method=str(hw.get("method") or "GET"),
        timeout_seconds=float(hw.get("timeout_seconds") or 4),
        cooldown_seconds=float(hw.get("cooldown_seconds") or 2),
        reason="unknown_face",
    )


def trigger_zone(hardware: dict[str, Any]) -> dict[str, Any] | None:
    hw = merge_hardware(hardware)
    if not hw.get("enabled") or not hw.get("on_zone_alert", False):
        return None
    base = str(hw.get("base_url") or "").strip()
    if not base:
        return None
    return trigger(
        "alarma",
        base_url=base,
        alarma_path=str(hw.get("alarma_path") or "/alarma"),
        ok_path=str(hw.get("ok_path") or "/ok"),
        method=str(hw.get("method") or "GET"),
        timeout_seconds=float(hw.get("timeout_seconds") or 4),
        cooldown_seconds=float(hw.get("cooldown_seconds") or 2),
        reason="zone_alert",
    )
