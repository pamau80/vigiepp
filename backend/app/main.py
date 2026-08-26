"""API VigiEPP — demo comercial de detección de EPP con IA."""

from __future__ import annotations

import base64
import logging
import os
import threading
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
from . import inference as inference_mod
from . import notifications as notif_mod
from . import oidc as oidc_mod
from . import paths as paths_mod
from . import reports as reports_mod
from . import tenants as tenants_mod
from . import zones as zones_mod
from .compliance import evaluate
from .detector import PPEDetector, decode_image_bytes, encode_jpeg
from .identity import IdentityRegistry, IdentityService
from .profiles import get_profile, list_profiles, parse_required_list, PPE_CATALOG
from .scanlog import ScanEvent, log_scan, recent_scans
from .stream_rtsp import get_or_create_stream, stop_all, stop_stream
from .teach import TeachStore

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s: %(message)s")
logger = logging.getLogger("vigiepp")

FRONTEND_DIR = Path(__file__).resolve().parents[2] / "frontend"
_last_scan_log: dict[str, tuple[float, bool]] = {}
_SCAN_DEBOUNCE_S = float(os.getenv("VIGIEPP_SCAN_DEBOUNCE", "12"))
_detect_lock = threading.Lock()
# Render Free: YOLO+SFace en paralelo tumba el proceso (502). Una inferencia a la vez.
_DETECT_IMGSZ_MAX = int(os.getenv("VIGIEPP_IMGSZ_MAX", "256"))


BUILD_VERSION = "v37"


@asynccontextmanager
async def lifespan(_: FastAPI):
    # Render Free: identidad primero; YOLO lazy ~10s después (ID+EPP sin OOM).
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

    threading.Thread(target=_warm, name="vigiepp-warm", daemon=True).start()
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


class NVRProbeBody(BaseModel):
    vendor: str = "dahua"
    host: str
    username: str = ""
    password: str = ""
    port: int = 554
    http_port: int = 80
    channel_count: int = 8
    subtype: int = 0


class NVRRegisterBody(NVRProbeBody):
    name: str = ""
    id: str | None = None


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
    required: list[str] | None = None,
) -> dict[str, Any]:
    compliance = evaluate(detections, profile, required_override=required)
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
            "required": required if required is not None else list(get_profile(profile)["required"]),
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
        "model_warning": (PPEDetector.peek().error if PPEDetector.peek() else None),
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
                "gallery_size": result.get("gallery_size", 0),
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
            "gallery_size": result.get("gallery_size", 0),
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


class SiteCreateBody(BaseModel):
    name: str = Field(..., min_length=1, max_length=80)


class SiteActiveBody(BaseModel):
    site_id: str = Field(..., min_length=1, max_length=40)


@app.get("/api/health")
def health() -> dict[str, Any]:
    # No llamar PPEDetector.get(): en cold start bloquearía >5s y Render marca 502.
    det = PPEDetector.peek()
    reg = IdentityRegistry.peek()
    from . import cloud_persist as cloud_mod

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


@app.get("/api/auth/oidc/config")
def oidc_config() -> dict[str, Any]:
    return oidc_mod.public_config()


@app.get("/api/auth/oidc/login")
def oidc_login() -> dict[str, Any]:
    try:
        return {"ok": True, "url": oidc_mod.authorize_url()}
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc


@app.get("/api/auth/oidc/callback")
def oidc_callback(response: Response, code: str = "", state: str = "") -> dict[str, Any]:
    if not code:
        raise HTTPException(400, "Falta code")
    try:
        tokens = oidc_mod.exchange_code(code)
        access = str(tokens.get("access_token") or "")
        user = oidc_mod.userinfo(access) if access else {}
        role = "admin"
        token = auth_mod.create_session(role)
        auth_mod.set_session_cookie(response, token)
        return {
            "ok": True,
            "role": role,
            "token": token,
            "user": {
                "email": user.get("email"),
                "name": user.get("name") or user.get("preferred_username"),
            },
        }
    except Exception as exc:  # noqa: BLE001
        logger.exception("OIDC callback falló")
        raise HTTPException(401, f"OIDC falló: {exc}") from exc


@app.get("/api/sites")
def sites_list() -> dict[str, Any]:
    active_id = tenants_mod.get_active_site_id()
    return {
        "sites": tenants_mod.list_sites(),
        "active_site_id": active_id,
        "active_site": tenants_mod.get_site(active_id),
    }


@app.post("/api/sites")
def sites_create(body: SiteCreateBody) -> dict[str, Any]:
    site = tenants_mod.create_site(body.name)
    return {"ok": True, "site": site}


