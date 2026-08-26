from __future__ import annotations

from typing import Any

from fastapi import APIRouter

from .. import mass_scan as mass_scan_mod
from .. import metrics as metrics_mod
from .. import watchlist as watch_mod
from ..detect_pipeline import (
    DETECT_IMGSZ_MAX,
    build_response,
    compliance_cell_fields,
    detect_lock,
    thumb_b64,
    validate_rtsp_url,
)

router = APIRouter(prefix="/api/surveillance", tags=["surveillance"])

@router.post("/mass/scan")
def surveillance_mass_scan(
    profile: str = "general",
    conf: float = 0.35,
    required: str = "",
) -> dict[str, Any]:
    """Analiza EPP en todos los canales activos de la watchlist."""
    from .. import mass_scan as mass_scan_mod
    from .. import watchlist as watch_mod

    enabled = [c for c in watch_mod.list_channels() if c.get("enabled")]
    result = mass_scan_mod.run_mass_scan(
        enabled,
        profile=profile,
        conf=conf,
        required=required,
        validate_rtsp_url=validate_rtsp_url,
        detect_lock=detect_lock,
        detect_imgsz_max=DETECT_IMGSZ_MAX,
        build_response=build_response,
        compliance_cell_fields=compliance_cell_fields,
        thumb_b64=thumb_b64,
    )
    metrics_mod.inc("mass_scans_total")
    return result


