"""FastAPI standalone — VigiEPP Forense (puerto 8001 por defecto)."""

from __future__ import annotations

import logging
from pathlib import Path

from fastapi import Depends, FastAPI, File, Form, HTTPException, Request, Response, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, PlainTextResponse
from pydantic import BaseModel, Field

from .auth_bridge import login_pin, require_forense_admin
from .config import BUILD, MAX_UPLOAD_MB, WEB_DIR, ensure_dirs
from .jobs import create_job, delete_job, get_job, keyframe_path, list_jobs
from .license import license_status, verify_license

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("vigiepp.forense")

app = FastAPI(
    title="VigiEPP Forense",
    description="Análisis forense de video e informes IA de incidentes (producto aislado)",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:8001", "http://localhost:8001"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _require_license() -> None:
    ok, msg = verify_license()
    if not ok:
        raise HTTPException(402, msg)


class LoginBody(BaseModel):
    pin: str = Field(..., min_length=1, max_length=128)


@app.get("/api/forense/health")
def health() -> dict:
    lic = license_status()
    return {
        "status": "ok",
        "product": "VigiEPP Forense",
        "build": BUILD,
        "license": lic,
        "isolated": True,
        "vigiepp_core": "untouched",
    }


@app.post("/api/forense/auth/login")
def auth_login(body: LoginBody, request: Request, response: Response) -> dict:
    _require_license()
    return login_pin(request, response, body.pin)


@app.get("/api/forense/auth/me")
def auth_me(request: Request) -> dict:
    _require_license()
    role = require_forense_admin(request)
    return {"ok": True, "role": role}


@app.get("/api/forense/jobs")
def jobs_list(request: Request) -> dict:
    _require_license()
    require_forense_admin(request)
    jobs = [
        {
            "id": j["id"],
            "title": j.get("title"),
            "status": j.get("status"),
            "progress": j.get("progress"),
            "progress_message": j.get("progress_message"),
            "created_at": j.get("created_at"),
            "event_count": (j.get("analysis") or {}).get("event_count", 0),
        }
        for j in list_jobs()
    ]
    return {"ok": True, "jobs": jobs}


@app.post("/api/forense/jobs")
async def jobs_create(
    request: Request,
    video: UploadFile = File(...),
    title: str = Form(""),
    site: str = Form(""),
    profile: str = Form("epp_completo"),
    meters_per_pixel: float = Form(0.045),
) -> dict:
    _require_license()
    require_forense_admin(request)
    data = await video.read()
    max_b = MAX_UPLOAD_MB * 1024 * 1024
    if len(data) > max_b:
        raise HTTPException(413, f"Video supera {MAX_UPLOAD_MB} MB")
    if len(data) < 1000:
        raise HTTPException(400, "Archivo de video vacío o inválido")
    job = create_job(
        data,
        filename=video.filename or "video.mp4",
        title=title,
        site=site,
        profile=profile,
        meters_per_pixel=max(0.01, min(0.5, meters_per_pixel)),
    )
    return {"ok": True, "job": {"id": job["id"], "status": job["status"]}}


@app.get("/api/forense/jobs/{job_id}")
def jobs_get(job_id: str, request: Request) -> dict:
    _require_license()
    require_forense_admin(request)
    job = get_job(job_id)
    if not job:
        raise HTTPException(404, "Trabajo no encontrado")
    return {
        "ok": True,
        "job": {
            "id": job["id"],
            "title": job.get("title"),
            "site": job.get("site"),
            "status": job.get("status"),
            "progress": job.get("progress"),
            "progress_message": job.get("progress_message"),
            "meta": job.get("meta"),
            "analysis": job.get("analysis"),
            "error": job.get("error"),
            "meters_per_pixel": job.get("meters_per_pixel"),
        },
    }


@app.get("/api/forense/jobs/{job_id}/report.md")
def jobs_report_md(job_id: str, request: Request) -> PlainTextResponse:
    _require_license()
    require_forense_admin(request)
    job = get_job(job_id)
    if not job:
        raise HTTPException(404, "Trabajo no encontrado")
    md = job.get("report_md") or ""
    return PlainTextResponse(md, media_type="text/markdown; charset=utf-8")


@app.get("/api/forense/jobs/{job_id}/keyframes/{name}")
def jobs_keyframe(job_id: str, name: str, request: Request) -> FileResponse:
    _require_license()
    require_forense_admin(request)
    path = keyframe_path(job_id, name)
    if not path:
        raise HTTPException(404, "Captura no encontrada")
    return FileResponse(path, media_type="image/jpeg")


@app.delete("/api/forense/jobs/{job_id}")
def jobs_delete(job_id: str, request: Request) -> dict:
    _require_license()
    require_forense_admin(request)
    if not delete_job(job_id):
        raise HTTPException(404, "Trabajo no encontrado")
    return {"ok": True}


@app.on_event("startup")
def startup() -> None:
    ensure_dirs()
    ok, detail = verify_license()
    logger.info("VigiEPP Forense %s — licencia: %s (%s)", BUILD, ok, detail)


@app.get("/", response_class=HTMLResponse)
def index() -> HTMLResponse:
    html_path = WEB_DIR / "index.html"
    if not html_path.is_file():
        return HTMLResponse("<h1>VigiEPP Forense</h1><p>UI no encontrada</p>")
    return HTMLResponse(
        html_path.read_text(encoding="utf-8"),
        headers={"Cache-Control": "no-store"},
    )


@app.get("/forense.css")
def forense_css() -> FileResponse:
    return FileResponse(WEB_DIR / "forense.css", media_type="text/css")


@app.get("/forense.js")
def forense_js() -> FileResponse:
    return FileResponse(WEB_DIR / "forense.js", media_type="application/javascript")