@app.post("/api/sites/active")
def sites_set_active(body: SiteActiveBody) -> dict[str, Any]:
    try:
        site = tenants_mod.set_active_site(body.site_id)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    return {"ok": True, "site": site, "active_site_id": body.site_id}


@app.get("/api/profiles")
def profiles() -> list[dict[str, Any]]:
    return list_profiles()


@app.get("/api/ppe/catalog")
def ppe_catalog() -> dict[str, Any]:
    return {"items": PPE_CATALOG}


@app.post("/api/detect")
async def detect_upload(
    file: UploadFile = File(...),
    profile: str = Form("general"),
    conf: float = Form(0.35),
    identify: bool = Form(False),
    return_image: bool = Form(False),
    imgsz: int = Form(416),
    threshold: float = Form(0.33),
    required: str = Form(""),
) -> JSONResponse:
    data = await file.read()
    if not data:
        raise HTTPException(400, "Archivo vacío")
    if not _detect_lock.acquire(blocking=False):
        return JSONResponse(
            {"ok": False, "busy": True, "error": "IA ocupada, esperá un momento."},
            status_code=429,
        )
    try:
        return _detect_frame(
            data,
            profile=profile,
            conf=conf,
            identify=identify,
            return_image=return_image,
            imgsz=imgsz,
            threshold=threshold,
            required=parse_required_list(required),
        )
    finally:
        _detect_lock.release()


