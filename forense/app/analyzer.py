"""Análisis de frames reutilizando motor VigiEPP (solo lectura)."""

from __future__ import annotations

import logging
from typing import Any, Callable

from .charts import build_speed_series, tracks_to_json
from .config import DEFAULT_PROFILE
from .frame_store import append_frame, clear_frames
from .heatmap import render_heatmap
from .kinematics import (
    compute_track_speeds,
    find_proximity_events,
    find_speed_violations,
    snapshot_proximity,
    snapshot_track_speeds,
)
from .detection_filter import filter_detections
from .event_feedback import filter_suppressed_events
from .scene_signals import detect_fire_smoke, fire_smoke_events
from .tracker import IoUTracker, _classify

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
    imgsz: int = 320,
    min_detection_confidence: float = 0.42,
    min_box_area_ratio: float = 0.0008,
) -> dict[str, Any]:
    """Ejecuta detección + compliance + zonas + acciones sobre un frame."""
    from app import actions as actions_mod
    from app.detect_pipeline import build_response
    from app.detector import PPEDetector, encode_jpeg

    h, w = frame_bgr.shape[:2]
    det = PPEDetector.get()
    detections, _ = det.predict(frame_bgr, annotate=False, imgsz=imgsz)
    detections = filter_detections(
        detections,
        w,
        h,
        min_confidence=min_detection_confidence,
        min_area_ratio=min_box_area_ratio,
    )

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
        for person in comp.get("persons") or []:
            missing = [str(m).lower() for m in (person.get("missing") or [])]
            if any("chaleco" in m or "vest" in m or "reflect" in m for m in missing):
                events.append(
                    {
                        "time_sec": time_sec,
                        "time_label": _format_ts(time_sec),
                        "type": "epp_reflective",
                        "severity": "high",
                        "message": "Persona sin chaleco/ropa reflectante de alta visibilidad",
                        "source": "detector",
                    }
                )
                break

    scene = detect_fire_smoke(frame_bgr)
    events.extend(fire_smoke_events(time_sec, _format_ts(time_sec), scene))

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

    events = filter_suppressed_events(events)

    keyframe_jpeg = None
    if events:
        keyframe_jpeg = encode_jpeg(frame_bgr, quality=78)
    elif scene.get("fire") or scene.get("smoke"):
        keyframe_jpeg = encode_jpeg(frame_bgr, quality=78)

    return {
        "time_sec": time_sec,
        "time_label": _format_ts(time_sec),
        "detection_count": len(detections),
        "detections": detections,
        "frame_w": w,
        "frame_h": h,
        "events": events,
        "keyframe_jpeg": keyframe_jpeg,
        "compliance": comp,
    }


