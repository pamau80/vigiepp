"""API conectores EHS."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from .. import audit as audit_mod
from .. import ehs_connectors as ehs_mod

router = APIRouter(prefix="/api/ehs", tags=["ehs"])


class EHSConfigBody(BaseModel):
    connectors: dict[str, dict[str, Any]] = Field(default_factory=dict)


class EHSPushBody(BaseModel):
    worker_name: str = "—"
    worker_rut: str = ""
    worker_id: str = ""
    profile: str = "general"
    compliant: bool = False
    summary: str = ""
    missing: list[str] = Field(default_factory=list)
    evidence_id: str | None = None
    site: str = ""


@router.get("/config")
def ehs_config_get() -> dict[str, Any]:
    return {"ok": True, "config": ehs_mod.get_config()}


@router.post("/config")
def ehs_config_save(body: EHSConfigBody) -> dict[str, Any]:
    cfg = ehs_mod.save_config(body.model_dump())
    audit_mod.log("ehs_config", detail=str(len(body.connectors)))
    return {"ok": True, "config": cfg}


@router.post("/test/{connector_id}")
def ehs_test(connector_id: str) -> dict[str, Any]:
    result = ehs_mod.test_connector(connector_id)
    if not result.get("ok"):
        raise HTTPException(400, result.get("error") or result.get("detail") or "Falló")
    return {"ok": True, **result}


@router.post("/push")
def ehs_push(body: EHSPushBody) -> dict[str, Any]:
    incident = body.model_dump()
    results = ehs_mod.push_incident(incident)
    audit_mod.log("ehs_push", detail=body.summary[:120])
    return {"ok": True, "results": results}
