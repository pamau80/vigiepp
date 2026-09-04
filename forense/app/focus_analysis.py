"""Re-análisis de la ventana de enfoque en casos existentes."""

from __future__ import annotations

import logging
from typing import Any

from .detection_filter import strict_inference_overrides
from .sampler import sample_window_frames
from .templates import inference_settings

logger = logging.getLogger("vigiepp.forense.focus_analysis")


def _in_window(time_sec: float, start: float, end: float) -> bool:
    return start <= float(time_sec) <= end


def merge_focus_timeline(
    existing: list[dict[str, Any]],
    new_events: list[dict[str, Any]],
    *,
    from_sec: float,
    until_sec: float,
) -> list[dict[str, Any]]:
    kept = [e for e in existing if not _in_window(float(e.get("time_sec") or 0), from_sec, until_sec)]
    merged = kept + list(new_events)
    merged.sort(key=lambda e: float(e.get("time_sec") or 0))
    return merged


def merge_focus_keyframes(
    existing: list[dict[str, Any]],
    new_items: list[dict[str, Any]],
    *,
    from_sec: float,
    until_sec: float,
) -> list[dict[str, Any]]:
    kept = [k for k in existing if not _in_window(float(k.get("time_sec") or 0), from_sec, until_sec)]
    merged = kept + [{k: v for k, v in item.items() if k != "jpeg"} for item in new_items]
    merged.sort(key=lambda k: float(k.get("time_sec") or 0))
    return merged


def analyze_focus_window(
    job: dict[str, Any],
    video_path: str,
    *,
    from_sec: float,
    until_sec: float,
    job_dir,
    progress_cb=None,
) -> dict[str, Any]:
    """YOLO + reglas solo en la ventana indicada."""
    from .analyzer import run_analysis

    inf = inference_settings(job.get("template_id"))
    inf = {**inf, **strict_inference_overrides(bool(job.get("strict_detection")))}
    samples = sample_window_frames(
        video_path,
        focus_from_sec=from_sec,
        focus_until_sec=until_sec,
        interval_sec=float(inf.get("focus_burst_interval_sec", 0.12)),
        max_frames=min(120, int(inf.get("max_frames", 5000))),
    )
    if not samples:
        return {"timeline": [], "keyframes": [], "event_count": 0, "frames_analyzed": 0}

    if progress_cb:
        progress_cb(40, f"Analizando {len(samples)} fotogramas en ventana de enfoque")

    partial = run_analysis(
        samples,
        job_id=job["id"],
        profile=job["profile"],
        meters_per_pixel=float(job["meters_per_pixel"]),
        max_machinery_kmh=float(job["max_machinery_kmh"]),
        max_person_kmh=float(job["max_person_kmh"]),
        min_distance_m=float(job["min_distance_m"]),
        heatmap_path=None,
        progress_cb=lambda p, m: progress_cb(min(85, p), m) if progress_cb else None,
        progress_base=40,
        progress_span=45,
        imgsz=int(inf.get("imgsz", 320)),
        record_frames=False,
        min_detection_confidence=float(inf.get("min_detection_confidence", 0.42)),
        min_box_area_ratio=float(inf.get("min_box_area_ratio", 0.0008)),
    )
    return partial
