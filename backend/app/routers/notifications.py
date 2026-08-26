from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from .. import notifications as notif_mod

router = APIRouter(prefix="/api/notifications", tags=["notifications"])


class NotifyConfigBody(BaseModel):
    enabled: Optional[bool] = None
    on_non_compliant: Optional[bool] = None
    on_unknown_face: Optional[bool] = None
    on_zone_alert: Optional[bool] = None
    only_known_workers: Optional[bool] = None
    cooldown_seconds: Optional[int] = None
    access_control: Optional[dict[str, Any]] = None
    channels: Optional[dict[str, Any]] = None
    template: Optional[dict[str, str]] = None
    recipients_extra: Optional[list[str]] = None


class NotifySendBody(BaseModel):
    name: str = "Prueba"
    rut: str = "—"
    profile: str = "general"
    summary: str = "Notificación de prueba VigiEPP"
    missing: list[str] = Field(default_factory=list)
    worker_id: Optional[str] = None
    force: bool = True


class HardwareTestBody(BaseModel):
    action: str = "alarma"

@router.get("/config")
def notifications_config_get() -> dict[str, Any]:
    cfg = notif_mod.get_config()
    return {**cfg, "email_transport": notif_mod.email_transport_status()}


@router.post("/config")
def notifications_config_set(body: NotifyConfigBody) -> dict[str, Any]:
    patch = body.model_dump(exclude_none=True)
    try:
        return {"ok": True, "config": notif_mod.save_config(patch)}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/log")
def notifications_log(limit: int = 40) -> list[dict[str, Any]]:
    return notif_mod.recent_log(limit=limit)


@router.post("/send")
def notifications_send(body: NotifySendBody) -> dict[str, Any]:
    return notif_mod.send_notification(
        {
            "name": body.name,
            "rut": body.rut,
            "profile": body.profile,
            "summary": body.summary,
            "missing": body.missing,
            "worker_id": body.worker_id,
            "ts": datetime.now(timezone.utc).isoformat(),
        },
        force=body.force,
        kind="manual",
    )


@router.post("/test")
def notifications_test() -> dict[str, Any]:
    return notif_mod.send_notification(
        {
            "name": "Prueba VigiEPP",
            "rut": "11.111.111-1",
            "profile": "general",
            "summary": "Esta es una notificación de prueba",
            "missing": ["casco"],
            "worker_id": "test",
            "ts": datetime.now(timezone.utc).isoformat(),
        },
        force=True,
        kind="test",
    )


@router.post("/hardware/test")
def notifications_hardware_test(body: HardwareTestBody) -> dict[str, Any]:
    """Dispara /alarma o /ok en el ESP32 (misma red que el servidor VigiEPP)."""
    return notif_mod.test_hardware(body.action or "alarma")


