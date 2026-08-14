"""API VigiEPP — demo comercial de detección de EPP con IA."""

from __future__ import annotations

import base64
import logging
import os
import time
import zipfile
from contextlib import asynccontextmanager
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional
from urllib.parse import urlparse

import cv2
import numpy as np
from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, PlainTextResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from . import auth as auth_mod
from . import exposure as exposure_mod
from . import notifications as notif_mod
from . import paths as paths_mod
from . import reports as reports_mod
from . import zones as zones_mod
from .compliance import evaluate
from .detector import PPEDetector, decode_image_bytes, encode_jpeg
from .identity import IdentityRegistry, IdentityService
from .profiles import list_profiles
from .scanlog import ScanEvent, log_scan, recent_scans
from .stream_rtsp import get_or_create_stream, stop_all, stop_stream
from .teach import TeachStore

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s: %(message)s")
logger = logging.getLogger("vigiepp")

FRONTEND_DIR = Path(__file__).resolve().parents[2] / "frontend"
_last_scan_log: dict[str, tuple[float, bool]] = {}
_SCAN_DEBOUNCE_S = float(os.getenv("VIGIEPP_SCAN_DEBOUNCE", "12"))


@asynccontextmanager
async def lifespan(_: FastAPI):
    # Precargar modelos en background al arrancar
    try:
        PPEDetector.get()
    except Exception:  # noqa: BLE001
        logger.exception("Precarga de modelo EPP falló")
    try:
        from . import cloud_persist as cloud_mod

        if cloud_mod.configured():
            # Volumen durable: HF es la fuente de verdad tras cada cold start
            result = cloud_mod.hydrate(force=True)
        else:
            result = cloud_mod.pull_and_restore_if_empty()
        if result.get("restored"):
            logger.info("Identidad restaurada desde volumen durable: %s", result.get("workers"))
    except Exception:  # noqa: BLE001
        logger.exception("Durable persist pull falló")
    try:
        IdentityRegistry.get()
    except Exception:  # noqa: BLE001
        logger.exception("Precarga de identidad facial falló")
    yield
    stop_all()


_docs = "/docs" if auth_mod.docs_enabled() else None
app = FastAPI(
    title="VigiEPP",
    description="Detección de EPP con IA — demo para faenas en Chile",
    version="0.2.0",
    lifespan=lifespan,
    docs_url=_docs,
    redoc_url=_docs and "/redoc",
    openapi_url="/openapi.json" if auth_mod.docs_enabled() else None,
)

_cors_raw = os.getenv("VIGIEPP_CORS_ORIGINS", "").strip()
_cors_origins = [o.strip() for o in _cors_raw.split(",") if o.strip()] if _cors_raw else ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(auth_mod.AuthMiddleware)


class DetectB64Request(BaseModel):
    image_b64: str = Field(..., description="JPEG/PNG en base64 (con o sin data URL)")
    profile: str = "general"
    conf: float = 0.35


class RTSPStartRequest(BaseModel):
    url: str
    profile: str = "general"
    conf: float = 0.35


class CameraBody(BaseModel):
    name: str = ""
    url: str
    id: str | None = None


class AuthLoginRequest(BaseModel):
    pin: str = Field(..., min_length=1, max_length=128)


def _validate_rtsp_url(url: str) -> str:
    raw = (url or "").strip()
    if not raw:
        raise HTTPException(400, "URL RTSP requerida")
    parsed = urlparse(raw)
    if parsed.scheme not in ("rtsp", "rtsps"):
        raise HTTPException(400, "Solo se permiten URLs rtsp:// o rtsps://")
    host = (parsed.hostname or "").lower()
    blocked = {
        "localhost",
        "127.0.0.1",
        "::1",
        "0.0.0.0",
        "metadata.google.internal",
        "169.254.169.254",
        "metadata",
    }
    if host in blocked or host.startswith("127.") or host.endswith(".local"):
        raise HTTPException(400, "Host RTSP no permitido")
    allow = os.getenv("VIGIEPP_RTSP_ALLOW", "").strip()
    if allow and allow != "*":
        allowed_hosts = {h.strip().lower() for h in allow.split(",") if h.strip()}
        if host not in allowed_hosts:
            raise HTTPException(400, "Host RTSP fuera de la lista permitida")
    return raw


def _strip_data_url(b64: str) -> str:
    if "," in b64 and b64.strip().startswith("data:"):
        return b64.split(",", 1)[1]
    return b64