def _serialize_detections(detections: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for det in detections:
        box = det.get("box")
        if not box or len(box) != 4:
            continue
        label = str(det.get("label_es") or det.get("label") or "")
        kind = _classify(label)
        out.append(
            {
                "label": label,
                "kind": kind,
                "box": [round(float(x), 1) for x in box],
                "confidence": round(float(det.get("confidence") or 0), 3),
            }
        )
    return out


def _build_frame_record(
    *,
    time_sec: float,
    time_label: str,
    frame_w: int,
    frame_h: int,
    detections: list[dict[str, Any]],
    tracker: IoUTracker,
    meters_per_pixel: float,
    min_distance_m: float,
) -> dict[str, Any]:
    tracks = tracker.all_tracks()
    dets = _serialize_detections(detections)
    speeds = snapshot_track_speeds(tracks, time_sec, meters_per_pixel=meters_per_pixel)
    prox = snapshot_proximity(
        tracks, time_sec, meters_per_pixel=meters_per_pixel, min_distance_m=min_distance_m
    )
    persons = sum(1 for d in dets if d["kind"] == "person")
    vehicles = sum(1 for d in dets if d["kind"] == "machinery")
    return {
        "time_sec": round(time_sec, 3),
        "time_label": time_label,
        "frame_w": frame_w,
        "frame_h": frame_h,
        "detections": dets,
        "tracks": tracker.active_snapshot(time_sec),
        "speeds": speeds,
        "proximity": prox,
        "counts": {"persons": persons, "vehicles": vehicles, "objects": len(dets)},
        "min_distance_m": round(min((p["distance_m"] for p in prox), default=999), 2),
    }


def run_analysis(
    samples,
    *,
    job_id: str,
    profile: str,
    meters_per_pixel: float,
    max_machinery_kmh: float = 15.0,
    max_person_kmh: float = 8.0,
    min_distance_m: float = 2.0,
    heatmap_path=None,
    source_suffix: str = "",
    camera_label: str = "Cám. 1",
    progress_cb: Callable[[int, str], None] | None = None,
    progress_base: int = 10,
    progress_span: int = 75,
    imgsz: int = 320,
    record_frames: bool = True,
    min_detection_confidence: float = 0.42,
    min_box_area_ratio: float = 0.0008,
) -> dict[str, Any]:
    suffix = f":{source_suffix}" if source_suffix else ""
    source_id = f"forense:{job_id}{suffix}"
    timeline: list[dict[str, Any]] = []
    keyframes: list[dict[str, Any]] = []
    tracker = IoUTracker()
    frame_w, frame_h = 0, 0
    total = len(samples)

    try:
        from .teach_bridge import ensure_custom_model_if_available

        ensure_custom_model_if_available()
    except Exception:
        logger.debug("Teach bridge no disponible", exc_info=True)

    if record_frames:
        clear_frames(job_id)

    for i, sample in enumerate(samples):
        if progress_cb:
            pct = int(progress_base + (progress_span * (i + 1) / max(total, 1)))
            progress_cb(pct, f"{camera_label}: frame {i + 1}/{total}")
        try:
            result = analyze_frame(
                sample.frame_bgr,
                time_sec=sample.time_sec,
                source_id=source_id,
                profile=profile,
                meters_per_pixel=meters_per_pixel,
                imgsz=imgsz,
                min_detection_confidence=min_detection_confidence,
                min_box_area_ratio=min_box_area_ratio,
            )
            frame_w = max(frame_w, int(result.get("frame_w") or 0))
            frame_h = max(frame_h, int(result.get("frame_h") or 0))
            tracker.update(sample.time_sec, result.get("detections") or [])
            if record_frames:
                frame_rec = _build_frame_record(
                    time_sec=sample.time_sec,
                    time_label=result["time_label"],
                    frame_w=int(result.get("frame_w") or 0),
                    frame_h=int(result.get("frame_h") or 0),
                    detections=result.get("detections") or [],
                    tracker=tracker,
                    meters_per_pixel=meters_per_pixel,
                    min_distance_m=min_distance_m,
                )
                append_frame(job_id, frame_rec)
            for ev in result.get("events") or []:
                ev["camera"] = camera_label
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

    if progress_cb:
        progress_cb(88, "Calculando cinemática y mapa de calor")

    tracks = tracker.all_tracks()
    track_speeds = compute_track_speeds(tracks, meters_per_pixel=meters_per_pixel)
    speed_series = build_speed_series(tracks, meters_per_pixel=meters_per_pixel)
    speed_violations = find_speed_violations(
        track_speeds,
        max_machinery_kmh=max_machinery_kmh,
        max_person_kmh=max_person_kmh,
    )
    proximity_events = find_proximity_events(
        tracks,
        meters_per_pixel=meters_per_pixel,
        min_distance_m=min_distance_m,
    )

    for sv in speed_violations:
        timeline.append(
            {
                "time_sec": 0,
                "time_label": "—",
                "type": "speed_violation",
                "severity": "high",
                "message": sv["message"],
            }
        )
    for pe in proximity_events:
        timeline.append(
            {
                "time_sec": pe["time_sec"],
                "time_label": _format_ts(pe["time_sec"]),
                "type": "proximity",
                "severity": "critical",
                "message": pe["message"],
            }
        )

    timeline.sort(key=lambda e: e.get("time_sec", 0))

    heatmap_ok = False
    if heatmap_path and frame_w and frame_h:
        heatmap_ok = render_heatmap(tracks, frame_w=frame_w, frame_h=frame_h, out_path=heatmap_path)

    return {
        "timeline": timeline,
        "keyframes": keyframes,
        "event_count": len(timeline),
        "kinematics": {
            "track_speeds": track_speeds,
            "speed_violations": speed_violations,
            "proximity_events": proximity_events,
            "tracks_count": len(tracks),
        },
        "speed_series": speed_series,
        "tracks": tracks_to_json(tracks),
        "frames_analyzed": total,
        "heatmap": heatmap_ok,
        "frame_size": {"w": frame_w, "h": frame_h},
    }
