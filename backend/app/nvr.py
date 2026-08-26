"""NVR/DVR Dahua, Hikvision y RTSP genérico — URLs y descubrimiento de canales."""

from __future__ import annotations

import json
import logging
import re
import threading
import uuid
from datetime import datetime, timezone
from typing import Any
from urllib.parse import quote
from urllib.request import Request, urlopen

from .paths import data_dir
from . import secret_box as secret_mod
from .security_urls import validate_lan_http_host

logger = logging.getLogger("vigiepp.nvr")

_lock = threading.Lock()
NVR_FILE = data_dir() / "nvr_devices.json"


def refresh_paths() -> None:
    global NVR_FILE
    NVR_FILE = data_dir() / "nvr_devices.json"


def _device_password(device: dict[str, Any]) -> str:
    enc = device.get("password_enc")
    if enc:
        plain = secret_mod.decrypt_text(str(enc))
        if plain:
            return plain
    return str(device.get("password") or "")


def _store_password_fields(plain: str) -> dict[str, str]:
    enc = secret_mod.encrypt_text(plain or "")
    if enc:
        return {"password_enc": enc, "password": ""}
    return {"password": plain or ""}


def _sanitize_device(device: dict[str, Any]) -> dict[str, Any]:
    out = {k: v for k, v in device.items() if k not in ("password", "password_enc")}
    out["password_set"] = bool(_device_password(device))
    return out


def _maybe_migrate_password(device: dict[str, Any]) -> bool:
    if device.get("password") and not device.get("password_enc"):
        device.update(_store_password_fields(str(device.get("password") or "")))
        return True
    return False

VENDORS: dict[str, dict[str, Any]] = {
    "hikvision": {
        "id": "hikvision",
        "name": "Hikvision",
        "label": "Hikvision NVR/DVR",
        "default_port": 554,
        "http_port": 80,
        "max_channels": 32,
        "hint": "RTSP: /Streaming/Channels/{main} (principal) o {sub} (substream)",
    },
    "dahua": {
        "id": "dahua",
        "name": "Dahua",
        "label": "Dahua NVR/DVR",
        "default_port": 554,
        "http_port": 80,
        "max_channels": 32,
        "hint": "RTSP: /cam/realmonitor?channel=N&subtype=0|1",
    },
    "uniview": {
        "id": "uniview",
        "name": "Uniview",
        "label": "Uniview NVR",
        "default_port": 554,
        "http_port": 80,
        "max_channels": 32,
        "hint": "RTSP: /unicast/c{N}/s0/live",
    },
    "generic": {
        "id": "generic",
        "name": "RTSP genérico",
        "label": "URL RTSP manual",
        "default_port": 554,
        "http_port": 80,
        "max_channels": 1,
        "hint": "Pegá la URL RTSP completa del canal",
    },
    "onvif": {
        "id": "onvif",
        "name": "ONVIF",
        "label": "Cámara/NVR ONVIF",
        "default_port": 554,
        "http_port": 80,
        "max_channels": 16,
        "hint": "Sondeo ONVIF + URLs RTSP por fabricante detectado",
    },
}


def _load() -> dict[str, Any]:
    refresh_paths()
    if not NVR_FILE.exists():
        return {"devices": [], "updated_at": None}
    try:
        raw = json.loads(NVR_FILE.read_text(encoding="utf-8"))
        if isinstance(raw, dict) and isinstance(raw.get("devices"), list):
            migrated = False
            devices = []
            for d in raw.get("devices") or []:
                if isinstance(d, dict):
                    if _maybe_migrate_password(d):
                        migrated = True
                    devices.append(d)
            if migrated:
                raw["devices"] = devices
                _save(raw)
            return raw
    except json.JSONDecodeError:
        pass
    return {"devices": [], "updated_at": None}


def _save(payload: dict[str, Any]) -> None:
    payload["updated_at"] = datetime.now(timezone.utc).isoformat()
    NVR_FILE.parent.mkdir(parents=True, exist_ok=True)
    NVR_FILE.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    try:
        from . import cloud_persist as cloud_mod

        cloud_mod.schedule_push()
    except Exception:  # noqa: BLE001
        pass


def _cred(user: str, password: str) -> str:
    u = quote(user or "", safe="")
    p = quote(password or "", safe="")
    if u or p:
        return f"{u}:{p}@"
    return ""


def hikvision_rtsp(
    host: str,
    channel: int,
    *,
    username: str = "",
    password: str = "",
    port: int = 554,
    subtype: int = 0,
) -> str:
    """Canal 1 → 101 (main) / 102 (sub). Canal N → N*100+1."""
    ch = max(1, int(channel))
    stream_id = ch * 100 + (2 if subtype else 1)
    return f"rtsp://{_cred(username, password)}{host}:{port}/Streaming/Channels/{stream_id}"