def _detect_frame(
    data: bytes,
    *,
    profile: str,
    conf: float,
    identify: bool,
    return_image: bool,
    imgsz: int,
    threshold: float,
    required: list[str] | None = None,
) -> JSONResponse:
    try:
        frame = decode_image_bytes(data)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc

    h, w = frame.shape[:2]
    max_side = 384
    if max(h, w) > max_side:
        scale = max_side / max(h, w)
        frame = cv2.resize(frame, (int(w * scale), int(h * scale)))

    thr = max(0.25, min(0.7, float(threshold or 0.33)))
    identity = None
    detections: list = []
    annotated = frame
    imgsz_use = max(224, min(int(imgsz or _DETECT_IMGSZ_MAX), _DETECT_IMGSZ_MAX))
    combined = inference_mod.combined_inference_enabled()

    if identify and not combined:
        reg = IdentityRegistry.peek()
        if reg is None:
            threading.Thread(target=IdentityRegistry.get, name="id-load", daemon=True).start()
            identity = {
                "known": False,
                "booting": True,
                "name": None,
                "rut": None,
                "method": None,
                "faces_detected": 0,
                "reject_reason": "identity_loading",
            }
        else:
            identity = _identify_on_frame(frame, threshold=thr)
        if identity and return_image:
            annotated = _draw_identity(annotated, identity)
    else:
        reg = IdentityRegistry.peek()
        det = PPEDetector.peek()
        if identify and reg is None:
            threading.Thread(target=IdentityRegistry.get, name="id-load", daemon=True).start()
        if det is None or not det.ready:
            threading.Thread(target=PPEDetector.get, name="epp-load", daemon=True).start()
            if not identify:
                return JSONResponse(
                    {
                        "ok": False,
                        "booting": True,
                        "error": "Modelo IA cargando… reintentá en unos segundos.",
                        "detections": [],
                        "compliance": {"overall_compliant": False, "persons": [], "summary": "Cargando IA"},
                    },
                    status_code=503,
                )
        try:
            detections, annotated, identity = inference_mod.analyze_frame(
                frame,
                conf=conf,
                imgsz=imgsz_use,
                threshold=thr,
                identify=identify,
                annotate=return_image,
            )
        except RuntimeError:
            return JSONResponse(
                {
                    "ok": False,
                    "booting": True,
                    "error": "Modelo IA cargando… reintentá en unos segundos.",
                    "detections": [],
                    "compliance": {"overall_compliant": False, "persons": [], "summary": "Cargando IA"},
                },
                status_code=503,
            )
        except Exception:  # noqa: BLE001
            logger.exception("Inferencia falló")
            return JSONResponse(
                {
                    "ok": False,
                    "error": "La IA falló en este frame. Reintentá.",
                    "detections": [],
                    "compliance": {"overall_compliant": False, "persons": [], "summary": "Error de inferencia"},
                },
                status_code=503,
            )
        if identify and identity and return_image:
            annotated = _draw_identity(annotated, identity)

    jpeg = encode_jpeg(annotated, quality=68) if return_image else None
    payload = _build_response(
        detections,
        jpeg,
        profile,
        identity=identity,
        frame_wh=(frame.shape[1], frame.shape[0]),
        required=required,
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
    required: str = "",
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
    det = PPEDetector.get()
    identity = None
    detections: list = []
    if identify:
        identity = _identify_on_frame(frame)
    else:
        detections, _annotated = det.predict(
            frame, conf=conf, imgsz=_DETECT_IMGSZ_MAX, annotate=False
        )
    payload = _build_response(
        detections,
        None,
        profile,
        identity=identity,
        frame_wh=(frame.shape[1], frame.shape[0]),
        required=parse_required_list(required),
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


# ── NVR / DVR (Dahua, Hikvision, Uniview) ───────────────────────────────────


@app.get("/api/nvr/vendors")
def nvr_vendors() -> dict[str, Any]:
    from . import nvr as nvr_mod

    return {"ok": True, "vendors": nvr_mod.list_vendors()}


@app.post("/api/nvr/probe")
def nvr_probe(body: NVRProbeBody) -> dict[str, Any]:
    from . import nvr as nvr_mod

    try:
        result = nvr_mod.probe_device(
            body.vendor,
            body.host,
            username=body.username,
            password=body.password,
            port=body.port,
            http_port=body.http_port,
            channel_count=body.channel_count,
            subtype=body.subtype,
        )
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    return {"ok": True, **result}


@app.get("/api/nvr/devices")
def nvr_devices_list() -> dict[str, Any]:
    from . import nvr as nvr_mod

    return {"ok": True, "devices": nvr_mod.list_devices()}


@app.post("/api/nvr/devices")
def nvr_devices_register(body: NVRRegisterBody) -> dict[str, Any]:
    from . import audit as audit_mod
    from . import nvr as nvr_mod

    try:
        device = nvr_mod.register_device(
            body.vendor,
            body.host,
            body.name,
            username=body.username,
            password=body.password,
            port=body.port,
            http_port=body.http_port,
            channel_count=body.channel_count,
            subtype=body.subtype,
            device_id=body.id,
        )
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    audit_mod.log("nvr_register", detail=device.get("name") or device.get("host"))
    return {"ok": True, "device": device}


@app.delete("/api/nvr/devices/{device_id}")
def nvr_devices_delete(device_id: str) -> dict[str, Any]:
    from . import audit as audit_mod
    from . import nvr as nvr_mod

    ok = nvr_mod.delete_device(device_id)
    if not ok:
        raise HTTPException(404, "NVR no encontrado")
    audit_mod.log("nvr_delete", detail=device_id)
    return {"ok": True, "deleted": device_id}


@app.post("/api/nvr/devices/{device_id}/import-watchlist")
def nvr_import_watchlist(device_id: str, replace: bool = False) -> dict[str, Any]:
    from . import nvr as nvr_mod
    from . import watchlist as watch_mod

    devices = nvr_mod.list_devices()
    device = next((d for d in devices if d.get("id") == device_id), None)
    if not device:
        raise HTTPException(404, "NVR no encontrado")
    entries = []
    for ch in device.get("channels") or []:
        entries.append(
            {
                "name": f"{device.get('name')} · {ch.get('name')}",
                "url": ch.get("url"),
                "vendor": device.get("vendor"),
                "nvr_id": device_id,
                "channel": ch.get("channel"),
                "enabled": True,
            }
        )
    channels = watch_mod.import_channels(entries, replace=replace)
    return {"ok": True, "imported": len(entries), "channels": channels, "max": watch_mod.MAX_WATCH}


# ── Vigilancia masiva (watchlist) ───────────────────────────────────────────


@app.get("/api/watchlist")
def watchlist_list() -> dict[str, Any]:
    from . import watchlist as watch_mod

    return {"ok": True, "channels": watch_mod.list_channels(), "max": watch_mod.MAX_WATCH}


@app.post("/api/watchlist")
def watchlist_upsert(body: WatchChannelBody) -> dict[str, Any]:
    from . import watchlist as watch_mod

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


@app.post("/api/watchlist/import")
def watchlist_import(body: WatchImportBody) -> dict[str, Any]:
    from . import watchlist as watch_mod

    try:
        channels = watch_mod.import_channels(body.channels, replace=body.replace)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    return {"ok": True, "channels": channels, "max": watch_mod.MAX_WATCH}


@app.delete("/api/watchlist/{channel_id}")
def watchlist_delete(channel_id: str) -> dict[str, Any]:
    from . import watchlist as watch_mod

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


@app.get("/api/rtsp/jpeg")
def rtsp_jpeg(url: str, max_w: int = 480) -> Response:
    url = _validate_rtsp_url(url)
    stream = get_or_create_stream(url)
    frame = stream.read()
    if frame is None:
        raise HTTPException(202, stream.last_error or "Esperando frame RTSP")
    h, w = frame.shape[:2]
    if w > max_w:
        scale = max_w / w
        frame = cv2.resize(frame, (max_w, int(h * scale)))
    return Response(content=encode_jpeg(frame, quality=80), media_type="image/jpeg")


@app.post("/api/surveillance/mass/scan")
def surveillance_mass_scan(
    profile: str = "general",
    conf: float = 0.35,
    required: str = "",
) -> dict[str, Any]:
    """Analiza EPP en todos los canales activos de la watchlist."""
    from . import watchlist as watch_mod

    enabled = [c for c in watch_mod.list_channels() if c.get("enabled")]
    if not enabled:
        return {"ok": True, "cells": [], "summary": {"total": 0, "alerts": 0}}

    det = PPEDetector.get()
    req = parse_required_list(required)
    cells: list[dict[str, Any]] = []
    alert_count = 0

    for ch in enabled:
        url = ch.get("url") or ""
        cell: dict[str, Any] = {
            "id": ch.get("id"),
            "name": ch.get("name"),
            "url": url,
            "ok": False,
            "connected": False,
            "compliant": None,
            "missing": [],
            "alerts": [],
            "thumb": None,
            "error": None,
        }
        if not url:
            cell["error"] = "Sin URL"
            cells.append(cell)
            continue
        try:
            url = _validate_rtsp_url(url)
        except HTTPException as exc:
            cell["error"] = str(exc.detail)
            cells.append(cell)
            continue

        stream = get_or_create_stream(url)
        frame = stream.read()
        if frame is None:
            cell["error"] = stream.last_error or "Sin frame"
            cell["connected"] = stream.connected
            cells.append(cell)
            continue

        frame = _resize_frame(frame, 480)
        with _detect_lock:
            detections, _ = det.predict(frame, conf=conf, imgsz=_DETECT_IMGSZ_MAX, annotate=False)
        payload = _build_response(
            detections,
            None,
            profile,
            frame_wh=(frame.shape[1], frame.shape[0]),
            required=req,
        )
        comp = payload.get("compliance") or {}
        cell.update(
            {
                "ok": True,
                "connected": True,
                "compliant": comp.get("compliant"),
                "missing": comp.get("missing") or [],
                "alerts": payload.get("alerts") or [],
                "thumb": _thumb_b64(frame),
                "safety_score": payload.get("safety_score"),
            }
        )
        if not comp.get("compliant"):
            alert_count += 1
        cells.append(cell)

    return {
        "ok": True,
        "cells": cells,
        "summary": {"total": len(cells), "alerts": alert_count, "online": sum(1 for c in cells if c.get("connected"))},
    }


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
    threshold: float = Form(0.33),
    return_image: str = Form("false"),
) -> JSONResponse:
    data = await file.read()
    if not data:
        raise HTTPException(400, "Archivo vacío")
    if not _detect_lock.acquire(blocking=False):
        return JSONResponse(
            {"ok": False, "busy": True, "error": "IA ocupada, esperá un momento."},
            status_code=429,
        )
    try:
        try:
            frame = decode_image_bytes(data)
        except ValueError as exc:
            raise HTTPException(400, str(exc)) from exc
        reg = IdentityRegistry.peek()
        if reg is None:
            threading.Thread(target=IdentityRegistry.get, name="id-load", daemon=True).start()
            return JSONResponse(
                {
                    "ok": False,
                    "booting": True,
                    "error": "Reconocimiento facial cargando…",
                    "matches": [],
                    "identified": None,
                    "faces_detected": 0,
                    "gallery_size": 0,
                },
                status_code=503,
            )
        h, w = frame.shape[:2]
        max_side = 480
        if max(h, w) > max_side:
            scale = max_side / max(h, w)
            frame = cv2.resize(frame, (int(w * scale), int(h * scale)))
        thr = max(0.25, min(0.7, float(threshold or 0.33)))
        result = IdentityService().identify(frame, threshold=thr)
        annotated = result.pop("annotated", None)
        want_img = str(return_image).lower() in ("1", "true", "yes", "on")
        if want_img and annotated is not None:
            jpeg = encode_jpeg(annotated, quality=72)
            result["image_b64"] = base64.b64encode(jpeg).decode("ascii")
        return JSONResponse(result)
    finally:
        _detect_lock.release()


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

            detections, annotated = det.predict(
                frame, conf=conf, imgsz=_DETECT_IMGSZ_MAX, annotate=True
            )
            jpeg = encode_jpeg(annotated, quality=68)
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