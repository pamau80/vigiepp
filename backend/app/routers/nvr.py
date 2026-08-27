from __future__ import annotations

from typing import Any

from fastapi import APIRouter

router = APIRouter(prefix="/api/nvr", tags=['nvr'])

from fastapi import HTTPException
from pydantic import BaseModel


class NVRProbeBody(BaseModel):
    vendor: str = "dahua"
    host: str
    username: str = ""
    password: str = ""
    port: int = 554
    http_port: int = 80
    channel_count: int = 8
    subtype: int = 0

class NVRRegisterBody(NVRProbeBody):
    name: str = ""
    id: str | None = None

@router.get("/vendors")
def nvr_vendors() -> dict[str, Any]:
    from .. import nvr as nvr_mod

    return {"ok": True, "vendors": nvr_mod.list_vendors()}


@router.post("/probe")
def nvr_probe(body: NVRProbeBody) -> dict[str, Any]:
    from .. import nvr as nvr_mod

    try:
        result = nvr_mod.probe_device(
            body.vendor,
            body.host,
            username=body.username,
            password=body.password,
            port=body.port,
            http_port=body.http_port,
            channel_count=body.channel_count,
            subtype=body.subtype,
        )
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    return {"ok": True, **result}


@router.get("/devices")
def nvr_devices_list() -> dict[str, Any]:
    from .. import nvr as nvr_mod

    return {"ok": True, "devices": nvr_mod.list_devices()}


@router.post("/devices")
def nvr_devices_register(body: NVRRegisterBody) -> dict[str, Any]:
    from .. import audit as audit_mod
    from .. import nvr as nvr_mod

    try:
        device = nvr_mod.register_device(
            body.vendor,
            body.host,
            body.name,
            username=body.username,
            password=body.password,
            port=body.port,
            http_port=body.http_port,
            channel_count=body.channel_count,
            subtype=body.subtype,
            device_id=body.id,
        )
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    audit_mod.log("nvr_register", detail=device.get("name") or device.get("host"))
    return {"ok": True, "device": device}


@router.delete("/devices/{device_id}")
def nvr_devices_delete(device_id: str) -> dict[str, Any]:
    from .. import audit as audit_mod
    from .. import nvr as nvr_mod

    ok = nvr_mod.delete_device(device_id)
    if not ok:
        raise HTTPException(404, "NVR no encontrado")
    audit_mod.log("nvr_delete", detail=device_id)
    return {"ok": True, "deleted": device_id}


@router.post("/devices/{device_id}/import-watchlist")
def nvr_import_watchlist(device_id: str, replace: bool = False) -> dict[str, Any]:
    from .. import nvr as nvr_mod
    from .. import watchlist as watch_mod

    devices = nvr_mod.list_devices()
    device = next((d for d in devices if d.get("id") == device_id), None)
    if not device:
        raise HTTPException(404, "NVR no encontrado")
    entries = []
    for ch in device.get("channels") or []:
        entries.append(
            {
                "name": f"{device.get('name')} · {ch.get('name')}",
                "url": ch.get("url"),
                "vendor": device.get("vendor"),
                "nvr_id": device_id,
                "channel": ch.get("channel"),
                "enabled": True,
            }
        )
    channels = watch_mod.import_channels(entries, replace=replace)
    return {"ok": True, "imported": len(entries), "channels": channels, "max": watch_mod.MAX_WATCH}


# ── Vigilancia masiva (watchlist) ───────────────────────────────────────────


