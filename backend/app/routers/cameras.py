from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter

router = APIRouter(prefix="/api/cameras", tags=['cameras'])

from fastapi import HTTPException
from pydantic import BaseModel

class CameraBody(BaseModel):
    name: str = ""
    url: str
    id: str | None = None

@router.get("")
def cameras_list() -> dict[str, Any]:
    from .. import cameras as cameras_mod

    return {"ok": True, "cameras": cameras_mod.list_cameras(), "max": cameras_mod.MAX_CAMERAS}


@router.post("")
def cameras_upsert(body: CameraBody) -> dict[str, Any]:
    from .. import audit as audit_mod
    from .. import cameras as cameras_mod

    try:
        cam = cameras_mod.upsert(body.name, body.url, body.id)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    audit_mod.log("camera_upsert", detail=cam.get("name") or cam.get("id"))
    return {"ok": True, "camera": cam}


@router.delete("/{camera_id}")
def cameras_delete(camera_id: str) -> dict[str, Any]:
    from .. import audit as audit_mod
    from .. import cameras as cameras_mod

    ok = cameras_mod.delete(camera_id)
    if not ok:
        raise HTTPException(404, "Cámara no encontrada")
    audit_mod.log("camera_delete", detail=camera_id)
    return {"ok": True, "deleted": camera_id}


# ── NVR / DVR (Dahua, Hikvision, Uniview) ───────────────────────────────────


