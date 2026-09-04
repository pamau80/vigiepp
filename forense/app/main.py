"""FastAPI standalone — VigiEPP Forense (puerto 8001 por defecto)."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Literal

from fastapi import FastAPI, File, Form, HTTPException, Query, Request, Response, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, PlainTextResponse
from pydantic import BaseModel, Field

from .auth_bridge import auth_status_payload, login_pin, logout_session, require_forense_admin
from .config import (
    BUILD,
    DEFAULT_MAX_MACHINERY_KMH,
    DEFAULT_MAX_PERSON_KMH,
    DEFAULT_MIN_DISTANCE_M,
    DOL_API_KEY,
    MAX_UPLOAD_MB,
    ROOT,
    WEB_DIR,
    ensure_dirs,
)
from .frame_store import count_frames, nearest_frame, read_frames
from .jobs import (
    case_bundle_path,
    committee_md_path,
    create_job,
    delete_job,
    dismiss_matching_events,
    export_job_ehs,
    get_job,
    heatmap_path,
    has_job_video,
    job_video_path,
    keyframe_path,
    learn_event_at_timestamp,
    list_jobs,
    report_pdf_path,
    refocus_job,
    reanalyze_job,
    review_event,
)
from .event_feedback import apply_review_state, build_review_audit, delete_suppression_rule, ensure_event_ids, review_summary, suppression_summary
from .report_sections import build_report_sections
from .timeline_evidence import critical_alerts_summary, enrich_timeline_evidence
from .knowledge import (
    SITUATION_TYPES,
    create_knowledge,
    delete_knowledge,
    get_knowledge,
    knowledge_stats,
    list_knowledge,
    promote_job_keyframe,
    reset_knowledge,
)
from .knowledge_import import import_osha, import_seeds, list_import_catalog
from .sources import ingest_url, list_sources_catalog, sync_source, validate_records
from .license import license_status, verify_license
from .teach_bridge import (
    activate_custom_model,
    ensure_custom_model_if_available,
    promote_keyframe_to_teach,
    start_training,
    teach_status,
)
from .templates import list_templates
from .video_formats import SUPPORTED_FORMATS_HINT, is_supported_video_filename

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
    if not is_supported_video_filename(video.filename):
        raise HTTPException(400, f"{label}: formato no soportado. Admitidos: {SUPPORTED_FORMATS_HINT}")
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


@app.post("/api/forense/auth/logout")
def auth_logout(request: Request, response: Response) -> dict:
    _require_license()
    return logout_session(request, response)


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
    case_notes: str = Form(""),
    template_id: str = Form("general"),
    profile: str = Form(""),
    meters_per_pixel: float | None = Form(None),
    max_machinery_kmh: float | None = Form(None),
    max_person_kmh: float | None = Form(None),
    min_distance_m: float | None = Form(None),
    reference_job_id: str = Form(""),
    offset2: float = Form(0.0),
    offset3: float = Form(0.0),
    focus_description: str = Form(""),
    focus_from_sec: float | None = Form(None),
    focus_until_sec: float | None = Form(None),
    strict_detection: str = Form(""),
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
        case_notes=case_notes,
        template_id=template_id,
        profile=profile or None,
        meters_per_pixel=max(0.01, min(0.5, meters_per_pixel)) if meters_per_pixel is not None else None,
        max_machinery_kmh=max(1.0, min(80.0, max_machinery_kmh)) if max_machinery_kmh is not None else None,
        max_person_kmh=max(1.0, min(30.0, max_person_kmh)) if max_person_kmh is not None else None,
        min_distance_m=max(0.5, min(20.0, min_distance_m)) if min_distance_m is not None else None,
        reference_job_id=ref_id,
        extra_sources=extra_sources or None,
        focus_description=focus_description,
        focus_from_sec=focus_from_sec if focus_from_sec is not None and focus_from_sec >= 0 else None,
        focus_until_sec=focus_until_sec if focus_until_sec is not None and focus_until_sec > 0 else None,
        strict_detection=strict_detection.strip().lower() in {"1", "true", "on", "yes", "si", "sí"},
    )
    return {"ok": True, "job": {"id": job["id"], "status": job["status"]}}


def _job_payload(job: dict) -> dict:
    analysis = dict(job.get("analysis") or {})
    feedback = job.get("event_feedback") or {}
    timeline = enrich_timeline_evidence(
        ensure_event_ids(analysis.get("timeline") or []),
        analysis.get("keyframes") or [],
    )
    timeline = apply_review_state(timeline, feedback)
    if timeline:
        analysis = {**analysis, "timeline": timeline, "event_count": len([e for e in timeline if e.get("review_status") != "dismissed"])}
    sources = job.get("sources") or []
    return {
        "id": job["id"],
        "title": job.get("title"),
        "site": job.get("site"),
        "case_notes": job.get("case_notes"),
        "focus_description": job.get("focus_description"),
        "focus_from_sec": job.get("focus_from_sec"),
        "focus_until_sec": job.get("focus_until_sec"),
        "strict_detection": job.get("strict_detection"),
        "video_ai": job.get("video_ai"),
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
        "sources": sources,
        "video_cameras": [
            {"index": i, "label": (s.get("label") or f"Cám. {i + 1}")}
            for i, s in enumerate(sources)
            if has_job_video(job["id"], i)
        ] or ([{"index": 0, "label": "Cám. 1"}] if has_job_video(job["id"], 0) else []),
        "meters_per_pixel": job.get("meters_per_pixel"),
        "max_machinery_kmh": job.get("max_machinery_kmh"),
        "max_person_kmh": job.get("max_person_kmh"),
        "min_distance_m": job.get("min_distance_m"),
        "has_heatmap": bool(analysis.get("heatmap")),
        "has_pdf": report_pdf_path(job["id"]) is not None,
        "has_bundle": case_bundle_path(job["id"]) is not None,
        "has_committee": committee_md_path(job["id"]) is not None,
        "has_video": has_job_video(job["id"]),
        "frames_analyzed": count_frames(job["id"]),
        "ehs_push": job.get("ehs_push"),
        "knowledge": job.get("knowledge"),
        "event_feedback": feedback,
        "review_summary": review_summary(timeline, feedback),
        "critical_alerts": critical_alerts_summary(
            [e for e in timeline if e.get("review_status") != "dismissed"],
            job,
        ),
    }


@app.get("/api/forense/jobs/{job_id}")
def jobs_get(job_id: str, request: Request) -> dict:
    _require_license()
    require_forense_admin(request)
    job = get_job(job_id)
    if not job:
        raise HTTPException(404, "Trabajo no encontrado")
    return {"ok": True, "job": _job_payload(job)}


@app.get("/api/forense/jobs/{job_id}/video")
def jobs_video(job_id: str, request: Request, cam: int = Query(0, ge=0, le=2)) -> FileResponse:
    _require_license()
    require_forense_admin(request)
    if not get_job(job_id):
        raise HTTPException(404, "Trabajo no encontrado")
    path = job_video_path(job_id, cam)
    if not path:
        raise HTTPException(404, "Video no disponible")
    return FileResponse(path, media_type="video/mp4", filename=path.name)


@app.get("/api/forense/jobs/{job_id}/analysis/frames")
def jobs_analysis_frames(
    job_id: str,
    request: Request,
    from_sec: float = Query(0.0, ge=0),
    until_sec: float | None = Query(None, ge=0),
    limit: int = Query(500, ge=1, le=2000),
) -> dict:
    _require_license()
    require_forense_admin(request)
    if not get_job(job_id):
        raise HTTPException(404, "Trabajo no encontrado")
    frames = read_frames(job_id, from_sec=from_sec, until_sec=until_sec, limit=limit)
    return {
        "ok": True,
        "job_id": job_id,
        "from_sec": from_sec,
        "until_sec": until_sec,
        "count": len(frames),
        "frames": frames,
        "total_stored": count_frames(job_id),
    }


@app.get("/api/forense/jobs/{job_id}/analysis/frame-at")
def jobs_frame_at(
    job_id: str,
    request: Request,
    time_sec: float = Query(..., ge=0),
) -> dict:
    _require_license()
    require_forense_admin(request)
    if not get_job(job_id):
        raise HTTPException(404, "Trabajo no encontrado")
    rec = nearest_frame(job_id, time_sec)
    if not rec:
        raise HTTPException(404, "Sin frames analizados aún")
    return {"ok": True, "frame": rec}


class LearnEventBody(BaseModel):
    time_sec: float = Field(..., ge=0)
    title: str = Field(..., min_length=1, max_length=200)
    description: str = Field("", max_length=4000)
    situation_type: str = Field("other", max_length=64)
    industry: str = Field("general", max_length=64)


class RefocusBody(BaseModel):
    focus_description: str = Field("", max_length=4000)
    focus_from_sec: float = Field(..., ge=0)
    focus_until_sec: float = Field(..., gt=0)
    strict_detection: bool | None = None
    camera_index: int = Field(0, ge=0, le=2)
    all_cameras: bool = False


class DismissMatchBody(BaseModel):
    query: str = Field(..., min_length=3, max_length=500)
    note: str = Field("", max_length=500)


@app.post("/api/forense/jobs/{job_id}/refocus")
def jobs_refocus(job_id: str, body: RefocusBody, request: Request) -> dict:
    _require_license()
    require_forense_admin(request)
    if body.focus_until_sec <= body.focus_from_sec:
        raise HTTPException(400, "focus_until_sec debe ser mayor que focus_from_sec")
    try:
        job = refocus_job(
            job_id,
            focus_description=body.focus_description,
            focus_from_sec=body.focus_from_sec,
            focus_until_sec=body.focus_until_sec,
            strict_detection=body.strict_detection,
            camera_index=body.camera_index,
            all_cameras=body.all_cameras,
        )
    except FileNotFoundError as exc:
        raise HTTPException(404, str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(409, str(exc)) from exc
    return {"ok": True, "job": {"id": job["id"], "status": job["status"]}}


@app.post("/api/forense/jobs/{job_id}/reanalyze")
def jobs_reanalyze(job_id: str, request: Request) -> dict:
    _require_license()
    require_forense_admin(request)
    try:
        job = reanalyze_job(job_id)
    except FileNotFoundError as exc:
        raise HTTPException(404, str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(409, str(exc)) from exc
    return {"ok": True, "job": {"id": job["id"], "status": job["status"]}}


class EventReviewBody(BaseModel):
    verdict: Literal["confirmed", "dismissed", "restored"]
    note: str = Field("", max_length=500)


@app.get("/api/forense/suppression-rules")
def suppression_rules_list(request: Request) -> dict:
    _require_license()
    require_forense_admin(request)
    return {"ok": True, **suppression_summary()}


@app.delete("/api/forense/suppression-rules")
def suppression_rules_delete(
    request: Request,
    event_type: str = Query(..., alias="type"),
    rule_id: str = Query(""),
) -> dict:
    _require_license()
    require_forense_admin(request)
    rid = rule_id.strip() or None
    if not delete_suppression_rule(event_type, rid):
        raise HTTPException(404, "Regla no encontrada")
    return {"ok": True, **suppression_summary()}


@app.post("/api/forense/jobs/{job_id}/events/{event_id}/review")
def jobs_review_event(job_id: str, event_id: str, body: EventReviewBody, request: Request) -> dict:
    _require_license()
    role = require_forense_admin(request)
    try:
        job = review_event(job_id, event_id, verdict=body.verdict, note=body.note, reviewed_by=role)
    except FileNotFoundError as exc:
        raise HTTPException(404, str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    return {"ok": True, "job": _job_payload(job)}


@app.post("/api/forense/jobs/{job_id}/events/dismiss-matching")
def jobs_dismiss_matching(job_id: str, body: DismissMatchBody, request: Request) -> dict:
    _require_license()
    role = require_forense_admin(request)
    try:
        job, dismissed = dismiss_matching_events(
            job_id,
            body.query,
            note=body.note,
            reviewed_by=role,
        )
    except FileNotFoundError as exc:
        raise HTTPException(404, str(exc)) from exc
    return {"ok": True, "dismissed_count": len(dismissed), "dismissed_ids": dismissed, "job": _job_payload(job)}


@app.get("/api/forense/jobs/{job_id}/report-sections")
def jobs_report_sections(job_id: str, request: Request) -> dict:
    _require_license()
    require_forense_admin(request)
    job = get_job(job_id)
    if not job:
        raise HTTPException(404, "Trabajo no encontrado")
    return {"ok": True, "report": build_report_sections(job)}


@app.get("/api/forense/jobs/{job_id}/review-audit.json")
def jobs_review_audit(job_id: str, request: Request) -> JSONResponse:
    _require_license()
    require_forense_admin(request)
    job = get_job(job_id)
    if not job:
        raise HTTPException(404, "Trabajo no encontrado")
    payload = {
        "job_id": job_id,
        "title": job.get("title"),
        "site": job.get("site"),
        "exported_at": datetime.now(UTC).isoformat(),
        "entries": build_review_audit(job),
    }
    return JSONResponse(payload)


@app.post("/api/forense/jobs/{job_id}/events/learn")
def jobs_learn_event(job_id: str, body: LearnEventBody, request: Request) -> dict:
    _require_license()
    require_forense_admin(request)
    if not get_job(job_id):
        raise HTTPException(404, "Trabajo no encontrado")
    try:
        entry = learn_event_at_timestamp(
            job_id,
            body.time_sec,
            title=body.title,
            description=body.description,
            situation_type=body.situation_type,
            industry=body.industry,
        )
    except FileNotFoundError as exc:
        raise HTTPException(404, str(exc)) from exc
    return {"ok": True, "entry": entry}


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


class KnowledgeBody(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    situation_type: str = Field("other", max_length=64)
    description: str = Field("", max_length=4000)
    industry: str = Field("general", max_length=64)
    labels: str = Field("", max_length=500)
    event_types: str = Field("", max_length=500)


class KnowledgeResetBody(BaseModel):
    confirm: str = Field(..., min_length=1)


class PromoteKnowledgeBody(BaseModel):
    keyframe_name: str = Field(..., min_length=1)
    title: str = Field(..., min_length=1, max_length=200)
    situation_type: str = Field("other", max_length=64)
    description: str = Field("", max_length=4000)


@app.get("/api/forense/knowledge")
def knowledge_list(request: Request, industry: str | None = None) -> dict:
    _require_license()
    require_forense_admin(request)
    return {
        "ok": True,
        "entries": list_knowledge(industry=industry),
        "stats": knowledge_stats(),
        "situation_types": SITUATION_TYPES,
    }


@app.post("/api/forense/knowledge")
async def knowledge_create(
    request: Request,
    title: str = Form(...),
    situation_type: str = Form("other"),
    description: str = Form(""),
    industry: str = Form("general"),
    labels: str = Form(""),
    event_types: str = Form(""),
    media: UploadFile | None = File(None),
) -> dict:
    _require_license()
    require_forense_admin(request)
    media_bytes = None
    media_filename = None
    if media and media.filename:
        media_bytes = await media.read()
        media_filename = media.filename
    label_list = [x.strip() for x in labels.split(",") if x.strip()]
    event_list = [x.strip() for x in event_types.split(",") if x.strip()]
    entry = create_knowledge(
        title=title,
        situation_type=situation_type,
        description=description,
        industry=industry,
        labels=label_list,
        event_types=event_list,
        media_bytes=media_bytes,
        media_filename=media_filename,
    )
    return {"ok": True, "entry": entry}


@app.delete("/api/forense/knowledge/{entry_id}")
def knowledge_delete(entry_id: str, request: Request) -> dict:
    _require_license()
    require_forense_admin(request)
    if not delete_knowledge(entry_id):
        raise HTTPException(404, "Situación no encontrada")
    return {"ok": True}


@app.post("/api/forense/knowledge/reset")
def knowledge_reset(body: KnowledgeResetBody, request: Request) -> dict:
    _require_license()
    require_forense_admin(request)
    if body.confirm.strip().upper() != "RESETEAR":
        raise HTTPException(400, "Escribí RESETEAR para confirmar")
    removed = reset_knowledge()
    return {"ok": True, "removed": removed}


class KnowledgeImportSeedsBody(BaseModel):
    pack_id: str | None = None
    industry: str | None = None
    limit: int | None = Field(None, ge=1, le=200)
    skip_existing: bool = True


class KnowledgeImportOshaBody(BaseModel):
    keywords: list[str] = Field(default_factory=lambda: ["CRANE", "HOIST", "MARITIME"])
    limit_per_keyword: int = Field(10, ge=1, le=50)
    default_industry: str = "portuario"
    fatality_only: bool = False
    skip_existing: bool = True


class KnowledgeSourceSyncBody(BaseModel):
    source_id: str = Field(..., min_length=1, max_length=64)
    limit: int | None = Field(None, ge=1, le=200)
    skip_existing: bool = True
    fatality_only: bool = False


class KnowledgeSourceSyncIndustryBody(BaseModel):
    industry: str = Field(..., min_length=1, max_length=64)
    limit_per_source: int = Field(15, ge=1, le=50)
    skip_existing: bool = True


class KnowledgeIngestUrlBody(BaseModel):
    url: str = Field(..., min_length=8, max_length=2000)
    title: str = Field("", max_length=200)
    industry: str = Field("general", max_length=64)
    situation_type: str = Field("other", max_length=64)
    tags: list[str] = Field(default_factory=list)
    save: bool = True


class KnowledgeBulkValidateBody(BaseModel):
    records: list[dict] = Field(default_factory=list)
    default_industry: str = Field("general", max_length=64)
    check_duplicates: bool = True


@app.get("/api/forense/knowledge/sources/catalog")
def knowledge_sources_catalog(request: Request) -> dict:
    _require_license()
    require_forense_admin(request)
    return {"ok": True, **list_sources_catalog(), "dol_api_configured": bool(DOL_API_KEY)}


@app.post("/api/forense/knowledge/sources/sync")
def knowledge_sources_sync(body: KnowledgeSourceSyncBody, request: Request) -> dict:
    _require_license()
    require_forense_admin(request)
    result = sync_source(
        body.source_id,
        limit=body.limit,
        skip_existing=body.skip_existing,
        fatality_only=body.fatality_only,
    )
    if not result.get("ok"):
        raise HTTPException(400, result.get("error", "Sincronización falló"))
    return {"ok": True, **result, "stats": knowledge_stats()}


@app.post("/api/forense/knowledge/sources/sync-industry")
def knowledge_sources_sync_industry(body: KnowledgeSourceSyncIndustryBody, request: Request) -> dict:
    _require_license()
    require_forense_admin(request)
    from .sources.sync import sync_all_by_industry

    result = sync_all_by_industry(
        body.industry,
        limit_per_source=body.limit_per_source,
        skip_existing=body.skip_existing,
    )
    return {"ok": True, **result, "stats": knowledge_stats()}


@app.post("/api/forense/knowledge/sources/ingest-url")
def knowledge_sources_ingest_url(body: KnowledgeIngestUrlBody, request: Request) -> dict:
    _require_license()
    require_forense_admin(request)
    result = ingest_url(
        body.url,
        title=body.title,
        industry=body.industry,
        situation_type=body.situation_type,
        tags=body.tags,
        save=body.save,
    )
    if not result.get("ok"):
        raise HTTPException(400, result.get("error", "Ingesta falló"))
    return {"ok": True, **result, "stats": knowledge_stats()}


@app.post("/api/forense/knowledge/bulk-validate")
def knowledge_bulk_validate(body: KnowledgeBulkValidateBody, request: Request) -> dict:
    _require_license()
    require_forense_admin(request)
    return validate_records(
        body.records,
        default_industry=body.default_industry,
        check_duplicates=body.check_duplicates,
    )


@app.get("/api/forense/knowledge/import/catalog")
def knowledge_import_catalog(request: Request) -> dict:
    _require_license()
    require_forense_admin(request)
    return {
        "ok": True,
        "catalog": list_import_catalog(),
        "dol_api_configured": bool(DOL_API_KEY),
    }


@app.post("/api/forense/knowledge/import/seeds")
def knowledge_import_seeds(body: KnowledgeImportSeedsBody, request: Request) -> dict:
    _require_license()
    require_forense_admin(request)
    result = import_seeds(
        pack_id=body.pack_id,
        industry=body.industry,
        limit=body.limit,
        skip_existing=body.skip_existing,
    )
    return {"ok": True, **result, "stats": knowledge_stats()}


@app.post("/api/forense/knowledge/import/osha")
def knowledge_import_osha(body: KnowledgeImportOshaBody, request: Request) -> dict:
    _require_license()
    require_forense_admin(request)
    result = import_osha(
        keywords=body.keywords,
        limit_per_keyword=body.limit_per_keyword,
        default_industry=body.default_industry,
        fatality_only=body.fatality_only,
        skip_existing=body.skip_existing,
        dol_api_key=DOL_API_KEY or None,
    )
    return {"ok": True, **result, "stats": knowledge_stats()}


@app.get("/api/forense/knowledge/{entry_id}/thumb.jpg")
def knowledge_thumb(entry_id: str, request: Request) -> FileResponse:
    _require_license()
    require_forense_admin(request)
    from .config import KNOWLEDGE_DIR
    from .path_safety import resolve_under, safe_entry_id

    safe = safe_entry_id(entry_id)
    if not safe:
        raise HTTPException(404, "Miniatura no disponible")
    path = resolve_under(KNOWLEDGE_DIR, safe, "thumb.jpg")
    if not path or not path.is_file():
        raise HTTPException(404, "Miniatura no disponible")
    return FileResponse(path, media_type="image/jpeg")


@app.post("/api/forense/jobs/{job_id}/knowledge")
def knowledge_promote_from_job(job_id: str, body: PromoteKnowledgeBody, request: Request) -> dict:
    _require_license()
    require_forense_admin(request)
    job = get_job(job_id)
    if not job:
        raise HTTPException(404, "Trabajo no encontrado")
    entry = promote_job_keyframe(
        job,
        keyframe_name=body.keyframe_name,
        title=body.title,
        situation_type=body.situation_type,
        description=body.description,
    )
    if not entry:
        raise HTTPException(400, "No se pudo guardar la captura en la biblioteca")
    return {"ok": True, "entry": entry}


class PromoteTeachBody(BaseModel):
    keyframe_name: str = Field(..., min_length=1)
    class_id: str = Field(..., min_length=1)


class TrainTeachBody(BaseModel):
    epochs: int = Field(40, ge=10, le=120)


@app.get("/api/forense/teach/status")
def forense_teach_status(request: Request) -> dict:
    _require_license()
    require_forense_admin(request)
    return {"ok": True, **teach_status()}


@app.post("/api/forense/teach/activate")
def forense_teach_activate(request: Request) -> dict:
    _require_license()
    require_forense_admin(request)
    result = activate_custom_model()
    if not result.get("ok"):
        raise HTTPException(400, result.get("error", "Modelo no disponible"))
    return {"ok": True, **result}


@app.post("/api/forense/teach/train")
def forense_teach_train(body: TrainTeachBody, request: Request) -> dict:
    _require_license()
    require_forense_admin(request)
    result = start_training(epochs=body.epochs)
    if not result.get("ok"):
        raise HTTPException(400, result.get("error", "No se pudo iniciar entrenamiento"))
    return {"ok": True, **result}


@app.post("/api/forense/jobs/{job_id}/teach")
def forense_promote_teach(job_id: str, body: PromoteTeachBody, request: Request) -> dict:
    _require_license()
    require_forense_admin(request)
    if not get_job(job_id):
        raise HTTPException(404, "Trabajo no encontrado")
    result = promote_keyframe_to_teach(job_id, body.keyframe_name, body.class_id)
    if not result.get("ok"):
        raise HTTPException(400, result.get("error", "No se pudo enviar a Teach"))
    return {"ok": True, **result}


@app.on_event("startup")
def startup() -> None:
    ensure_dirs()
    ok, detail = verify_license()
    logger.info("VigiEPP Forense %s — licencia: %s (%s)", BUILD, ok, detail)
    try:
        loaded = ensure_custom_model_if_available()
        if loaded.get("ok"):
            logger.info("Modelo Teach activo: %s", loaded.get("model"))
    except Exception as exc:
        logger.info("Forense arranca con modelo base (Teach: %s)", exc)


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


@app.get("/i18n-es-cl.js")
def forense_i18n() -> FileResponse:
    return FileResponse(WEB_DIR / "i18n-es-cl.js", media_type="application/javascript")


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
