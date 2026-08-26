"""Endpoints privacidad y retención de evidencia."""

from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter
from pydantic import BaseModel, Field

from .. import audit as audit_mod
from .. import privacy as privacy_mod

router = APIRouter(prefix="/api/privacy", tags=["privacy"])


class PrivacyPatchBody(BaseModel):
    qr_only_mode: Optional[bool] = None
    retention_days: Optional[int] = Field(None, ge=7, le=365)


@router.get("/config")
def privacy_config_get() -> dict[str, Any]:
    return {"ok": True, "config": privacy_mod.get_config()}


@router.post("/config")
def privacy_config_save(body: PrivacyPatchBody) -> dict[str, Any]:
    patch = body.model_dump(exclude_none=True)
    cfg = privacy_mod.save_config(patch)
    audit_mod.log("privacy_config", detail=str(patch)[:200])
    return {"ok": True, "config": cfg}


@router.post("/retention/run")
def privacy_retention_run() -> dict[str, Any]:
    result = privacy_mod.apply_retention()
    audit_mod.log("privacy_retention", detail=str(result.get("evidence_removed", 0)))
    return {"ok": True, "result": result}
