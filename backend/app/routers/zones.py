from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Request

from .. import zones as zones_mod

router = APIRouter(prefix="/api/zones", tags=["zones"])

@router.get("")
def zones_get() -> dict[str, Any]:
    return zones_mod.get_zones()


@router.get("/presets")
def zones_presets() -> dict[str, Any]:
    return {"presets": zones_mod.list_presets()}


@router.post("/presets/{preset_id}")
def zones_apply_preset(preset_id: str) -> dict[str, Any]:
    try:
        return zones_mod.apply_preset(preset_id)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc


@router.post("")
async def zones_save(request: Request) -> dict[str, Any]:
    body = await request.json()
    zones = body.get("zones") if isinstance(body, dict) else body
    if not isinstance(zones, list):
        raise HTTPException(400, "Se esperaba { zones: [...] }")
    return zones_mod.save_zones(zones)


