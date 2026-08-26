from __future__ import annotations

import cv2
from typing import Any

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse, Response

from .. import stream_rtsp as stream_mod
from ..detect_pipeline import (
    DETECT_IMGSZ_MAX,
    build_response,
    identify_on_frame,
    validate_rtsp_url,
)
from ..detector import PPEDetector, encode_jpeg
from ..profiles import parse_required_list
from pydantic import BaseModel

router = APIRouter(prefix="/api/rtsp", tags=["rtsp"])


class RTSPStartRequest(BaseModel):
    url: str
    profile: str = "general"
    conf: float = 0.35

@router.post("/start")
def rtsp_start(body: RTSPStartRequest) -> dict[str, Any]:
    url = validate_rtsp_url(body.url)
    try:
        stream = stream_mod.get_or_create_stream(url)
    except RuntimeError as exc:
        raise HTTPException(503, str(exc)) from exc
    return {
        "ok": True,
        "url": url,
        "connected": stream.connected,
        "error": stream.last_error,
        "hint": "Usa GET /api/rtsp/frame?url=...&profile=... para frames anotados",
    }


@router.get("/frame")
def rtsp_frame(
    url: str,
    profile: str = "general",
    conf: float = 0.35,
    identify: bool = False,
    required: str = "",
) -> JSONResponse:
    url = validate_rtsp_url(url)
    stream = stream_mod.get_or_create_stream(url)
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
    identity = None
    detections: list = []
    if identify:
        identity = identify_on_frame(frame)
    else:
        detections, _annotated = det.predict(
            frame, conf=conf, imgsz=DETECT_IMGSZ_MAX, annotate=False
        )
    payload = build_response(
        detections,
        None,
        profile,
        identity=identity,
        frame_wh=(frame.shape[1], frame.shape[0]),
        required=parse_required_list(required),
    )
    return JSONResponse(payload)


@router.post("/stop")
def rtsp_stop(body: RTSPStartRequest) -> dict[str, Any]:
    stream_mod.stop_stream(body.url)
    return {"ok": True}


@router.get("/jpeg")
def rtsp_jpeg(url: str, max_w: int = 480) -> Response:
    url = validate_rtsp_url(url)
    stream = stream_mod.get_or_create_stream(url)
    frame = stream.read()
    if frame is None:
        raise HTTPException(202, stream.last_error or "Esperando frame RTSP")
    h, w = frame.shape[:2]
    if w > max_w:
        scale = max_w / w
        frame = cv2.resize(frame, (max_w, int(h * scale)))
    return Response(content=encode_jpeg(frame, quality=80), media_type="image/jpeg")