def _build_response(
    detections: list[dict],
    annotated_jpeg: bytes | None,
    profile: str,
    identity: dict[str, Any] | None = None,
    frame_wh: tuple[int, int] | None = None,
) -> dict[str, Any]:
    compliance = evaluate(detections, profile)
    fw = frame_wh[0] if frame_wh else 0
    fh = frame_wh[1] if frame_wh else 0
    zone_eval = zones_mod.evaluate_zones(detections, fw, fh) if fw and fh else {"alerts": [], "hits": [], "zones": []}
    alerts = list(compliance.alerts or [])
    for a in zone_eval.get("alerts") or []:
        if a not in alerts:
            alerts.append(a)

    # Si hay zona restringida / near-miss, no marcar como cumple global
    zone_bad = bool(zone_eval.get("alerts"))
    overall = bool(compliance.overall_compliant) and not zone_bad

    exposure = exposure_mod.update_exposure(overall, identity)

    persons = [asdict(p) for p in compliance.persons]
    # Safety score en vivo 0–100 (promedio scores de personas; penaliza zonas)
    if persons:
        avg = sum(float(p.get("score") or 0) for p in persons) / max(1, len(persons))
        live_score = int(round(avg * 100))
    elif detections:
        live_score = 40 if zone_bad else 70
    else:
        live_score = None
    if zone_bad and live_score is not None:
        live_score = max(0, live_score - 25)
    if exposure.get("active") and live_score is not None and int(exposure.get("seconds") or 0) > 30:
        live_score = max(0, live_score - 10)
    if identity and not identity.get("known") and int(identity.get("faces_detected") or 0) > 0:
        live_score = max(0, (live_score if live_score is not None else 55) - 15)
    # Faltantes críticos pesan más en vivo
    if persons and live_score is not None:
        crit = {"casco", "hardhat", "helmet", "arnes", "chaleco", "safety vest", "vest"}
        miss = []
        for p in persons:
            miss.extend(str(x).lower() for x in (p.get("missing") or []))
        if any(any(c in m for c in crit) for m in miss):
            live_score = max(0, live_score - 10)

    payload: dict[str, Any] = {
        "ok": True,
        "detections": detections,
        "compliance": {
            "profile_id": compliance.profile_id,
            "profile_name": compliance.profile_name,
            "overall_compliant": overall,
            "summary": compliance.summary
            if not zone_bad
            else f"{compliance.summary} · alerta de zona",
            "alerts": alerts,
            "persons": persons,
        },
        "identity": identity,
        "zones": {
            "alerts": zone_eval.get("alerts") or [],
            "hits": zone_eval.get("hits") or [],
            "defs": zone_eval.get("zones") or [],
        },
        "exposure": exposure,
        "safety_score": live_score,
        "model": PPEDetector.get().model_name,
        "model_ready": PPEDetector.get().ready,
        "model_warning": PPEDetector.get().error,
    }
    if frame_wh:
        payload["frame_width"] = frame_wh[0]
        payload["frame_height"] = frame_wh[1]
    if annotated_jpeg is not None:
        payload["image_b64"] = base64.b64encode(annotated_jpeg).decode("ascii")
    return payload


def _identify_on_frame(frame: np.ndarray, threshold: float = 0.42) -> dict[str, Any] | None:
    try:
        result = IdentityService().identify(frame, threshold=threshold)
        person = result.get("identified")
        match = (result.get("matches") or [{}])[0]
        face_box = match.get("box")
        if not person:
            return {
                "known": False,
                "name": None,
                "rut": None,
                "method": result.get("method"),
                "faces_detected": result.get("faces_detected", 0),
                "score": match.get("score"),
                "confidence": match.get("confidence"),
                "reject_reason": match.get("reject_reason"),
                "face_box": face_box,
            }
        return {
            "known": bool(person.get("id")),
            "name": person.get("name"),
            "rut": person.get("rut"),
            "id": person.get("id"),
            "method": result.get("method"),
            "score": match.get("score"),
            "confidence": match.get("confidence") or ("high" if person.get("id") else "none"),
            "reject_reason": match.get("reject_reason"),
            "faces_detected": result.get("faces_detected", 0),
            "face_box": face_box,
            "group": person.get("group"),
            "active": person.get("active", True),
        }
    except Exception:  # noqa: BLE001
        logger.exception("Identificación en detect falló")
        return None


def _maybe_log(
    profile: str,
    compliance_block: dict,
    identity: dict | None,
    frame_bgr=None,
) -> str | None:
    """Registra escaneos con persona real y debounce (evita inflar KPIs).
    Si no cumple, guarda evidencia JPEG y devuelve evidence_id."""
    from . import evidence as evidence_mod
    from .detector import encode_jpeg

    persons = compliance_block.get("persons") or []
    known = bool(identity and identity.get("known"))
    faces = int((identity or {}).get("faces_detected") or 0)
    summary = str(compliance_block.get("summary") or "")
    summary_l = summary.lower()

    # No loguear standby / frames vacíos
    if not persons and not known:
        return None
    if "sin persona" in summary_l and not persons:
        return None
    if not identity and not persons:
        return None

    compliant = bool(compliance_block.get("overall_compliant"))
    key = str(
        (identity or {}).get("id")
        or (identity or {}).get("rut")
        or ("known" if known else f"anon-{faces}")
    )
    now = time.time()
    prev = _last_scan_log.get(key)
    if prev and (now - prev[0]) < _SCAN_DEBOUNCE_S and prev[1] == compliant:
        # Misma persona/estado reciente: solo intentar notify (tiene su propio cooldown)
        try:
            if identity:
                notif_mod.maybe_notify_scan(identity, compliance_block, profile)
        except Exception:  # noqa: BLE001
            logger.exception("Notificación automática falló")
        return None

    _last_scan_log[key] = (now, compliant)

    evidence_id = None
    if identity and not compliant and frame_bgr is not None:
        try:
            jpeg = encode_jpeg(frame_bgr, quality=72)
            evidence_id = evidence_mod.save_evidence_jpeg(jpeg)
        except Exception:  # noqa: BLE001
            logger.exception("No se pudo guardar evidencia")

    if identity:
        missing: list[str] = []
        for p in persons:
            missing.extend(p.get("missing") or [])
        log_scan(
            ScanEvent(
                ts=datetime.now(timezone.utc).isoformat(),
                worker_name=identity.get("name"),
                worker_rut=identity.get("rut"),
                worker_id=identity.get("id"),
                profile=profile,
                compliant=compliant,
                summary=summary,
                missing=missing,
                detections=[],
                evidence_id=evidence_id,
            )
        )
    try:
        if identity:
            notif_mod.maybe_notify_scan(identity, compliance_block, profile)
    except Exception:  # noqa: BLE001
        logger.exception("Notificación automática falló")
    return evidence_id

