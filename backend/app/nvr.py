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

logger = logging.getLogger("vigiepp.nvr")

_lock = threading.Lock()
NVR_FILE = data_dir() / "nvr_devices.json"

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
}


def _load() -> dict[str, Any]:
    if not NVR_FILE.exists():
        return {"devices": [], "updated_at": None}
    try:
        raw = json.loads(NVR_FILE.read_text(encoding="utf-8"))
        if isinstance(raw, dict) and isinstance(raw.get("devices"), list):
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
    try:
        req = Request(url, method="GET")
        with urlopen(req, timeout=timeout) as resp:  # noqa: S310
            body = resp.read(2048).decode("utf-8", errors="replace")
            return True, body[:500]
    except Exception as exc:  # noqa: BLE001
        return False, str(exc)


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
    else:
        probe_note = "Sin sondeo HTTP; se generan URLs RTSP por canal"

    channels = list_channels(
        v,
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
        "host": host,
        "device_name": device_name,
        "online_http": online,
        "probe_note": probe_note,
        "channels": channels,
        "channel_count": len(channels),
    }


def list_devices() -> list[dict[str, Any]]:
    with _lock:
        return list(_load().get("devices") or [])


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
    channels = list_channels(
        vendor,
        host,
        username=username,
        password=password,
        port=port,
        http_port=http_port,
        channel_count=channel_count,
        subtype=subtype,
    )
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
    }
    with _lock:
        data = _load()
        devices: list[dict[str, Any]] = list(data.get("devices") or [])
        if device_id:
            for d in devices:
                if d.get("id") == device_id:
                    d.update(entry)
                    _save({"devices": devices})
                    return d
        devices.append(entry)
        _save({"devices": devices})
        return entry


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
