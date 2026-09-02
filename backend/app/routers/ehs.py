"""API conectores EHS e incidentes."""

from __future__ import annotations

from typing import Any, Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from .. import audit as audit_mod
from .. import ehs_connectors as ehs_mod
from .. import ehs_incidents as inc_mod

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


class EHSIncidentCreateBody(BaseModel):
    worker_name: str = "—"
    worker_rut: str = ""
    worker_id: str = ""
    profile: str = "general"
    compliant: bool = False
    summary: str = ""
    missing: list[str] = Field(default_factory=list)
    evidence_id: str | None = None
    site: str = ""
    note: str = ""


class EHSIncidentStatusBody(BaseModel):
    status: Literal["open", "closed", "verified"]
    note: str = ""


@router.get("/config")
def ehs_config_get() -> dict[str, Any]:
    return {"ok": True, "config": ehs_mod.get_config()}


@router.post("/config")
def ehs_config_save(body: EHSConfigBody) -> dict[str, Any]:
    cfg = ehs_mod.save_config(body.model_dump())
    audit_mod.log("ehs_config", detail=str(len(body.connectors)))
    return {"ok": True, "config": cfg}


@router.get("/incidents")
def ehs_incidents_list(status: str | None = None, limit: int = 100) -> dict[str, Any]:
    items = inc_mod.list_incidents(status=status, limit=limit)
    return {"ok": True, "incidents": items, "count": len(items)}


@router.post("/incidents")
def ehs_incidents_create(body: EHSIncidentCreateBody) -> dict[str, Any]:
    incident = inc_mod.create_incident(body.model_dump(), source="manual")
    audit_mod.log("ehs_incident_create", detail=incident.get("id", ""))
    return {"ok": True, "incident": incident}


@router.patch("/incidents/{incident_id}")
def ehs_incidents_update(incident_id: str, body: EHSIncidentStatusBody) -> dict[str, Any]:
    try:
        incident = inc_mod.update_incident_status(incident_id, body.status, note=body.note)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    except KeyError as exc:
        raise HTTPException(404, "Incidente no encontrado") from exc
    audit_mod.log("ehs_incident_status", detail=f"{incident_id}:{body.status}")
    return {"ok": True, "incident": incident}


@router.post("/test/{connector_id}")
def ehs_test(connector_id: str) -> dict[str, Any]:
    result = ehs_mod.test_connector(connector_id)
    if not result.get("ok"):
        raise HTTPException(400, result.get("error") or result.get("detail") or "Falló")
    return {"ok": True, **result}


@router.post("/push")
def ehs_push(body: EHSPushBody) -> dict[str, Any]:
    incident_data = body.model_dump()
    results = ehs_mod.push_incident(incident_data)
    items = inc_mod.list_incidents(limit=1)
    created = items[0] if items else None
    audit_mod.log("ehs_push", detail=body.summary[:120])
    return {"ok": True, "results": results, "incident": created}
