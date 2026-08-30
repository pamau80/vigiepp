from __future__ import annotations

from typing import Any

from fastapi import APIRouter

router = APIRouter(prefix="/api/watchlist", tags=['watchlist'])

from fastapi import HTTPException
from pydantic import BaseModel, Field


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

