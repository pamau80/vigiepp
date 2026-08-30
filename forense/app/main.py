"""FastAPI standalone — VigiEPP Forense (puerto 8001 por defecto)."""

from __future__ import annotations

import logging

from fastapi import FastAPI, File, Form, HTTPException, Request, Response, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, PlainTextResponse
from pydantic import BaseModel, Field

from .auth_bridge import auth_status_payload, login_pin, require_forense_admin
from .config import (
    BUILD,
    DEFAULT_MAX_MACHINERY_KMH,
    DEFAULT_MAX_PERSON_KMH,
    DEFAULT_MIN_DISTANCE_M,
    MAX_UPLOAD_MB,
    ROOT,
    WEB_DIR,
    ensure_dirs,
)
from .jobs import (
    case_bundle_path,
    committee_md_path,
    create_job,
    delete_job,
    export_job_ehs,
    get_job,
    heatmap_path,
    keyframe_path,
    list_jobs,
    report_pdf_path,
)
from .license import license_status, verify_license
from .templates import list_templates

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("vigiepp.forense")

app = FastAPI(
    title="VigiEPP Forense",
    description="Análisis forense de video e informes IA de incidentes (producto aislado)",
    version="0.2.0",
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


async def _read_upload(video: UploadFile | None, label: str) -> dict | None:
    if video is None or not video.filename:
        return None
    data = await video.read()
    max_b = MAX_UPLOAD_MB * 1024 * 1024
    if len(data) > max_b:
        raise HTTPException(413, f"{label} supera {MAX_UPLOAD_MB} MB")
    if len(data) < 1000:
        raise HTTPException(400, f"Archivo {label} vacío o inválido")
    return {"bytes": data, "filename": video.filename}


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


@app.get("/api/forense/auth/status")
def auth_status(request: Request) -> dict:
    _require_license()
    return auth_status_payload(request)


@app.get("/api/forense/auth/me")
def auth_me(request: Request) -> dict:
    _require_license()
    payload = auth_status_payload(request)
    if not payload.get("can_access"):
        raise HTTPException(401, "No autorizado. Ingresá con PIN administrador.")
    return {"ok": True, "role": payload.get("role")}


@app.get("/api/forense/templates")
def templates_list(request: Request) -> dict:
    _require_license()
    require_forense_admin(request)
    return {"ok": True, "templates": list_templates()}


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
            "template_id": j.get("template_id"),
            "event_count": (j.get("analysis") or {}).get("event_count", 0),
        }
        for j in list_jobs()
    ]
    return {"ok": True, "jobs": jobs}


@app.post("/api/forense/jobs")
async def jobs_create(
    request: Request,
    video: UploadFile = File(...),
    video2: UploadFile | None = File(None),
    video3: UploadFile | None = File(None),
    title: str = Form(""),
    site: str = Form(""),
    template_id: str = Form("general"),
    profile: str = Form(""),
    meters_per_pixel: float | None = Form(None),
    max_machinery_kmh: float | None = Form(None),
    max_person_kmh: float | None = Form(None),
    min_distance_m: float | None = Form(None),
    reference_job_id: str = Form(""),
    offset2: float = Form(0.0),
    offset3: float = Form(0.0),
) -> dict:
    _require_license()
    require_forense_admin(request)
    primary = await _read_upload(video, "Video principal")
    assert primary is not None

    extra_sources: list[dict] = []
    for extra_file, off in ((video2, offset2), (video3, offset3)):
        extra = await _read_upload(extra_file, "Video adicional")
        if extra:
            extra["offset_sec"] = float(off)
            extra_sources.append(extra)

    ref_id = reference_job_id.strip() or None
    if ref_id and not get_job(ref_id):
        raise HTTPException(400, "Trabajo de referencia no encontrado")

    job = create_job(
        primary["bytes"],
        filename=primary["filename"] or "video.mp4",
        title=title,
        site=site,
        template_id=template_id,
        profile=profile or None,
        meters_per_pixel=max(0.01, min(0.5, meters_per_pixel)) if meters_per_pixel is not None else None,
        max_machinery_kmh=max(1.0, min(80.0, max_machinery_kmh)) if max_machinery_kmh is not None else None,
        max_person_kmh=max(1.0, min(30.0, max_person_kmh)) if max_person_kmh is not None else None,
        min_distance_m=max(0.5, min(20.0, min_distance_m)) if min_distance_m is not None else None,
        reference_job_id=ref_id,
        extra_sources=extra_sources or None,
    )
    return {"ok": True, "job": {"id": job["id"], "status": job["status"]}}


