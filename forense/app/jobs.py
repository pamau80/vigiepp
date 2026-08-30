"""Cola de trabajos forenses (almacenamiento aislado)."""

from __future__ import annotations

import json
import logging
import shutil
import threading
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Callable

from .analyzer import run_analysis
from .config import BUILD, JOBS_DIR, ensure_dirs
from .report import build_report_markdown, maybe_enrich_with_llm
from .sampler import adaptive_sample_video

logger = logging.getLogger("vigiepp.forense.jobs")
_lock = threading.Lock()
_jobs: dict[str, dict[str, Any]] = {}


def _job_dir(job_id: str) -> Path:
    return JOBS_DIR / job_id


def _save_job(job: dict[str, Any]) -> None:
    ensure_dirs()
    path = _job_dir(job["id"]) / "job.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    serializable = {k: v for k, v in job.items() if k != "analysis_raw"}
    path.write_text(json.dumps(serializable, ensure_ascii=False, indent=2), encoding="utf-8")


def _load_jobs_from_disk() -> None:
    ensure_dirs()
    for d in JOBS_DIR.iterdir():
        if not d.is_dir():
            continue
        jf = d / "job.json"
        if jf.is_file():
            try:
                job = json.loads(jf.read_text(encoding="utf-8"))
                _jobs[job["id"]] = job
            except json.JSONDecodeError:
                pass


def list_jobs() -> list[dict[str, Any]]:
    with _lock:
        if not _jobs:
            _load_jobs_from_disk()
        return sorted(_jobs.values(), key=lambda j: j.get("created_at", ""), reverse=True)


def get_job(job_id: str) -> dict[str, Any] | None:
    with _lock:
        if job_id not in _jobs:
            _load_jobs_from_disk()
        return _jobs.get(job_id)


def _set_progress(job_id: str, pct: int, message: str) -> None:
    job = _jobs.get(job_id)
    if not job:
        return
    job["progress"] = max(0, min(100, pct))
    job["progress_message"] = message
    _save_job(job)


def create_job(
    video_bytes: bytes,
    *,
    filename: str,
    title: str,
    site: str,
    profile: str,
    meters_per_pixel: float,
) -> dict[str, Any]:
    ensure_dirs()
    job_id = uuid.uuid4().hex[:12]
    job_dir = _job_dir(job_id)
    job_dir.mkdir(parents=True, exist_ok=True)
    ext = Path(filename).suffix.lower() or ".mp4"
    video_path = job_dir / f"source{ext}"
    video_path.write_bytes(video_bytes)

    job = {
        "id": job_id,
        "build": BUILD,
        "title": title.strip() or "Análisis forense",
        "site": site.strip() or "Faena",
        "profile": profile,
        "meters_per_pixel": meters_per_pixel,
        "filename": filename,
        "status": "queued",
        "progress": 0,
        "progress_message": "En cola",
        "created_at": datetime.now(UTC).isoformat(),
        "updated_at": datetime.now(UTC).isoformat(),
        "meta": {},
        "analysis": {},
        "report_md": "",
    }
    with _lock:
        _jobs[job_id] = job
        _save_job(job)

    threading.Thread(target=_process_job, args=(job_id, str(video_path)), daemon=True).start()
    return job


def _process_job(job_id: str, video_path: str) -> None:
    job = _jobs.get(job_id)
    if not job:
        return
    try:
        job["status"] = "processing"
        _set_progress(job_id, 5, "Muestreando video")

        samples, meta = adaptive_sample_video(video_path)
        job["meta"] = meta
        _set_progress(job_id, 10, f"Muestreados {len(samples)} frames")

        analysis = run_analysis(
            samples,
            job_id=job_id,
            profile=job["profile"],
            meters_per_pixel=float(job["meters_per_pixel"]),
            progress_cb=lambda p, m: _set_progress(job_id, p, m),
        )

        kf_dir = _job_dir(job_id) / "keyframes"
        kf_dir.mkdir(exist_ok=True)
        for i, kf in enumerate(analysis.get("keyframes") or []):
            jpeg = kf.pop("jpeg", None)
            if jpeg:
                p = kf_dir / f"kf_{i:03d}.jpg"
                p.write_bytes(jpeg)
                kf["image"] = p.name

        job["analysis"] = {
            "timeline": analysis.get("timeline") or [],
            "keyframes": analysis.get("keyframes") or [],
            "event_count": analysis.get("event_count", 0),
        }
        _set_progress(job_id, 92, "Generando informe IA")

        narrative = maybe_enrich_with_llm(job)
        if narrative:
            job["llm_narrative"] = narrative
        job["report_md"] = build_report_markdown(job)
        (_job_dir(job_id) / "report.md").write_text(job["report_md"], encoding="utf-8")

        job["status"] = "done"
        job["progress"] = 100
        job["progress_message"] = "Completado"
        job["updated_at"] = datetime.now(UTC).isoformat()
        _save_job(job)
    except Exception as exc:
        logger.exception("Job %s falló", job_id)
        job["status"] = "error"
        job["error"] = str(exc)
        job["progress_message"] = "Error"
        job["updated_at"] = datetime.now(UTC).isoformat()
        _save_job(job)


def delete_job(job_id: str) -> bool:
    with _lock:
        if job_id in _jobs:
            del _jobs[job_id]
        d = _job_dir(job_id)
        if d.exists():
            shutil.rmtree(d, ignore_errors=True)
            return True
    return False


def keyframe_path(job_id: str, name: str) -> Path | None:
    p = _job_dir(job_id) / "keyframes" / name
    return p if p.is_file() else None
