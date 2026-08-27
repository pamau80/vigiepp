"""API VigiEPP — factory FastAPI modular."""

from __future__ import annotations

import logging
import os
import threading
import time
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles

from . import auth as auth_mod
from . import privacy as privacy_mod
from .detector import PPEDetector
from .identity import IdentityRegistry
from .routers import register_routers
from .routers.core import BUILD_VERSION
from .request_limits import MaxBodySizeMiddleware
from .security_headers import SecurityHeadersMiddleware
from .startup_checks import run_startup_security_checks
from .stream_rtsp import stop_all

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s: %(message)s")
logger = logging.getLogger("vigiepp")

FRONTEND_DIR = Path(__file__).resolve().parents[2] / "frontend"


@asynccontextmanager
async def lifespan(_: FastAPI):
    def _warm() -> None:
        try:
            from . import cloud_persist as cloud_mod

            if cloud_mod.configured():
                result = cloud_mod.hydrate(force=True)
            else:
                result = cloud_mod.pull_and_restore_if_empty()
            if result.get("restored"):
                logger.info("Identidad restaurada desde volumen durable: %s", result.get("workers"))
        except Exception:  # noqa: BLE001
            logger.exception("Durable persist pull falló")
        try:
            IdentityRegistry.get()
            logger.info("Identidad facial precargada")
        except Exception:  # noqa: BLE001
            logger.exception("Precarga de identidad facial falló")

        def _lazy_yolo() -> None:
            time.sleep(10)
            try:
                PPEDetector.get()
                logger.info("Modelo EPP precargado (lazy, post-identidad)")
            except Exception:  # noqa: BLE001
                logger.exception("Precarga lazy EPP falló")

        threading.Thread(target=_lazy_yolo, name="epp-lazy", daemon=True).start()
        try:
            privacy_mod.apply_retention()
        except Exception:  # noqa: BLE001
            logger.exception("Retención inicial falló")

    threading.Thread(target=_warm, name="vigiepp-warm", daemon=True).start()
    run_startup_security_checks()
    yield
    stop_all()


_docs = "/docs" if auth_mod.docs_enabled() else None
app = FastAPI(
    title="VigiEPP",
    description="Detección de EPP con IA — demo para faenas en Chile",
    version="0.3.0",
    lifespan=lifespan,
    docs_url=_docs,
    redoc_url=_docs and "/redoc",
    openapi_url="/openapi.json" if auth_mod.docs_enabled() else None,
)

_cors_raw = os.getenv("VIGIEPP_CORS_ORIGINS", "").strip()
if _cors_raw:
    _cors_origins = [o.strip() for o in _cors_raw.split(",") if o.strip()]
    _cors_credentials = "*" not in _cors_origins
else:
    _cors_origins = []
    _cors_credentials = False

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins if _cors_origins else ["http://127.0.0.1:8000", "http://localhost:8000"],
    allow_credentials=_cors_credentials,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)
app.add_middleware(MaxBodySizeMiddleware)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(auth_mod.AuthMiddleware)

register_routers(app)

if FRONTEND_DIR.exists():
    app.mount("/assets", StaticFiles(directory=FRONTEND_DIR / "assets"), name="assets")

    @app.get("/favicon.ico", include_in_schema=False)
    async def favicon() -> FileResponse:
        png = FRONTEND_DIR / "assets" / "favicon.png"
        ico = FRONTEND_DIR / "favicon.ico"
        path = png if png.exists() else ico
        return FileResponse(path)

    @app.get("/", response_class=HTMLResponse)
    async def index() -> HTMLResponse:
        html = (FRONTEND_DIR / "index.html").read_text(encoding="utf-8")
        return HTMLResponse(
            html,
            headers={
                "Cache-Control": "no-store, no-cache, must-revalidate",
                "Pragma": "no-cache",
            },
        )
else:

    @app.get("/")
    async def index_fallback() -> dict[str, str]:
        return {"message": "Frontend no encontrado. Crea la carpeta frontend/"}


def create_app() -> FastAPI:
    return app
