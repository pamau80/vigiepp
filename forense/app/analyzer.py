"""Análisis de frames reutilizando motor VigiEPP (solo lectura)."""

from __future__ import annotations

import logging
from typing import Any, Callable

from .config import DEFAULT_PROFILE

logger = logging.getLogger("vigiepp.forense.analyzer")


def _format_ts(sec: float) -> str:
    s = int(sec)
    h, rem = divmod(s, 3600)
    m, s = divmod(rem, 60)
    return f"{h:02d}:{m:02d}:{s:02d}"


def analyze_frame(
    frame_bgr,
    *,
    time_sec: float,
    source_id: str,
    profile: str = DEFAULT_PROFILE,
    meters_per_pixel: float = 0.045,
) -> dict[str, Any]:
    """Ejecuta detección + compliance + zonas + acciones sobre un frame."""
    from app import actions as actions_mod
    from app.detect_pipeline import build_response
    from app.detector import PPEDetector, encode_jpeg

    h, w = frame_bgr.shape[:2]
    det = PPEDetector.get()
    detections, _ = det.predict(frame_bgr, annotate=False, imgsz=256)

    # Calibración temporal para proximidad en metros (sin persistir en VigiEPP)
    settings = actions_mod.get_settings()
    settings["meters_per_pixel"] = meters_per_pixel

    resp = build_response(
        detections,
        None,
        profile,
        frame_wh=(w, h),
        source_id=source_id,
    )
    events: list[dict[str, Any]] = []

    for tr in (resp.get("actions") or {}).get("triggered") or []:
        events.append(
            {
                "time_sec": time_sec,
                "time_label": _format_ts(time_sec),
                "type": "action",
                "severity": tr.get("severity"),
                "message": tr.get("message") or tr.get("rule_name"),
                "rule_id": tr.get("rule_id"),
            }
        )

    comp = resp.get("compliance") or {}
    if not comp.get("overall_compliant") and (comp.get("persons") or comp.get("alerts")):
        events.append(
            {
                "time_sec": time_sec,
                "time_label": _format_ts(time_sec),
                "type": "epp_non_compliant",
                "severity": "high",
                "message": comp.get("summary") or "Incumplimiento EPP",
            }
        )

    for zalert in (resp.get("zones") or {}).get("alerts") or []:
        events.append(
            {
                "time_sec": time_sec,
                "time_label": _format_ts(time_sec),
                "type": "zone",
                "severity": zalert.get("severity", "medium"),
                "message": zalert.get("message") or "Alerta de zona",
            }
        )

    keyframe_jpeg = None
    if events:
        keyframe_jpeg = encode_jpeg(frame_bgr, quality=78)

    return {
        "time_sec": time_sec,
        "time_label": _format_ts(time_sec),
        "detection_count": len(detections),
        "events": events,
        "keyframe_jpeg": keyframe_jpeg,
        "compliance": comp,
    }


def run_analysis(
    samples,
    *,
    job_id: str,
    profile: str,
    meters_per_pixel: float,
    progress_cb: Callable[[int, str], None] | None = None,
) -> dict[str, Any]:
    source_id = f"forense:{job_id}"
    timeline: list[dict[str, Any]] = []
    keyframes: list[dict[str, Any]] = []
    total = len(samples)

    for i, sample in enumerate(samples):
        if progress_cb:
            pct = int(10 + (80 * (i + 1) / max(total, 1)))
            progress_cb(pct, f"Analizando frame {i + 1}/{total}")
        try:
            result = analyze_frame(
                sample.frame_bgr,
                time_sec=sample.time_sec,
                source_id=source_id,
                profile=profile,
                meters_per_pixel=meters_per_pixel,
            )
            for ev in result.get("events") or []:
                timeline.append(ev)
            if result.get("keyframe_jpeg"):
                keyframes.append(
                    {
                        "time_sec": sample.time_sec,
                        "time_label": result["time_label"],
                        "jpeg": result["keyframe_jpeg"],
                        "events": [e.get("message") for e in result.get("events") or []],
                    }
                )
        except Exception:
            logger.exception("Frame %s falló en job %s", sample.index, job_id)

    timeline.sort(key=lambda e: e.get("time_sec", 0))
    return {"timeline": timeline, "keyframes": keyframes, "event_count": len(timeline)}
