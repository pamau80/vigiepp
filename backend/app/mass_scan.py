"""Barrido masivo: captura RTSP en paralelo + inferencia EPP serial (lock)."""

from __future__ import annotations

import logging
import threading
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any

import numpy as np

from .detector import PPEDetector
from .profiles import parse_required_list
from .stream_rtsp import get_or_create_stream

logger = logging.getLogger("vigiepp.mass_scan")

_FETCH_WORKERS = 4


def _resize_frame(frame: np.ndarray, max_dim: int = 480) -> np.ndarray:
    import cv2

    h, w = frame.shape[:2]
    if max(h, w) <= max_dim:
        return frame
    scale = max_dim / max(h, w)
    return cv2.resize(frame, (int(w * scale), int(h * scale)))


def _fetch_frame(
    ch: dict[str, Any],
    validate_rtsp_url: Callable[[str], str],
) -> tuple[dict[str, Any], np.ndarray | None]:
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
        return cell, None
    try:
        url = validate_rtsp_url(url)
    except Exception as exc:  # noqa: BLE001
        cell["error"] = str(exc)
        return cell, None
    try:
        stream = get_or_create_stream(url)
    except RuntimeError as exc:
        cell["error"] = str(exc)
        return cell, None
    frame = stream.read()
    if frame is None:
        cell["error"] = stream.last_error or "Sin frame"
        cell["connected"] = stream.connected
        return cell, None
    return cell, _resize_frame(frame)


def run_mass_scan(
    enabled: list[dict[str, Any]],
    *,
    profile: str,
    conf: float,
    required: str,
    validate_rtsp_url: Callable[[str], str],
    detect_lock: threading.Lock,
    detect_imgsz_max: int,
    build_response: Callable[..., dict[str, Any]],
    compliance_cell_fields: Callable[[dict[str, Any]], dict[str, Any]],
    thumb_b64: Callable[[np.ndarray], str],
) -> dict[str, Any]:
    if not enabled:
        return {"ok": True, "cells": [], "summary": {"total": 0, "alerts": 0, "online": 0}}

    det = PPEDetector.get()
    req = parse_required_list(required)
    fetched: list[tuple[dict[str, Any], np.ndarray | None]] = []
    workers = min(_FETCH_WORKERS, max(1, len(enabled)))

    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(_fetch_frame, ch, validate_rtsp_url): ch for ch in enabled}
        for fut in as_completed(futures):
            ch = futures[fut]
            try:
                cell, frame = fut.result()
            except Exception as exc:
                logger.exception("fetch canal %s falló", ch.get("id"))
                cell = {
                    "id": ch.get("id"),
                    "name": ch.get("name"),
                    "url": ch.get("url"),
                    "ok": False,
                    "error": str(exc),
                }
                frame = None
            fetched.append((cell, frame))

    cells: list[dict[str, Any]] = []
    alert_count = 0
    for cell, frame in fetched:
        if frame is None:
            cells.append(cell)
            continue
        with detect_lock:
            detections, _ = det.predict(frame, conf=conf, imgsz=detect_imgsz_max, annotate=False)
        payload = build_response(
            detections,
            None,
            profile,
            frame_wh=(frame.shape[1], frame.shape[0]),
            required=req,
            source_id=f"watchlist:{cell.get('id') or 'unknown'}",
        )
        fields = compliance_cell_fields(payload)
        cell.update(
            {
                "ok": True,
                "connected": True,
                "compliant": fields.get("compliant"),
                "missing": fields.get("missing") or [],
                "alerts": fields.get("alerts") or [],
                "actions": fields.get("actions") or [],
                "thumb": thumb_b64(frame),
                "safety_score": payload.get("safety_score"),
            }
        )
        if not fields.get("compliant"):
            alert_count += 1
        cells.append(cell)

    return {
        "ok": True,
        "cells": cells,
        "summary": {
            "total": len(cells),
            "alerts": alert_count,
            "online": sum(1 for c in cells if c.get("connected")),
        },
    }
