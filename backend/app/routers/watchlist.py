from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter

router = APIRouter(prefix="/api/watchlist", tags=['watchlist'])

from fastapi import HTTPException
from pydantic import BaseModel, Field
from typing import Any

class WatchChannelBody(BaseModel):
    name: str = ""
    url: str
    id: str | None = None
    vendor: str = ""
    nvr_id: str = ""
    channel: int | None = None
    enabled: bool = True

class WatchImportBody(BaseModel):
    channels: list[dict[str, Any]] = Field(default_factory=list)
    replace: bool = False

@router.get("")
def watchlist_list() -> dict[str, Any]:
    from .. import watchlist as watch_mod

    return {"ok": True, "channels": watch_mod.list_channels(), "max": watch_mod.MAX_WATCH}


@router.post("")
def watchlist_upsert(body: WatchChannelBody) -> dict[str, Any]:
    from .. import watchlist as watch_mod

    try:
        ch = watch_mod.upsert(
            body.name,
            body.url,
            channel_id=body.id,
            vendor=body.vendor,
            nvr_id=body.nvr_id,
            channel_num=body.channel,
            enabled=body.enabled,
        )
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    return {"ok": True, "channel": ch}


@router.post("/import")
def watchlist_import(body: WatchImportBody) -> dict[str, Any]:
    from .. import watchlist as watch_mod

    try:
        channels = watch_mod.import_channels(body.channels, replace=body.replace)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    return {"ok": True, "channels": channels, "max": watch_mod.MAX_WATCH}


@router.delete("/{channel_id}")
def watchlist_delete(channel_id: str) -> dict[str, Any]:
    from .. import watchlist as watch_mod

    ok = watch_mod.delete(channel_id)
    if not ok:
        raise HTTPException(404, "Canal no encontrado")
    return {"ok": True, "deleted": channel_id}


def _resize_frame(frame: np.ndarray, max_dim: int = 720) -> np.ndarray:
    h, w = frame.shape[:2]
    if max(h, w) <= max_dim:
        return frame
    scale = max_dim / max(h, w)
    return cv2.resize(frame, (int(w * scale), int(h * scale)))


def _thumb_b64(frame: np.ndarray, max_w: int = 320) -> str:
    h, w = frame.shape[:2]
    if w > max_w:
        scale = max_w / w
        frame = cv2.resize(frame, (max_w, int(h * scale)))
    jpeg = encode_jpeg(frame, quality=72)
    return base64.b64encode(jpeg).decode("ascii")


def _compliance_cell_fields(payload: dict[str, Any]) -> dict[str, Any]:
    comp = payload.get("compliance") or {}
    persons = comp.get("persons") or []
    missing: list[str] = []
    for p in persons:
        for m in p.get("missing") or []:
            missing.append(str(m))
    return {
        "compliant": comp.get("overall_compliant"),
        "missing": missing,
        "alerts": comp.get("alerts") or [],
    }


