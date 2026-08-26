"""Endpoints multi-faena / sitios."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from .. import audit as audit_mod
from .. import site_reload as site_reload_mod
from .. import tenants as tenants_mod

router = APIRouter(prefix="/api", tags=["sites"])


class SiteCreateBody(BaseModel):
    name: str = Field(..., min_length=1, max_length=80)


class SiteActiveBody(BaseModel):
    site_id: str = Field(..., min_length=1, max_length=40)


@router.get("/sites")
def sites_list() -> dict[str, Any]:
    active_id = tenants_mod.get_active_site_id()
    return {
        "sites": tenants_mod.list_sites(),
        "active_site_id": active_id,
        "active_site": tenants_mod.get_site(active_id),
    }


@router.post("/sites")
def sites_create(body: SiteCreateBody) -> dict[str, Any]:
    site = tenants_mod.create_site(body.name)
    return {"ok": True, "site": site}


@router.post("/sites/active")
def sites_set_active(body: SiteActiveBody) -> dict[str, Any]:
    try:
        site = tenants_mod.set_active_site(body.site_id)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    site_reload_mod.reload_site_context()
    audit_mod.log("site_active", detail=site.get("name") or body.site_id)
    return {"ok": True, "site": site, "active_site_id": body.site_id}