def dahua_rtsp(
    host: str,
    channel: int,
    *,
    username: str = "",
    password: str = "",
    port: int = 554,
    subtype: int = 0,
) -> str:
    ch = max(1, int(channel))
    st = max(0, min(1, int(subtype)))
    return f"rtsp://{_cred(username, password)}{host}:{port}/cam/realmonitor?channel={ch}&subtype={st}"


def uniview_rtsp(
    host: str,
    channel: int,
    *,
    username: str = "",
    password: str = "",
    port: int = 554,
    subtype: int = 0,
) -> str:
    ch = max(1, int(channel))
    stream = 1 if subtype else 0
    return f"rtsp://{_cred(username, password)}{host}:{port}/unicast/c{ch}/s{stream}/live"


def build_channel_url(
    vendor: str,
    host: str,
    channel: int,
    *,
    username: str = "",
    password: str = "",
    port: int = 554,
    subtype: int = 0,
    custom_url: str = "",
) -> str:
    v = (vendor or "generic").lower().strip()
    host = (host or "").strip()
    if v == "generic" and custom_url.strip():
        return custom_url.strip()
    if not host:
        raise ValueError("Host/IP del NVR requerido")
    if v == "hikvision":
        return hikvision_rtsp(host, channel, username=username, password=password, port=port, subtype=subtype)
    if v == "dahua":
        return dahua_rtsp(host, channel, username=username, password=password, port=port, subtype=subtype)
    if v == "uniview":
        return uniview_rtsp(host, channel, username=username, password=password, port=port, subtype=subtype)
    raise ValueError(f"Fabricante no soportado: {vendor}")


def list_channels(
    vendor: str,
    host: str,
    *,
    username: str = "",
    password: str = "",
    port: int = 554,
    http_port: int = 80,
    channel_count: int = 8,
    subtype: int = 0,
) -> list[dict[str, Any]]:
    v = (vendor or "dahua").lower().strip()
    count = max(1, min(32, int(channel_count or 8)))
    out: list[dict[str, Any]] = []
    for i in range(1, count + 1):
        try:
            url = build_channel_url(
                v,
                host,
                i,
                username=username,
                password=password,
                port=port,
                subtype=subtype,
            )
        except ValueError:
            continue
        label = f"Canal {i}"
        out.append(
            {
                "channel": i,
                "name": label,
                "url": url,
                "subtype": subtype,
                "vendor": v,
            }
        )
    return out


def _http_probe(url: str, timeout: float = 4.0) -> tuple[bool, str]:
    from urllib.parse import urlparse

    parsed = urlparse(url)
    host = parsed.hostname or ""
    ok_h, msg = validate_lan_http_host(host)
    if not ok_h:
        return False, msg
    try:
        req = Request(url, method="GET")
        with urlopen(req, timeout=timeout) as resp:  # noqa: S310
            body = resp.read(2048).decode("utf-8", errors="replace")
            return True, body[:500]
    except Exception as exc:  # noqa: BLE001
        return False, str(exc)


_ONVIF_GET_DEVICE_INFO = (
    "<?xml version=\"1.0\" encoding=\"UTF-8\"?>"
    "<soap:Envelope xmlns:soap=\"http://www.w3.org/2003/05/soap-envelope\" "
    "xmlns:tds=\"http://www.onvif.org/ver10/device/wsdl\">"
    "<soap:Body><tds:GetDeviceInformation/></soap:Body></soap:Envelope>"
)


def _onvif_soap_post(host: str, http_port: int, envelope: str, timeout: float = 4.0) -> tuple[bool, str]:
    ok_h, msg = validate_lan_http_host(host)
    if not ok_h:
        return False, msg
    url = f"http://{host}:{int(http_port)}/onvif/device_service"
    try:
        data = envelope.encode("utf-8")
        req = Request(
            url,
            data=data,
            method="POST",
            headers={"Content-Type": "application/soap+xml; charset=utf-8"},
        )
        with urlopen(req, timeout=timeout) as resp:  # noqa: S310
            body = resp.read(8192).decode("utf-8", errors="replace")
            return True, body
    except Exception as exc:  # noqa: BLE001
        return False, str(exc)


