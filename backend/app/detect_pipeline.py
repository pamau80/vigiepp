"""Pipeline detección EPP + identidad (HTTP, RTSP, WebSocket, masivo)."""

from __future__ import annotations

import base64
import logging
import os
import threading
import time
from dataclasses import asdict
from datetime import UTC, datetime
from typing import Any

import cv2
import numpy as np
from fastapi import HTTPException
from fastapi.responses import JSONResponse

from . import exposure as exposure_mod
from . import inference as inference_mod
from . import metrics as metrics_mod
from . import notifications as notif_mod
from . import zones as zones_mod
from .compliance import evaluate
from .detector import PPEDetector, decode_image_bytes, encode_jpeg
from .identity import IdentityRegistry, IdentityService
from .profiles import get_profile
from .scanlog import ScanEvent, log_scan

logger = logging.getLogger("vigiepp.detect")

_last_scan_log: dict[str, tuple[float, bool]] = {}
SCAN_DEBOUNCE_S = float(os.getenv("VIGIEPP_SCAN_DEBOUNCE", "12"))
detect_lock = threading.Lock()
DETECT_IMGSZ_MAX = int(os.getenv("VIGIEPP_IMGSZ_MAX", "256"))

def validate_rtsp_url(url: str) -> str:
    from fastapi import HTTPException

    try:
        from .rtsp_security import validate_rtsp_url as _validate

        return _validate(url)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc





def build_response(
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
        live_score = round(avg * 100)
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


def identify_on_frame(frame: np.ndarray, threshold: float = 0.42) -> dict[str, Any] | None:
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
    except Exception:
        logger.exception("Identificación en detect falló")
        return None


def maybe_log(
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
    if prev and (now - prev[0]) < SCAN_DEBOUNCE_S and prev[1] == compliant:
        # Misma persona/estado reciente: solo intentar notify (tiene su propio cooldown)
        try:
            if identity:
                notif_mod.maybe_notify_scan(identity, compliance_block, profile)
        except Exception:
            logger.exception("Notificación automática falló")
        return None

    _last_scan_log[key] = (now, compliant)

    evidence_id = None
    if identity and not compliant and frame_bgr is not None:
        try:
            jpeg = encode_jpeg(frame_bgr, quality=72)
            evidence_id = evidence_mod.save_evidence_jpeg(jpeg)
        except Exception:
            logger.exception("No se pudo guardar evidencia")

    if identity:
        missing: list[str] = []
        for p in persons:
            missing.extend(p.get("missing") or [])
        log_scan(
            ScanEvent(
                ts=datetime.now(UTC).isoformat(),
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
    except Exception:
        logger.exception("Notificación automática falló")
    try:
        from . import ehs_connectors as ehs_mod
        from . import tenants as tenants_mod

        if identity and not compliant:
            site = tenants_mod.get_site(tenants_mod.get_active_site_id())
            ehs_mod.push_incident(
                {
                    "ts": datetime.now(UTC).isoformat(),
                    "worker_name": identity.get("name"),
                    "worker_rut": identity.get("rut"),
                    "worker_id": identity.get("id"),
                    "profile": profile,
                    "compliant": compliant,
                    "summary": summary,
                    "missing": missing,
                    "evidence_id": evidence_id,
                    "site": (site or {}).get("name") or "",
                }
            )
    except Exception:
        logger.exception("EHS push falló")
    return evidence_id

def maybe_notify_unknown(profile: str, identity: dict | None) -> None:
    if not identity:
        return
    if identity.get("known"):
        return
    if not identity.get("faces_detected"):
        return
    try:
        notif_mod.maybe_notify_unknown(identity, profile)
    except Exception:
        logger.exception("Notificación de desconocido falló")


def draw_identity(frame: np.ndarray, identity: dict[str, Any] | None) -> np.ndarray:
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



def detect_frame(
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
    t0 = time.perf_counter()
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
    imgsz_use = max(224, min(int(imgsz or DETECT_IMGSZ_MAX), DETECT_IMGSZ_MAX))
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
            identity = identify_on_frame(frame, threshold=thr)
        if identity and return_image:
            annotated = draw_identity(annotated, identity)
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
        except Exception:
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
            annotated = draw_identity(annotated, identity)

    jpeg = encode_jpeg(annotated, quality=68) if return_image else None
    payload = build_response(
        detections,
        jpeg,
        profile,
        identity=identity,
        frame_wh=(frame.shape[1], frame.shape[0]),
        required=required,
    )
    if identify and identity and identity.get("known"):
        evid = maybe_log(profile, payload["compliance"], identity, frame_bgr=annotated)
        if evid:
            payload["evidence_id"] = evid
    elif identify and identity and not identity.get("known"):
        maybe_notify_unknown(profile, identity)
    try:
        notif_mod.maybe_notify_zones(
            identity,
            (payload.get("zones") or {}).get("alerts") or [],
            profile,
        )
    except Exception:
        logger.exception("Notificación de zona falló")
    try:
        access = notif_mod.maybe_access_gate(identity, payload["compliance"], profile)
        if access is not None:
            payload["access"] = access
    except Exception:
        logger.exception("Access gate falló")
    metrics_mod.inc("detect_requests_total")
    metrics_mod.observe_detect_ms((time.perf_counter() - t0) * 1000.0)
    return JSONResponse(payload)



def thumb_b64(frame: np.ndarray, max_w: int = 320) -> str:
    h, w = frame.shape[:2]
    if w > max_w:
        scale = max_w / w
        frame = cv2.resize(frame, (max_w, int(h * scale)))
    jpeg = encode_jpeg(frame, quality=72)
    return base64.b64encode(jpeg).decode("ascii")


def compliance_cell_fields(payload: dict[str, Any]) -> dict[str, Any]:
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


