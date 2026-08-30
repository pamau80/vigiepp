from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from ..scanlog import recent_scans

router = APIRouter(prefix="/api", tags=["scans"])

@router.get("/scans/recent")
def scans_recent(limit: int = 15) -> list[dict[str, Any]]:
    return recent_scans(limit=limit)


@router.get("/evidence/{evidence_id}")
def evidence_get(evidence_id: str) -> FileResponse:
    from .. import evidence as evidence_mod

    path = evidence_mod.evidence_path(evidence_id)
    if not path:
        raise HTTPException(404, "Evidencia no encontrada")
    return FileResponse(path, media_type="image/jpeg", filename=f"{evidence_id}.jpg")


