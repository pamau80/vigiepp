from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Request

from .. import zones as zones_mod

router = APIRouter(prefix="/api/zones", tags=["zones"])

@router.get("")
def zones_get(source_id: str = "") -> dict[str, Any]:
    data = zones_mod.get_zones()
    if source_id:
        sid = source_id.strip()
        by_src = data.get("by_source") or {}
        zones = by_src.get(sid) if sid in by_src else data.get("zones") or []
        return {"zones": zones, "source_id": sid or "live", "by_source": data.get("by_source") or {}}
    return data


@router.get("/sources")
def zones_sources() -> dict[str, Any]:
    return {"sources": zones_mod.list_zone_sources()}


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
    source_id = body.get("source_id") if isinstance(body, dict) else None
    if not isinstance(zones, list):
        raise HTTPException(400, "Se esperaba { zones: [...] }")
    return zones_mod.save_zones(zones, source_id=source_id)