def _job_payload(job: dict) -> dict:
    analysis = job.get("analysis") or {}
    return {
        "id": job["id"],
        "title": job.get("title"),
        "site": job.get("site"),
        "status": job.get("status"),
        "progress": job.get("progress"),
        "progress_message": job.get("progress_message"),
        "meta": job.get("meta"),
        "analysis": analysis,
        "comparison": job.get("comparison"),
        "error": job.get("error"),
        "template_id": job.get("template_id"),
        "template_name": job.get("template_name"),
        "reference_job_id": job.get("reference_job_id"),
        "sources": job.get("sources"),
        "meters_per_pixel": job.get("meters_per_pixel"),
        "max_machinery_kmh": job.get("max_machinery_kmh"),
        "max_person_kmh": job.get("max_person_kmh"),
        "min_distance_m": job.get("min_distance_m"),
        "has_heatmap": bool(analysis.get("heatmap")),
        "has_pdf": report_pdf_path(job["id"]) is not None,
        "has_bundle": case_bundle_path(job["id"]) is not None,
        "has_committee": committee_md_path(job["id"]) is not None,
        "ehs_push": job.get("ehs_push"),
    }


@app.get("/api/forense/jobs/{job_id}")
def jobs_get(job_id: str, request: Request) -> dict:
    _require_license()
    require_forense_admin(request)
    job = get_job(job_id)
    if not job:
        raise HTTPException(404, "Trabajo no encontrado")
    return {"ok": True, "job": _job_payload(job)}


@app.get("/api/forense/jobs/{job_id}/charts")
def jobs_charts(job_id: str, request: Request) -> JSONResponse:
    _require_license()
    require_forense_admin(request)
    job = get_job(job_id)
    if not job:
        raise HTTPException(404, "Trabajo no encontrado")
    series = (job.get("analysis") or {}).get("speed_series") or []
    return JSONResponse({"ok": True, "speed_series": series})


@app.get("/api/forense/jobs/{job_id}/report.md")
def jobs_report_md(job_id: str, request: Request) -> PlainTextResponse:
    _require_license()
    require_forense_admin(request)
    job = get_job(job_id)
    if not job:
        raise HTTPException(404, "Trabajo no encontrado")
    md = job.get("report_md") or ""
    return PlainTextResponse(md, media_type="text/markdown; charset=utf-8")


@app.get("/api/forense/jobs/{job_id}/committee.md")
def jobs_committee_md(job_id: str, request: Request) -> PlainTextResponse:
    _require_license()
    require_forense_admin(request)
    path = committee_md_path(job_id)
    if not path:
        job = get_job(job_id)
        if not job:
            raise HTTPException(404, "Trabajo no encontrado")
        md = job.get("committee_md") or ""
        if not md:
            raise HTTPException(404, "Informe comité no disponible")
        return PlainTextResponse(md, media_type="text/markdown; charset=utf-8")
    return PlainTextResponse(path.read_text(encoding="utf-8"), media_type="text/markdown; charset=utf-8")


@app.get("/api/forense/jobs/{job_id}/report.pdf")
def jobs_report_pdf(job_id: str, request: Request) -> FileResponse:
    _require_license()
    require_forense_admin(request)
    path = report_pdf_path(job_id)
    if not path:
        raise HTTPException(404, "PDF no disponible")
    return FileResponse(path, media_type="application/pdf", filename=f"forense-{job_id}.pdf")


@app.get("/api/forense/jobs/{job_id}/case_bundle.zip")
def jobs_case_bundle(job_id: str, request: Request) -> FileResponse:
    _require_license()
    require_forense_admin(request)
    path = case_bundle_path(job_id)
    if not path:
        raise HTTPException(404, "Bundle no disponible")
    return FileResponse(path, media_type="application/zip", filename=f"forense-case-{job_id}.zip")


@app.post("/api/forense/jobs/{job_id}/export-ehs")
def jobs_export_ehs(job_id: str, request: Request) -> dict:
    _require_license()
    require_forense_admin(request)
    results = export_job_ehs(job_id)
    if results and results[0].get("error") == "Trabajo no encontrado":
        raise HTTPException(404, "Trabajo no encontrado")
    return {"ok": True, "results": results}


@app.get("/api/forense/jobs/{job_id}/heatmap.jpg")
def jobs_heatmap(job_id: str, request: Request) -> FileResponse:
    _require_license()
    require_forense_admin(request)
    path = heatmap_path(job_id)
    if not path:
        raise HTTPException(404, "Mapa de calor no disponible")
    return FileResponse(path, media_type="image/jpeg")


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


@app.get("/favicon.ico", include_in_schema=False)
def favicon() -> FileResponse:
    for candidate in (
        ROOT / "frontend" / "assets" / "favicon.png",
        ROOT / "frontend" / "favicon.ico",
        WEB_DIR / "favicon.ico",
    ):
        if candidate.is_file():
            media = "image/png" if candidate.suffix == ".png" else "image/x-icon"
            return FileResponse(candidate, media_type=media)
    raise HTTPException(404, "favicon no encontrado")
