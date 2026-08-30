"""Registro de routers API."""

from __future__ import annotations

from fastapi import FastAPI

from . import (
    actions,
    audit,
    auth,
    cameras,
    core,
    detect,
    identity,
    notifications,
    nvr,
    privacy,
    reports,
    rtsp,
    scans,
    sites,
    surveillance,
    teach,
    watchlist,
    zones,
)
from .ehs import router as ehs_router


def register_routers(app: FastAPI) -> None:
    app.include_router(core.router)
    app.include_router(core.metrics_router)
    app.include_router(auth.router)
    app.include_router(detect.router)
    app.include_router(zones.router)
    app.include_router(actions.router)
    app.include_router(scans.router)
    app.include_router(reports.router)
    app.include_router(notifications.router)
    app.include_router(rtsp.router)
    app.include_router(cameras.router)
    app.include_router(nvr.router)
    app.include_router(watchlist.router)
    app.include_router(surveillance.router)
    app.include_router(audit.router)
    app.include_router(identity.router)
    app.include_router(teach.router)
    app.include_router(sites.router)
    app.include_router(privacy.router)
    app.include_router(ehs_router)
