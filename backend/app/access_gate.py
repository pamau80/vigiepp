"""Control de acceso físico: torniquete, relé Modbus, HTTP y gateways Wiegand."""

from __future__ import annotations

import ipaddress
import json
import logging
import threading
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from typing import Any, Literal
from urllib.parse import urljoin, urlparse

from . import hardware_alarm as hw_mod

logger = logging.getLogger("vigiepp.access_gate")

GateAction = Literal["allow", "deny"]

_lock = threading.Lock()
_last_action: dict[str, float] = {}

DEFAULT_GATE: dict[str, Any] = {
    "enabled": False,
    "driver": "esp32",
    "cooldown_seconds": 2,
    "on_non_compliant": True,
    "on_unknown_face": True,
    "on_zone_alert": False,
    "auto_ok": True,
    "require_identity_for_ok": False,
    "esp32": dict(hw_mod.DEFAULT_HARDWARE),
    "modbus": {
        "host": "",
        "port": 502,
        "unit_id": 1,
        "coil_allow": 0,
        "coil_deny": 1,
        "pulse_ms": 800,
    },
    "http_dual": {
        "allow_url": "",
        "deny_url": "",
        "method": "GET",
        "timeout_seconds": 4,
    },
    "wiegand": {
        "base_url": "",
        "allow_path": "/open",
        "deny_path": "/close",
        "method": "GET",
        "timeout_seconds": 4,
        "pass_rut": True,
    },
}


def merge_gate(raw: dict[str, Any] | None) -> dict[str, Any]:
    gate = json.loads(json.dumps(DEFAULT_GATE))
    if not isinstance(raw, dict):
        return gate
    for k, v in raw.items():
        if k in ("esp32", "modbus", "http_dual", "wiegand") and isinstance(v, dict):
            gate[k].update(v)
        elif k in gate and k not in ("esp32", "modbus", "http_dual", "wiegand"):
            gate[k] = v
    # Retrocompat: hardware plano → esp32
    if isinstance(raw.get("hardware"), dict):
        gate["esp32"] = hw_mod.merge_hardware(raw["hardware"])
        if raw["hardware"].get("enabled"):
            gate["enabled"] = True
            gate["driver"] = "esp32"
    elif raw.get("base_url"):
        gate["esp32"] = hw_mod.merge_hardware(raw)
        gate["enabled"] = bool(raw.get("enabled"))
        gate["driver"] = "esp32"
    gate["esp32"] = hw_mod.merge_hardware(gate.get("esp32"))
    return gate


def _host_private(host: str) -> bool:
    h = (host or "").strip().lower().split("%")[0]
    if not h or h in ("localhost", "127.0.0.1", "::1") or h.endswith(".local"):
        return True
    try:
        ip = ipaddress.ip_address(h)
        return bool(ip.is_private or ip.is_loopback or ip.is_link_local)
    except ValueError:
        return h.endswith(".lan") or h.endswith(".home")


def _cooldown(key: str, seconds: float) -> bool:
    now = time.time()
    with _lock:
        last = _last_action.get(key, 0.0)
        if seconds > 0 and (now - last) < seconds:
            return True
        _last_action[key] = now
    return False


def _http_call(url: str, method: str = "GET", timeout: float = 4.0, body: dict | None = None) -> tuple[bool, str]:
    u = (url or "").strip()
    if not u:
        return False, "URL vacía"
    parsed = urlparse(u)
    if parsed.scheme not in ("http", "https") or not parsed.hostname:
        return False, "URL inválida"
    if not _host_private(parsed.hostname):
        return False, "solo hosts LAN/privados"
    m = (method or "GET").upper()
    data = json.dumps(body or {"source": "VigiEPP"}).encode() if m == "POST" else None
    headers = {"User-Agent": "VigiEPP/2.0", "Accept": "*/*"}
    if data:
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(u, data=data, headers=headers, method=m)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return True, f"HTTP {resp.status}"
    except urllib.error.HTTPError as exc:
        return False, f"HTTP {exc.code}"
    except Exception as exc:  # noqa: BLE001
        return False, str(exc)


def _modbus_write_coil(host: str, port: int, unit_id: int, address: int, value: bool) -> tuple[bool, str]:
    try:
        from pymodbus.client import ModbusTcpClient
    except ImportError:
        return False, "pymodbus no instalado"

    host = (host or "").strip()
    if not host or not _host_private(host):
        return False, "host Modbus inválido o no LAN"
    try:
        client = ModbusTcpClient(host=host, port=int(port or 502), timeout=4)
        if not client.connect():
            return False, "Modbus sin conexión"
        result = client.write_coil(int(address), bool(value), slave=int(unit_id or 1))
        client.close()
        if result.isError():
            return False, f"Modbus error: {result}"
        return True, f"coil {address}={'ON' if value else 'OFF'}"
    except Exception as exc:  # noqa: BLE001
        return False, str(exc)


