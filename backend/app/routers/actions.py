from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Request

from .. import actions as actions_mod
from .. import watchlist as watchlist_mod
from .. import zones as zones_mod

router = APIRouter(prefix="/api/actions", tags=["actions"])


@router.get("/rules")
def actions_get_rules() -> dict[str, Any]:
    data = actions_mod.get_rules()
    data["settings"] = actions_mod.get_settings()
    return data


@router.get("/settings")
def actions_get_settings() -> dict[str, Any]:
    return {"settings": actions_mod.get_settings()}


@router.post("/settings")
async def actions_save_settings(request: Request) -> dict[str, Any]:
    body = await request.json()
    settings = body.get("settings") if isinstance(body, dict) else body
    if not isinstance(settings, dict):
        raise HTTPException(400, "Se esperaba { settings: {...} }")
    return actions_mod.save_settings(settings)


@router.get("/sources")
def actions_list_sources() -> dict[str, Any]:
    sources = [{"id": "live", "label": "Vivo / portería"}]
    try:
        for ch in watchlist_mod.list_channels():
            if not ch.get("enabled", True):
                continue
            cid = ch.get("id") or ""
            sources.append(
                {
                    "id": f"watchlist:{cid}",
                    "label": ch.get("name") or f"Canal {cid}",
                }
            )
    except Exception:  # noqa: BLE001
        pass
    zone_src = zones_mod.list_zone_sources()
    return {"sources": sources, "zone_sources": zone_src}


@router.get("/presets")
def actions_presets() -> dict[str, Any]:
    return {"presets": actions_mod.list_presets()}


@router.post("/rules")
async def actions_save_rules(request: Request) -> dict[str, Any]:
    body = await request.json()
    rules = body.get("rules") if isinstance(body, dict) else body
    if not isinstance(rules, list):
        raise HTTPException(400, "Se esperaba { rules: [...] }")
    payload = actions_mod.save_rules(rules)
    payload["settings"] = actions_mod.get_settings()
    return payload


@router.post("/presets/{preset_id}")
def actions_add_preset(preset_id: str) -> dict[str, Any]:
    try:
        return actions_mod.add_rule_from_preset(preset_id)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc


@router.post("/rules/reset")
def actions_reset_defaults() -> dict[str, Any]:
    from ..actions import _default_payload, save_rules

    payload = _default_payload()
    save_rules(payload["rules"])
    actions_mod.save_settings(payload["settings"])
    return actions_mod.get_rules() | {"settings": actions_mod.get_settings()}


@router.get("/events")
def actions_list_events(
    limit: int = 100,
    severity: str | None = None,
    source_id: str | None = None,
) -> dict[str, Any]:
    events = actions_mod.list_action_events(limit=limit, severity=severity, source_id=source_id)
    return {"ok": True, "events": events, "count": len(events)}
