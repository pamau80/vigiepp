"""Análisis multi-cámara con sincronización por offset temporal."""

from __future__ import annotations

from typing import Any, Callable

from .analyzer import run_analysis
from .sampler import adaptive_sample_video


def merge_analyses(parts: list[dict[str, Any]]) -> dict[str, Any]:
    timeline: list[dict] = []
    keyframes: list[dict] = []
    track_speeds: list[dict] = []
    speed_series: list[dict] = []
    speed_violations: list[dict] = []
    proximity_events: list[dict] = []
    tracks: list[dict] = []
    heatmap = False
    frame_w, frame_h = 0, 0

    for part in parts:
        timeline.extend(part.get("timeline") or [])
        keyframes.extend(part.get("keyframes") or [])
        kin = part.get("kinematics") or {}
        track_speeds.extend(kin.get("track_speeds") or [])
        speed_violations.extend(kin.get("speed_violations") or [])
        proximity_events.extend(kin.get("proximity_events") or [])
        speed_series.extend(part.get("speed_series") or [])
        tracks.extend(part.get("tracks") or [])
        heatmap = heatmap or bool(part.get("heatmap"))
        fs = part.get("frame_size") or {}
        frame_w = max(frame_w, int(fs.get("w") or 0))
        frame_h = max(frame_h, int(fs.get("h") or 0))

    timeline.sort(key=lambda e: e.get("time_sec", 0))
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
        "tracks": tracks,
        "heatmap": heatmap,
        "frame_size": {"w": frame_w, "h": frame_h},
        "sources_count": len(parts),
    }


def run_multi_source_analysis(
    sources: list[dict[str, Any]],
    *,
    job_id: str,
    profile: str,
    meters_per_pixel: float,
    max_machinery_kmh: float,
    max_person_kmh: float,
    min_distance_m: float,
    heatmap_path,
    progress_cb: Callable[[int, str], None] | None = None,
    sample_kw: dict[str, Any] | None = None,
    imgsz: int = 320,
) -> dict[str, Any]:
    """sources: [{path, offset_sec, label}]"""
    sample_kw = sample_kw or {}
    parts: list[dict[str, Any]] = []
    n = len(sources)
    for idx, src in enumerate(sources):
        label = src.get("label") or f"Cam {idx + 1}"
        offset = float(src.get("offset_sec") or 0)
        samples, _ = adaptive_sample_video(src["path"], **sample_kw)
        for s in samples:
            s.time_sec += offset

        span = int(80 / max(n, 1))
        base = 10 + idx * span

        def _cb(pct: int, msg: str, _base=base, _span=span) -> None:
            if progress_cb:
                progress_cb(min(90, _base + int(_span * (pct - 10) / 80)), msg)

        part = run_analysis(
            samples,
            job_id=job_id,
            profile=profile,
            meters_per_pixel=meters_per_pixel,
            max_machinery_kmh=max_machinery_kmh,
            max_person_kmh=max_person_kmh,
            min_distance_m=min_distance_m,
            heatmap_path=heatmap_path if idx == 0 else None,
            source_suffix=f"cam{idx}",
            camera_label=label,
            progress_cb=_cb,
            progress_base=base,
            progress_span=span,
            imgsz=imgsz,
        )
        parts.append(part)
    return merge_analyses(parts)
