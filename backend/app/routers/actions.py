from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Request

from .. import actions as actions_mod

router = APIRouter(prefix="/api/actions", tags=["actions"])


@router.get("/rules")
def actions_get_rules() -> dict[str, Any]:
    return actions_mod.get_rules()


@router.get("/presets")
def actions_presets() -> dict[str, Any]:
    return {"presets": actions_mod.list_presets()}


@router.post("/rules")
async def actions_save_rules(request: Request) -> dict[str, Any]:
    body = await request.json()
    rules = body.get("rules") if isinstance(body, dict) else body
    if not isinstance(rules, list):
        raise HTTPException(400, "Se esperaba { rules: [...] }")
    return actions_mod.save_rules(rules)


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
    return payload