def _maybe_notify_unknown(profile: str, identity: dict | None) -> None:
    if not identity:
        return
    if identity.get("known"):
        return
    if not identity.get("faces_detected"):
        return
    try:
        notif_mod.maybe_notify_unknown(identity, profile)
    except Exception:  # noqa: BLE001
        logger.exception("Notificación de desconocido falló")


def _draw_identity(frame: np.ndarray, identity: dict[str, Any] | None) -> np.ndarray:
    if not identity:
        return frame
    out = frame
    name = identity.get("name") or "Desconocido"
    rut = identity.get("rut") or ""
    known = identity.get("known")
    color = (46, 160, 67) if known else (50, 50, 220)
    label = f"{name}" + (f"  {rut}" if rut and not str(rut).startswith("SIN-RUT") else "")
    cv2.rectangle(out, (12, 12), (12 + max(220, len(label) * 11), 52), color, -1)
    cv2.putText(out, label[:48], (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
    return out


class NotifyConfigBody(BaseModel):
    enabled: Optional[bool] = None
    on_non_compliant: Optional[bool] = None
    on_unknown_face: Optional[bool] = None
    on_zone_alert: Optional[bool] = None
    only_known_workers: Optional[bool] = None
    cooldown_seconds: Optional[int] = None
    access_control: Optional[dict[str, Any]] = None
    channels: Optional[dict[str, Any]] = None
    template: Optional[dict[str, str]] = None
    recipients_extra: Optional[list[str]] = None


class NotifySendBody(BaseModel):
    name: str = "Prueba"
    rut: str = "—"
    profile: str = "general"
    summary: str = "Notificación de prueba VigiEPP"
    missing: list[str] = Field(default_factory=list)
    worker_id: Optional[str] = None
    force: bool = True


class HardwareTestBody(BaseModel):
    action: str = "alarma"


@app.get("/api/health")
def health() -> dict[str, Any]:
    det = PPEDetector.get()
    from . import cloud_persist as cloud_mod

    cloud = cloud_mod.status()
    on_render = bool(os.getenv("RENDER") or os.getenv("RENDER_SERVICE_ID"))
    ephemeral_flag = os.getenv("VIGIEPP_EPHEMERAL", "").strip().lower() in ("1", "true", "yes")
    durable = bool(cloud.get("configured"))
    # Persistencia real = disco host O volumen durable HF
    data_persistent = durable or (paths_mod.is_persistent() and not ephemeral_flag and not on_render) or (
        paths_mod.is_persistent() and os.getenv("VIGIEPP_EPHEMERAL", "").strip() in ("0", "false", "no")
    )
    if durable:
        data_persistent = True
    ephemeral_risk = on_render and not durable and ephemeral_flag
    if on_render and not durable and os.getenv("VIGIEPP_EPHEMERAL", "1").strip() not in ("0", "false", "no"):
        # Free sin HF = riesgo
        ephemeral_risk = True
        data_persistent = False
    return {
        "status": "ok",
        "product": "VigiEPP",
        "model_ready": det.ready,
        "model": det.model_name,
        "warning": det.error,
        "auth_enabled": auth_mod.auth_enabled(),
        "data_dir": str(paths_mod.data_dir()),
        "data_persistent": bool(data_persistent),
        "data_ephemeral_risk": bool(ephemeral_risk and not durable),
        "cloud_backup": cloud,
        "default_pins": auth_mod.using_default_pins(),
        "email_transport": notif_mod.email_transport_status().get("mode"),
    }


@app.get("/api/auth/status")
def auth_status() -> dict[str, Any]:
    return auth_mod.auth_status()


@app.post("/api/auth/login")
def auth_login(body: AuthLoginRequest, request: Request, response: Response) -> dict[str, Any]:
    if not auth_mod.auth_enabled():
        return {"ok": True, "auth_enabled": False, "role": "admin", "message": "Auth desactivada"}
    ip = auth_mod.client_ip(request)
    auth_mod.check_login_rate(ip)
    role = auth_mod.resolve_pin_role(body.pin)
    if not role:
        raise HTTPException(401, "PIN incorrecto")
    auth_mod.clear_login_rate(ip)
    token = auth_mod.create_session(role)
    auth_mod.set_session_cookie(response, token)
    return {
        "ok": True,
        "auth_enabled": True,
        "token": token,
        "role": role,
        "expires_hours": auth_mod.SESSION_HOURS,
    }


@app.post("/api/auth/logout")
def auth_logout(request: Request, response: Response) -> dict[str, Any]:
    token = auth_mod.extract_token(request)
    auth_mod.revoke_session(token)
    auth_mod.clear_session_cookie(response)
    return {"ok": True}


@app.get("/api/auth/me")
def auth_me(request: Request) -> dict[str, Any]:
    if not auth_mod.auth_enabled():
        return {"ok": True, "authenticated": True, "auth_enabled": False, "role": "admin"}
    token = auth_mod.extract_token(request)
    role = auth_mod.session_role(token)
    if not role:
        raise HTTPException(401, "No autorizado")
    return {"ok": True, "authenticated": True, "auth_enabled": True, "role": role}


@app.get("/api/profiles")
def profiles() -> list[dict[str, Any]]:
    return list_profiles()


@app.post("/api/detect")
async def detect_upload(
    file: UploadFile = File(...),
    profile: str = Form("general"),
    conf: float = Form(0.35),
    identify: bool = Form(True),
    return_image: bool = Form(False),
    imgsz: int = Form(416),
    threshold: float = Form(0.42),
) -> JSONResponse:
    data = await file.read()
    if not data:
        raise HTTPException(400, "Archivo vacío")
    try:
        frame = decode_image_bytes(data)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc

    # Reducir resolución de entrada si viene muy grande (acelera)
    h, w = frame.shape[:2]
    max_side = 720
    if max(h, w) > max_side:
        scale = max_side / max(h, w)
        frame = cv2.resize(frame, (int(w * scale), int(h * scale)))

    det = PPEDetector.get()
    detections, annotated = det.predict(frame, conf=conf, imgsz=imgsz)

    thr = max(0.28, min(0.7, float(threshold or 0.42)))
    identity = _identify_on_frame(frame, threshold=thr) if identify else None
    if identity and return_image:
        annotated = _draw_identity(annotated, identity)

    jpeg = encode_jpeg(annotated, quality=70) if return_image else None
    payload = _build_response(
        detections, jpeg, profile, identity=identity, frame_wh=(frame.shape[1], frame.shape[0])
    )
    if identify and identity and identity.get("known"):
        evid = _maybe_log(profile, payload["compliance"], identity, frame_bgr=annotated)
        if evid:
            payload["evidence_id"] = evid
    elif identify and identity and not identity.get("known"):
        _maybe_notify_unknown(profile, identity)
    try:
        notif_mod.maybe_notify_zones(
            identity,
            (payload.get("zones") or {}).get("alerts") or [],
            profile,
        )
    except Exception:  # noqa: BLE001
        logger.exception("Notificación de zona falló")
    try:
        access = notif_mod.maybe_access_gate(identity, payload["compliance"], profile)
        if access is not None:
            payload["access"] = access
    except Exception:  # noqa: BLE001
        logger.exception("Access gate falló")
    return JSONResponse(payload)


@app.get("/api/zones")
def zones_get() -> dict[str, Any]:
    return zones_mod.get_zones()


@app.get("/api/zones/presets")
def zones_presets() -> dict[str, Any]:
    return {"presets": zones_mod.list_presets()}


@app.post("/api/zones/presets/{preset_id}")
def zones_apply_preset(preset_id: str) -> dict[str, Any]:
    try:
        return zones_mod.apply_preset(preset_id)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc


@app.post("/api/zones")
async def zones_save(request: Request) -> dict[str, Any]:
    body = await request.json()
    zones = body.get("zones") if isinstance(body, dict) else body
    if not isinstance(zones, list):
        raise HTTPException(400, "Se esperaba { zones: [...] }")
    return zones_mod.save_zones(zones)


@app.get("/api/scans/recent")
def scans_recent(limit: int = 15) -> list[dict[str, Any]]:
    return recent_scans(limit=limit)


@app.get("/api/evidence/{evidence_id}")
def evidence_get(evidence_id: str) -> FileResponse:
    from . import evidence as evidence_mod

    path = evidence_mod.evidence_path(evidence_id)
    if not path:
        raise HTTPException(404, "Evidencia no encontrada")
    return FileResponse(path, media_type="image/jpeg", filename=f"{evidence_id}.jpg")


@app.get("/api/reports/stats")
def reports_stats(days: int = 30, profile: Optional[str] = None) -> dict[str, Any]:
    return reports_mod.compute_stats(days=max(1, min(days, 365)), profile=profile or None)


@app.get("/api/reports/export.csv")
def reports_export_csv(
    days: int = 30,
    only_bad: bool = False,
    profile: Optional[str] = None,
) -> Response:
    content = reports_mod.export_csv(
        days=max(1, min(days, 365)),
        only_non_compliant=only_bad,
        profile=profile or None,
    )
    filename = "vigiepp_incumplimientos.csv" if only_bad else "vigiepp_escaneos.csv"
    return Response(
        content=content,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@app.get("/api/reports/print")
def reports_print(days: int = 7, profile: Optional[str] = None) -> dict[str, Any]:
    return reports_mod.build_printable_report(days=max(1, min(days, 365)), profile=profile or None)


@app.get("/api/reports/print.html", response_class=HTMLResponse)
def reports_print_html(days: int = 7, profile: Optional[str] = None) -> HTMLResponse:
    report = reports_mod.build_printable_report(days=max(1, min(days, 365)), profile=profile or None)
    return HTMLResponse(report.get("html") or "<p>Sin informe</p>")


@app.get("/api/reports/summary.txt")
def reports_summary_txt(days: int = 7, profile: Optional[str] = None) -> PlainTextResponse:
    report = reports_mod.build_printable_report(days=max(1, min(days, 365)), profile=profile or None)
    return PlainTextResponse(report["text"], media_type="text/plain; charset=utf-8")


@app.get("/api/notifications/config")
def notifications_config_get() -> dict[str, Any]:
    cfg = notif_mod.get_config()
    return {**cfg, "email_transport": notif_mod.email_transport_status()}


@app.post("/api/notifications/config")
def notifications_config_set(body: NotifyConfigBody) -> dict[str, Any]:
    patch = body.model_dump(exclude_none=True)
    try:
        return {"ok": True, "config": notif_mod.save_config(patch)}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/api/notifications/log")
def notifications_log(limit: int = 40) -> list[dict[str, Any]]:
    return notif_mod.recent_log(limit=limit)


@app.post("/api/notifications/send")
def notifications_send(body: NotifySendBody) -> dict[str, Any]:
    return notif_mod.send_notification(
        {
            "name": body.name,
            "rut": body.rut,
            "profile": body.profile,
            "summary": body.summary,
            "missing": body.missing,
            "worker_id": body.worker_id,
            "ts": datetime.now(timezone.utc).isoformat(),
        },
        force=body.force,
        kind="manual",
    )


@app.post("/api/notifications/test")
def notifications_test() -> dict[str, Any]:
    return notif_mod.send_notification(
        {
            "name": "Prueba VigiEPP",
            "rut": "11.111.111-1",
            "profile": "general",
            "summary": "Esta es una notificación de prueba",
            "missing": ["casco"],
            "worker_id": "test",
            "ts": datetime.now(timezone.utc).isoformat(),
        },
        force=True,
        kind="test",
    )


@app.post("/api/notifications/hardware/test")
def notifications_hardware_test(body: HardwareTestBody) -> dict[str, Any]:
    """Dispara /alarma o /ok en el ESP32 (misma red que el servidor VigiEPP)."""
    return notif_mod.test_hardware(body.action or "alarma")


@app.post("/api/rtsp/start")
def rtsp_start(body: RTSPStartRequest) -> dict[str, Any]:
    url = _validate_rtsp_url(body.url)
    stream = get_or_create_stream(url)
    return {
        "ok": True,
        "url": url,
        "connected": stream.connected,
        "error": stream.last_error,
        "hint": "Usa GET /api/rtsp/frame?url=...&profile=... para frames anotados",
    }


@app.get("/api/rtsp/frame")
def rtsp_frame(
    url: str,
    profile: str = "general",
    conf: float = 0.35,
    identify: bool = False,
) -> JSONResponse:
    url = _validate_rtsp_url(url)
    stream = get_or_create_stream(url)
    frame = stream.read()
    if frame is None:
        return JSONResponse(
            {
                "ok": False,
                "connected": stream.connected,
                "error": stream.last_error or "Esperando primer frame del stream...",
            },
            status_code=202,
        )

    h, w = frame.shape[:2]
    if max(h, w) > 720:
        scale = 720 / max(h, w)
        frame = cv2.resize(frame, (int(w * scale), int(h * scale)))

    det = PPEDetector.get()
    detections, _annotated = det.predict(frame, conf=conf, imgsz=416)
    identity = _identify_on_frame(frame) if identify else None
    payload = _build_response(
        detections, None, profile, identity=identity, frame_wh=(frame.shape[1], frame.shape[0])
    )
    return JSONResponse(payload)


@app.post("/api/rtsp/stop")
def rtsp_stop(body: RTSPStartRequest) -> dict[str, Any]:
    stop_stream(body.url)
    return {"ok": True}


@app.get("/api/cameras")
def cameras_list() -> dict[str, Any]:
    from . import cameras as cameras_mod

    return {"ok": True, "cameras": cameras_mod.list_cameras(), "max": cameras_mod.MAX_CAMERAS}


@app.post("/api/cameras")
def cameras_upsert(body: CameraBody) -> dict[str, Any]:
    from . import audit as audit_mod
    from . import cameras as cameras_mod

    try:
        cam = cameras_mod.upsert(body.name, body.url, body.id)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    audit_mod.log("camera_upsert", detail=cam.get("name") or cam.get("id"))
    return {"ok": True, "camera": cam}


@app.delete("/api/cameras/{camera_id}")
def cameras_delete(camera_id: str) -> dict[str, Any]:
    from . import audit as audit_mod
    from . import cameras as cameras_mod

    ok = cameras_mod.delete(camera_id)
    if not ok:
        raise HTTPException(404, "Cámara no encontrada")
    audit_mod.log("camera_delete", detail=camera_id)
    return {"ok": True, "deleted": camera_id}


@app.get("/api/audit")
def audit_recent(limit: int = 80) -> dict[str, Any]:
    from . import audit as audit_mod

    return {"ok": True, "events": audit_mod.recent(limit=limit)}


# ── Identidad (QR cédula + rostro) ──────────────────────────────────────────


@app.get("/api/identity/workers")
def identity_workers() -> list[dict[str, Any]]:
    return IdentityRegistry.get().list_workers()


@app.get("/api/identity/consent.csv")
def identity_consent_csv() -> Response:
    """Export CSV de consentimiento biométrico (Ley 19.628 / DS 44)."""
    import csv
    import io

    workers = IdentityRegistry.get().list_workers()
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(
        [
            "id",
            "nombre",
            "rut",
            "grupo",
            "activo",
            "consentimiento_ok",
            "consentimiento_fecha",
            "consentimiento_version",
            "enrolado_en",
            "muestras_rostro",
        ]
    )
    for w in workers:
        writer.writerow(
            [
                w.get("id") or "",
                w.get("name") or "",
                w.get("rut") or "",
                w.get("group") or "",
                "si" if w.get("active", True) else "no",
                "si" if w.get("consent_ok") else "no",
                w.get("consent_at") or "",
                w.get("consent_version") or "",
                w.get("enrolled_at") or "",
                w.get("face_samples") or 0,
            ]
        )
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M")
    return Response(
        content=buf.getvalue().encode("utf-8-sig"),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="vigiepp-consentimiento-{stamp}.csv"'},
    )


@app.get("/api/identity/backup")
def identity_backup() -> Response:
    """Descarga ZIP con workers.json + fotos/embeddings + config operativa."""
    from . import backup as backup_mod

    data = backup_mod.build_backup_zip()
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M")
    return Response(
        content=data,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="vigiepp-personas-{stamp}.zip"'},
    )


@app.post("/api/identity/backup/restore")
async def identity_backup_restore(
    file: UploadFile = File(...),
    mode: str = Form("merge"),
) -> dict[str, Any]:
    """Restaura backup ZIP. mode=merge|replace."""
    from . import backup as backup_mod

    raw = await file.read()
    if not raw:
        raise HTTPException(400, "Archivo vacío")
    try:
        result = backup_mod.restore_backup_zip(raw, mode=mode.strip() or "merge")
        backup_mod.reload_identity_registry()
        try:
            from . import cloud_persist as cloud_mod

            cloud_mod.schedule_push(2.0)
        except Exception:  # noqa: BLE001
            pass
        return result
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    except zipfile.BadZipFile as exc:
        raise HTTPException(400, "ZIP inválido") from exc


@app.delete("/api/identity/workers/{worker_id}")
def identity_delete(worker_id: str) -> dict[str, Any]:
    ok = IdentityRegistry.get().delete_worker(worker_id)
    if not ok:
        raise HTTPException(404, "Trabajador no encontrado")
    from . import audit as audit_mod

    audit_mod.log("worker_delete", detail=worker_id)
    return {"ok": True, "deleted": worker_id}


@app.patch("/api/identity/workers/{worker_id}")
async def identity_update(worker_id: str, request: Request) -> dict[str, Any]:
    """Actualiza ficha: nombre, RUT, activo, grupo, notas."""
    from .identity import compute_quality, normalize_person_name, normalize_rut, validate_rut, worker_public

    body = await request.json()
    reg = IdentityRegistry.get()
    worker = reg._workers.get(worker_id)
    if not worker:
        raise HTTPException(404, "Trabajador no encontrado")
    if "name" in body:
        name = normalize_person_name(str(body.get("name") or "").strip())
        if name:
            worker.name = name
    if "rut" in body:
        rut_raw = str(body.get("rut") or "").strip()
        if rut_raw:
            rut = normalize_rut(rut_raw)
            if not validate_rut(rut) and not rut.startswith("SIN-RUT"):
                raise HTTPException(400, "RUT inválido")
            for wid, w in reg._workers.items():
                if wid != worker_id and w.rut == rut:
                    raise HTTPException(409, f"El RUT ya está en {w.name}")
            worker.rut = rut
    if "active" in body:
        worker.active = bool(body.get("active"))
    if "group" in body:
        worker.group = str(body.get("group") or "").strip()[:80]
    if "notes" in body:
        worker.notes = str(body.get("notes") or "").strip()[:500]
    worker.quality = compute_quality(worker.face_samples)
    reg._workers[worker_id] = worker
    reg._save()
    return {"ok": True, "worker": worker_public(worker)}


@app.get("/api/identity/workers/{worker_id}/photo")
def identity_worker_photo(worker_id: str) -> Response:
    from .identity import FACES_DIR

    folder = FACES_DIR / worker_id
    if not folder.exists():
        raise HTTPException(404, "Sin foto")
    photos = sorted(folder.glob("face_*.jpg"))
    if not photos:
        raise HTTPException(404, "Sin foto")
    data = photos[-1].read_bytes()
    return Response(content=data, media_type="image/jpeg", headers={"Cache-Control": "private, max-age=60"})


@app.post("/api/identity/workers/{worker_id}/reset-faces")
def identity_reset_faces(worker_id: str) -> dict[str, Any]:
    """Borra solo las fotos/embeddings; mantiene nombre y RUT para re-enrolar."""
    from .identity import FACES_DIR, compute_quality, worker_public

    reg = IdentityRegistry.get()
    worker = reg._workers.get(worker_id)
    if not worker:
        raise HTTPException(404, "Trabajador no encontrado")
    folder = FACES_DIR / worker_id
    if folder.exists():
        for f in folder.iterdir():
            f.unlink(missing_ok=True)
    reg._embeddings[worker_id] = []
    worker.face_samples = 0
    worker.quality = compute_quality(0)
    reg._workers[worker_id] = worker
    reg._save()
    return {
        "ok": True,
        "worker": worker_public(worker),
        "message": "Rostros borrados. Volvé a enrolar 4 posiciones.",
    }


@app.post("/api/identity/enroll")
async def identity_enroll(
    file: UploadFile = File(...),
    name: str = Form(""),
    rut: str = Form(""),
    notes: str = Form(""),
    consent: str = Form("false"),
) -> JSONResponse:
    data = await file.read()
    try:
        frame = decode_image_bytes(data)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    agreed = str(consent).strip().lower() in ("1", "true", "yes", "on")
    result = IdentityService().enroll(frame, name=name, rut=rut, notes=notes, consent=agreed)
    if not result.get("ok"):
        raise HTTPException(400, result.get("error", "No se pudo enrolar"))
    if result.get("face_enrolled"):
        from . import audit as audit_mod

        w = result.get("worker") or {}
        audit_mod.log("enroll_face", detail=str(w.get("name") or name), extra={"samples": result.get("samples")})
    return JSONResponse(result)


@app.post("/api/identity/enroll-photos")
async def identity_enroll_photos(
    files: list[UploadFile] = File(...),
    name: str = Form(""),
    rut: str = Form(""),
    consent: str = Form("false"),
) -> JSONResponse:
    """Entrena rostros adjuntando varias fotos (sin countdown de poses)."""
    if not name.strip() and not rut.strip():
        raise HTTPException(400, "Indicá nombre o RUT")
    agreed = str(consent).strip().lower() in ("1", "true", "yes", "on")
    if not agreed:
        raise HTTPException(400, "Falta consentimiento biométrico para registrar el rostro.")
    saved = 0
    failed = 0
    last_worker = None
    errors: list[str] = []
    for f in files[:40]:
        data = await f.read()
        if not data:
            continue
        try:
            frame = decode_image_bytes(data)
        except ValueError:
            failed += 1
            continue
        result = IdentityService().enroll(
            frame, name=name, rut=rut, notes="foto_adjunta", consent=agreed
        )
        if result.get("face_enrolled"):
            saved += 1
            last_worker = result.get("worker")
        else:
            failed += 1
            err = result.get("error") or result.get("message") or "sin rostro"
            errors.append(str(err))
    if saved == 0:
        raise HTTPException(
            400,
            errors[0] if errors else "Ninguna foto tuvo rostro usable. Subí fotos de frente, con buena luz.",
        )
    ready = bool(last_worker and last_worker.get("ready"))
    return JSONResponse(
        {
            "ok": True,
            "saved": saved,
            "failed": failed,
            "worker": last_worker,
            "ready": ready,
            "message": (
                f"Rostro: {saved} fotos de calidad"
                + (f" · {failed} descartadas (borrosas/ángulo/lejos)" if failed else "")
                + (
                    " · ficha lista para identificación estricta."
                    if ready
                    else " · incompleta: necesitás al menos 4 muestras aceptadas."
                )
            ),
        }
    )


@app.post("/api/identity/identify")
async def identity_identify(
    file: UploadFile = File(...),
    threshold: float = Form(0.42),
) -> JSONResponse:
    data = await file.read()
    try:
        frame = decode_image_bytes(data)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    thr = max(0.28, min(0.7, float(threshold or 0.42)))
    result = IdentityService().identify(frame, threshold=thr)
    jpeg = encode_jpeg(result.pop("annotated"))
    result["image_b64"] = base64.b64encode(jpeg).decode("ascii")
    return JSONResponse(result)


# ── Enseñar EPP personalizado ───────────────────────────────────────────────


@app.get("/api/teach/guide")
def teach_guide() -> dict[str, Any]:
    return TeachStore.get().guide()


@app.get("/api/teach/classes")
def teach_classes() -> list[dict[str, Any]]:
    return TeachStore.get().list_classes()


@app.get("/api/teach/stats")
def teach_stats() -> dict[str, Any]:
    return TeachStore.get().stats()


@app.post("/api/teach/sample")
async def teach_sample(
    file: UploadFile = File(...),
    class_id: str = Form(...),
) -> JSONResponse:
    data = await file.read()
    try:
        frame = decode_image_bytes(data)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    result = TeachStore.get().add_sample(frame, class_id=class_id)
    if not result.get("ok"):
        raise HTTPException(400, result.get("error", "Error al guardar"))
    return JSONResponse(result)


@app.post("/api/teach/class")
async def teach_create_class(
    name: str = Form(...),
    hint: str = Form(""),
) -> JSONResponse:
    result = TeachStore.get().add_custom_class(name=name, hint=hint)
    if not result.get("ok"):
        raise HTTPException(400, result.get("error", "No se pudo crear la clase"))
    return JSONResponse(result)


@app.post("/api/teach/samples")
async def teach_samples_multi(
    files: list[UploadFile] = File(...),
    class_id: str = Form(...),
) -> JSONResponse:
    frames: list[Any] = []
    for f in files[:80]:
        data = await f.read()
        if not data:
            continue
        try:
            frames.append(decode_image_bytes(data))
        except ValueError:
            continue
    if not frames:
        raise HTTPException(400, "No se pudieron leer las fotos")
    result = TeachStore.get().add_samples_batch(frames, class_id=class_id)
    if not result.get("ok"):
        raise HTTPException(400, result.get("error") or result.get("message") or "Error")
    return JSONResponse(result)


@app.post("/api/teach/video")
async def teach_video(
    file: UploadFile = File(...),
    class_id: str = Form(...),
    max_frames: int = Form(40),
    stride: int = Form(12),
) -> JSONResponse:
    data = await file.read()
    if not data:
        raise HTTPException(400, "Video vacío")
    if len(data) > 120 * 1024 * 1024:
        raise HTTPException(400, "Video demasiado grande (máx. ~120 MB)")
    result = TeachStore.get().add_from_video(
        data,
        class_id=class_id,
        max_frames=max_frames,
        stride=stride,
    )
    if not result.get("ok"):
        raise HTTPException(400, result.get("error", "No se pudo procesar el video"))
    return JSONResponse(result)


@app.post("/api/teach/train")
def teach_train(epochs: int = 40) -> dict[str, Any]:
    result = TeachStore.get().start_training(epochs=epochs)
    if not result.get("ok"):
        raise HTTPException(400, result.get("error", "No se pudo entrenar"))
    return result


@app.post("/api/teach/activate")
def teach_activate() -> dict[str, Any]:
    result = PPEDetector.get().load_custom_model()
    if not result.get("ok"):
        raise HTTPException(400, result.get("error", "Modelo no disponible"))
    return result


@app.websocket("/ws/detect")
async def ws_detect(websocket: WebSocket) -> None:
    """Recibe frames JPEG binarios; responde JSON con resultado + imagen anotada."""
    if auth_mod.auth_enabled():
        token = websocket.cookies.get(auth_mod.COOKIE_NAME) or websocket.query_params.get("token")
        header = websocket.headers.get(auth_mod.HEADER_NAME.lower()) or websocket.headers.get("authorization")
        if header and header.lower().startswith("bearer "):
            token = header[7:].strip()
        elif header:
            token = header.strip()
        ok = auth_mod.session_valid(token) or (bool(token) and auth_mod.credentials_ok(token))
        if not ok:
            await websocket.close(code=4401)
            return
    await websocket.accept()
    det = PPEDetector.get()
    profile = "general"
    conf = 0.35
    try:
        while True:
            message = await websocket.receive()
            if message.get("type") == "websocket.disconnect":
                break

            if "text" in message and message["text"] is not None:
                import json

                meta = json.loads(message["text"])
                profile = meta.get("profile", profile)
                conf = float(meta.get("conf", conf))
                await websocket.send_json({"ok": True, "type": "config", "profile": profile, "conf": conf})
                continue

            data = message.get("bytes")
            if not data:
                continue

            try:
                frame = decode_image_bytes(data)
            except ValueError:
                await websocket.send_json({"ok": False, "error": "frame inválido"})
                continue

            detections, annotated = det.predict(frame, conf=conf, imgsz=416)
            jpeg = encode_jpeg(annotated, quality=70)
            payload = _build_response(detections, jpeg, profile)
            await websocket.send_json(payload)
    except WebSocketDisconnect:
        logger.info("WebSocket cerrado")
    except Exception:  # noqa: BLE001
        logger.exception("Error en WebSocket")
        try:
            await websocket.close()
        except Exception:  # noqa: BLE001
            pass


# Frontend estático
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
        return HTMLResponse(html)
else:

    @app.get("/")
    async def index_fallback() -> dict[str, str]:
        return {"message": "Frontend no encontrado. Crea la carpeta frontend/"}


def create_app() -> FastAPI:
    return app