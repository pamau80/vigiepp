from __future__ import annotations

import hmac
import json
import logging

from fastapi import (
    APIRouter,
    File,
    Form,
    HTTPException,
    UploadFile,
    WebSocket,
    WebSocketDisconnect,
)
from fastapi.responses import JSONResponse

from .. import auth as auth_mod
from .. import metrics as metrics_mod
from ..detect_pipeline import (
    DETECT_IMGSZ_MAX,
    build_response,
    detect_frame,
    detect_lock,
)
from ..detector import PPEDetector, decode_image_bytes, encode_jpeg
from ..profiles import parse_required_list

logger = logging.getLogger("vigiepp.detect")

router = APIRouter(tags=["detect"])


@router.post("/api/detect")
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
    if not detect_lock.acquire(blocking=False):
        metrics_mod.inc("detect_busy_total")
        return JSONResponse(
            {"ok": False, "busy": True, "error": "IA ocupada, esperá un momento."},
            status_code=429,
        )
    try:
        return detect_frame(
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
        detect_lock.release()


@router.websocket("/ws/detect")
async def ws_detect(websocket: WebSocket) -> None:
    """Recibe frames JPEG binarios; responde JSON con resultado + imagen anotada."""
    if auth_mod.auth_enabled():
        token = websocket.cookies.get(auth_mod.COOKIE_NAME) or websocket.query_params.get("token")
        header = websocket.headers.get(auth_mod.HEADER_NAME.lower()) or websocket.headers.get("authorization")
        if header and header.lower().startswith("bearer "):
            token = header[7:].strip()
        elif header:
            token = header.strip()
        ok = auth_mod.session_valid(token) or (
            bool(token)
            and auth_mod.api_key()
            and hmac.compare_digest(token, auth_mod.api_key() or "")
        )
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

            if not detect_lock.acquire(blocking=False):
                await websocket.send_json({"ok": False, "busy": True, "error": "IA ocupada"})
                continue
            try:
                detections, annotated = det.predict(
                    frame, conf=conf, imgsz=DETECT_IMGSZ_MAX, annotate=True
                )
                jpeg = encode_jpeg(annotated, quality=68)
                payload = build_response(detections, jpeg, profile)
                metrics_mod.inc("detect_requests_total")
                await websocket.send_json(payload)
            finally:
                detect_lock.release()
    except WebSocketDisconnect:
        logger.info("WebSocket cerrado")
    except Exception:
        logger.exception("Error en WebSocket")
        try:
            await websocket.close()
        except Exception:  # noqa: BLE001
            pass