def parse_onvif_device_info(xml: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for tag in ("Manufacturer", "Model", "FirmwareVersion", "SerialNumber", "HardwareId"):
        m = re.search(rf"<(?:tds:)?{tag}>([^<]+)", xml, re.I)
        if m:
            out[tag.lower()] = m.group(1).strip()
    return out


def infer_vendor_from_onvif(info: dict[str, str]) -> str:
    blob = " ".join(info.values()).lower()
    if "hikvision" in blob or "hik" in blob:
        return "hikvision"
    if "dahua" in blob:
        return "dahua"
    if "uniview" in blob:
        return "uniview"
    return "dahua"


def probe_onvif(
    host: str,
    *,
    http_port: int = 80,
    timeout: float = 4.0,
) -> dict[str, Any]:
    ok, body = _onvif_soap_post(host, http_port, _ONVIF_GET_DEVICE_INFO, timeout=timeout)
    if not ok:
        return {"ok": False, "error": body, "device_info": {}}
    info = parse_onvif_device_info(body)
    if not info:
        return {"ok": False, "error": "Respuesta ONVIF sin metadatos", "device_info": {}, "raw": body[:400]}
    return {
        "ok": True,
        "device_info": info,
        "inferred_vendor": infer_vendor_from_onvif(info),
        "device_name": info.get("model") or info.get("manufacturer") or host,
    }


def probe_device(
    vendor: str,
    host: str,
    *,
    username: str = "",
    password: str = "",
    port: int = 554,
    http_port: int = 80,
    channel_count: int = 8,
    subtype: int = 0,
) -> dict[str, Any]:
    v = (vendor or "dahua").lower().strip()
    host = (host or "").strip()
    if not host:
        raise ValueError("IP o host del NVR requerido")

    detected_vendor = v
    device_name = host
    online = False
    probe_note = ""
    onvif_meta: dict[str, Any] = {}

    if v == "onvif":
        onvif_result = probe_onvif(host, http_port=http_port)
        onvif_meta = onvif_result
        if onvif_result.get("ok"):
            online = True
            detected_vendor = str(onvif_result.get("inferred_vendor") or "dahua")
            device_name = str(onvif_result.get("device_name") or host)
            probe_note = "ONVIF: " + str(onvif_result.get("device_info", {}).get("manufacturer", ""))
        else:
            probe_note = f"ONVIF: {onvif_result.get('error', 'sin respuesta')}"
            detected_vendor = "dahua"

    if v == "hikvision":
        ok, body = _http_probe(f"http://{host}:{http_port}/ISAPI/System/deviceInfo")
        if ok:
            online = True
            m = re.search(r"<deviceName>([^<]+)", body)
            if m:
                device_name = m.group(1).strip()
        else:
            probe_note = f"HTTP ISAPI: {body[:120]}"
    elif v == "dahua":
        ok, body = _http_probe(f"http://{host}:{http_port}/cgi-bin/magicBox.cgi?action=getDeviceType")
        if ok and "type=" in body.lower():
            online = True
            device_name = body.strip().split("=", 1)[-1].strip()[:80]
        else:
            probe_note = f"HTTP CGI: {body[:120]}"
    elif v not in ("onvif", "generic"):
        probe_note = "Sin sondeo HTTP; se generan URLs RTSP por canal"

    channels = list_channels(
        detected_vendor,
        host,
        username=username,
        password=password,
        port=port,
        http_port=http_port,
        channel_count=channel_count,
        subtype=subtype,
    )

    return {
        "vendor": detected_vendor,
        "requested_vendor": v,
        "host": host,
        "device_name": device_name,
        "online_http": online,
        "probe_note": probe_note,
        "onvif": onvif_meta if v == "onvif" else None,
        "channels": channels,
        "channel_count": len(channels),
    }


def list_devices() -> list[dict[str, Any]]:
    with _lock:
        return [_sanitize_device(d) for d in (_load().get("devices") or [])]


def register_device(
    vendor: str,
    host: str,
    name: str,
    *,
    username: str = "",
    password: str = "",
    port: int = 554,
    http_port: int = 80,
    channel_count: int = 8,
    subtype: int = 0,
    device_id: str | None = None,
) -> dict[str, Any]:
    pwd_use = password
    if device_id and not pwd_use:
        with _lock:
            for d in (_load().get("devices") or []):
                if d.get("id") == device_id:
                    pwd_use = _device_password(d)
                    break
    channels = list_channels(
        vendor,
        host,
        username=username,
        password=pwd_use,
        port=port,
        http_port=http_port,
        channel_count=channel_count,
        subtype=subtype,
    )
    secret_fields = _store_password_fields(pwd_use) if pwd_use else {}
    entry = {
        "id": device_id or uuid.uuid4().hex[:10],
        "vendor": vendor,
        "host": host,
        "name": (name or "").strip()[:80] or f"NVR {host}",
        "port": port,
        "http_port": http_port,
        "username": username,
        "channel_count": len(channels),
        "subtype": subtype,
        "channels": channels,
        "enabled": True,
        **secret_fields,
    }
    with _lock:
        data = _load()
        devices: list[dict[str, Any]] = list(data.get("devices") or [])
        if device_id:
            for d in devices:
                if d.get("id") == device_id:
                    if not password:
                        entry.pop("password", None)
                        if d.get("password_enc"):
                            entry["password_enc"] = d["password_enc"]
                    d.update(entry)
                    _save({"devices": devices})
                    return _sanitize_device(d)
        devices.append(entry)
        _save({"devices": devices})
        return _sanitize_device(entry)


def delete_device(device_id: str) -> bool:
    with _lock:
        data = _load()
        devices = [d for d in (data.get("devices") or []) if d.get("id") != device_id]
        if len(devices) == len(data.get("devices") or []):
            return False
        _save({"devices": devices})
        return True


def list_vendors() -> list[dict[str, Any]]:
    return list(VENDORS.values())
