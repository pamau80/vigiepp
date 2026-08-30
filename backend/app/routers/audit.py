from __future__ import annotations

from typing import Any

from fastapi import APIRouter
from fastapi.responses import Response

from .. import audit as audit_mod

router = APIRouter(prefix="/api/audit", tags=["audit"])


@router.get("")
def audit_recent(limit: int = 80) -> dict[str, Any]:
    return {"ok": True, "events": audit_mod.recent(limit=limit)}


@router.get("/export.csv")
def audit_export_csv(limit: int = 500) -> Response:
    content = audit_mod.export_csv(limit=max(1, min(2000, limit)))
    return Response(
        content=content.encode("utf-8-sig"),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": "attachment; filename=\"vigiepp-audit.csv\""},
    )
