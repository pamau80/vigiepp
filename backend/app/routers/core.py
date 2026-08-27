from __future__ import annotations

import os
from typing import Any

from fastapi import APIRouter
from fastapi.responses import PlainTextResponse

from .. import auth as auth_mod
from .. import inference as inference_mod
from .. import metrics as metrics_mod
from .. import notifications as notif_mod
from .. import oidc as oidc_mod
from .. import paths as paths_mod
from .. import privacy as privacy_mod
from .. import tenants as tenants_mod
from ..detector import PPEDetector
from ..identity import IdentityRegistry
from ..profiles import list_profiles, PPE_CATALOG

router = APIRouter(prefix="/api", tags=["core"])

BUILD_VERSION = "v47"


@router.get("/health")
def health() -> dict[str, Any]:
    det = PPEDetector.peek()
    reg = IdentityRegistry.peek()
    from .. import cloud_persist as cloud_mod

    cloud = cloud_mod.status()
    on_render = bool(os.getenv("RENDER") or os.getenv("RENDER_SERVICE_ID"))
    ephemeral_flag = os.getenv("VIGIEPP_EPHEMERAL", "").strip().lower() in ("1", "true", "yes")
    durable = bool(cloud.get("configured"))
    data_persistent = durable or (paths_mod.is_persistent() and not ephemeral_flag and not on_render) or (
        paths_mod.is_persistent() and os.getenv("VIGIEPP_EPHEMERAL", "").strip() in ("0", "false", "no")
    )
    if durable:
        data_persistent = True
    ephemeral_risk = on_render and not durable and ephemeral_flag
    if on_render and not durable and os.getenv("VIGIEPP_EPHEMERAL", "1").strip() not in ("0", "false", "no"):
        ephemeral_risk = True
        data_persistent = False
    gallery_size = 0
    workers_ready = 0
    if reg is not None:
        for w in reg.list_workers():
            ec = int(w.get("embedding_count") or 0)
            gallery_size += ec
            if w.get("ready"):
                workers_ready += 1
    identity_ready = reg is not None
    epp_ready = bool(det and det.ready)
    combined = inference_mod.combined_inference_enabled()
    active_site = tenants_mod.get_site(tenants_mod.get_active_site_id())
    privacy_cfg = privacy_mod.get_config()
    pin_warn = bool(auth_mod.using_default_pins() and on_render)
    from ..stream_rtsp import active_stream_count

    return {
        "status": "ok",
        "product": "VigiEPP",
        "build": BUILD_VERSION,
        "model_ready": epp_ready,
        "identity_ready": identity_ready,
        "combined_inference": combined,
        "gallery_size": gallery_size,
        "workers_ready": workers_ready,
        "model": (det.model_name if det else "") or ("EPP bajo demanda" if not epp_ready else ""),
        "warning": (det.error if det else None) or (None if identity_ready else "Cargando identidad…"),
        "booting": not identity_ready and not epp_ready,
        "auth_enabled": auth_mod.auth_enabled(),
        "oidc": oidc_mod.public_config(),
        "active_site": active_site,
        "privacy": privacy_cfg,
        "data_dir": str(paths_mod.data_dir()),
        "data_persistent": bool(data_persistent),
        "data_ephemeral_risk": bool(ephemeral_risk and not durable),
        "cloud_backup": cloud,
        "production_pin_warning": pin_warn,
        "rtsp_streams_active": active_stream_count(),
        "email_transport": notif_mod.email_transport_status().get("mode"),
    }


@router.get("/profiles")
def profiles() -> list[dict[str, Any]]:
    return list_profiles()


@router.get("/ppe/catalog")
def ppe_catalog() -> dict[str, Any]:
    return {"items": PPE_CATALOG}

metrics_router = APIRouter(tags=["metrics"])


@metrics_router.get("/metrics")
def metrics_prometheus() -> PlainTextResponse:
    from ..stream_rtsp import active_stream_count

    extra = {"rtsp_streams_active": active_stream_count()}
    return PlainTextResponse(metrics_mod.prometheus_text(extra), media_type="text/plain; version=0.0.4")