def execute(
    action: GateAction,
    gate: dict[str, Any],
    *,
    reason: str = "",
    rut: str | None = None,
) -> dict[str, Any]:
    cfg = merge_gate(gate)
    ts = datetime.now(timezone.utc).isoformat()
    if not cfg.get("enabled"):
        return {"ok": False, "skipped": True, "action": action, "detail": "gate disabled", "ts": ts}

    driver = str(cfg.get("driver") or "esp32").lower()
    cd = float(cfg.get("cooldown_seconds") or 2)
    if _cooldown(f"{driver}:{action}", cd):
        return {"ok": True, "skipped": True, "action": action, "detail": "cooldown", "driver": driver, "ts": ts}

    if driver == "esp32":
        hw_action = "ok" if action == "allow" else "alarma"
        esp = cfg.get("esp32") or {}
        res = hw_mod.trigger(
            hw_action,
            base_url=str(esp.get("base_url") or ""),
            alarma_path=str(esp.get("alarma_path") or "/alarma"),
            ok_path=str(esp.get("ok_path") or "/ok"),
            method=str(esp.get("method") or "GET"),
            timeout_seconds=float(esp.get("timeout_seconds") or 4),
            cooldown_seconds=0,
            reason=reason,
        )
        res["driver"] = "esp32"
        res["gate_action"] = action
        return res

    if driver == "modbus":
        mb = cfg.get("modbus") or {}
        coil = int(mb.get("coil_allow") or 0) if action == "allow" else int(mb.get("coil_deny") or 1)
        ok, detail = _modbus_write_coil(
            str(mb.get("host") or ""),
            int(mb.get("port") or 502),
            int(mb.get("unit_id") or 1),
            coil,
            True,
        )
        return {"ok": ok, "action": action, "driver": "modbus", "detail": detail, "coil": coil, "reason": reason, "ts": ts}

    if driver == "http_dual":
        hd = cfg.get("http_dual") or {}
        url = str(hd.get("allow_url") or "") if action == "allow" else str(hd.get("deny_url") or "")
        ok, detail = _http_call(url, str(hd.get("method") or "GET"), float(hd.get("timeout_seconds") or 4))
        return {"ok": ok, "action": action, "driver": "http_dual", "url": url, "detail": detail, "reason": reason, "ts": ts}

    if driver == "wiegand":
        wg = cfg.get("wiegand") or {}
        base = str(wg.get("base_url") or "").strip().rstrip("/")
        path = str(wg.get("allow_path") or "/open") if action == "allow" else str(wg.get("deny_path") or "/close")
        url = urljoin(base + "/", path.lstrip("/"))
        body = {"rut": rut, "action": action, "source": "VigiEPP"} if wg.get("pass_rut") and rut else None
        ok, detail = _http_call(url, str(wg.get("method") or "GET"), float(wg.get("timeout_seconds") or 4), body)
        return {"ok": ok, "action": action, "driver": "wiegand", "url": url, "detail": detail, "reason": reason, "ts": ts}

    return {"ok": False, "action": action, "driver": driver, "detail": "driver desconocido", "ts": ts}


def sync_from_scan(
    identity: dict[str, Any] | None,
    compliance: dict[str, Any],
    *,
    gate: dict[str, Any],
    access_enabled: bool,
    require_identity: bool,
) -> dict[str, Any] | None:
    cfg = merge_gate(gate)
    if not cfg.get("enabled"):
        return None

    known = bool((identity or {}).get("known") and (identity or {}).get("id"))
    ok_epp = bool(compliance.get("overall_compliant"))
    rut = (identity or {}).get("rut")

    if access_enabled:
        allow = known and ok_epp
        if require_identity and not known:
            allow = False
        action: GateAction = "allow" if allow else "deny"
        return execute(action, cfg, reason="access_gate", rut=rut)

    if not ok_epp and cfg.get("on_non_compliant", True):
        return execute("deny", cfg, reason="non_compliant", rut=rut)

    if ok_epp and cfg.get("auto_ok", True):
        if cfg.get("require_identity_for_ok") and not known:
            return None
        return execute("allow", cfg, reason="compliant", rut=rut)
    return None


def test_driver(gate: dict[str, Any], action: GateAction) -> dict[str, Any]:
    return execute(action, gate, reason="manual_test")
