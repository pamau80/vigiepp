"""Cola de trabajos forenses (almacenamiento aislado)."""

from __future__ import annotations

import json
import logging
import shutil
import threading
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .comparison import compare_jobs
from .config import BUILD, JOBS_DIR, ensure_dirs
from .export import committee_section, export_case_bundle, push_to_ehs
from .knowledge import apply_knowledge_insights, match_knowledge_for_job, reinforce_knowledge_from_job
from .multi_source import run_multi_source_analysis
from .pdf_export import export_report_pdf
from .report import build_report_markdown, maybe_enrich_with_llm
from .sampler import adaptive_sample_video
from .templates import inference_settings, resolve_template

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
    case_notes: str = "",
    template_id: str = "general",
    profile: str | None = None,
    meters_per_pixel: float | None = None,
    max_machinery_kmh: float | None = None,
    max_person_kmh: float | None = None,
    min_distance_m: float | None = None,
    reference_job_id: str | None = None,
    extra_sources: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    tpl = resolve_template(template_id)
    ensure_dirs()
    job_id = uuid.uuid4().hex[:12]
    job_dir = _job_dir(job_id)
    job_dir.mkdir(parents=True, exist_ok=True)

    sources_dir = job_dir / "sources"
    sources_dir.mkdir(exist_ok=True)
    ext = Path(filename).suffix.lower() or ".mp4"
    primary_path = sources_dir / f"cam0{ext}"
    primary_path.write_bytes(video_bytes)

    source_meta = [{"label": "Cam 1", "offset_sec": 0.0, "path": str(primary_path), "filename": filename}]
    for i, extra in enumerate(extra_sources or [], start=1):
        ex_ext = Path(extra.get("filename") or "video.mp4").suffix.lower() or ".mp4"
        p = sources_dir / f"cam{i}{ex_ext}"
        p.write_bytes(extra["bytes"])
        source_meta.append(
            {
                "label": extra.get("label") or f"Cam {i + 1}",
                "offset_sec": float(extra.get("offset_sec") or 0),
                "path": str(p),
                "filename": extra.get("filename") or f"cam{i}{ex_ext}",
            }
        )

    job = {
        "id": job_id,
        "build": BUILD,
        "title": title.strip() or "Análisis forense",
        "site": site.strip() or "Faena",
        "case_notes": case_notes.strip(),
        "template_id": tpl["id"],
        "template_name": tpl["name"],
        "profile": profile or tpl["profile"],
        "meters_per_pixel": meters_per_pixel if meters_per_pixel is not None else tpl["meters_per_pixel"],
        "max_machinery_kmh": max_machinery_kmh if max_machinery_kmh is not None else tpl["max_machinery_kmh"],
        "max_person_kmh": max_person_kmh if max_person_kmh is not None else tpl["max_person_kmh"],
        "min_distance_m": min_distance_m if min_distance_m is not None else tpl["min_distance_m"],
        "reference_job_id": (reference_job_id or "").strip() or None,
        "sources": source_meta,
        "filename": filename,
        "status": "queued",
        "progress": 0,
        "progress_message": "En cola",
        "created_at": datetime.now(UTC).isoformat(),
        "updated_at": datetime.now(UTC).isoformat(),
        "meta": {},
        "analysis": {},
        "comparison": {},
        "report_md": "",
        "committee_md": "",
    }
    with _lock:
        _jobs[job_id] = job
        _save_job(job)

    threading.Thread(target=_process_job, args=(job_id,), daemon=True).start()
    return job


def _process_job(job_id: str) -> None:
    job = _jobs.get(job_id)
    if not job:
        return
    try:
        job["status"] = "processing"
        _set_progress(job_id, 5, "Preparando fuentes de video")

        inf = inference_settings(job.get("template_id"))
        sample_kw = {
            "base_interval_sec": inf.get("base_interval_sec", 0.45),
            "motion_threshold": inf.get("motion_threshold", 11.0),
            "burst_interval_sec": inf.get("burst_interval_sec", 0.1),
            "burst_duration_sec": inf.get("burst_duration_sec", 4.5),
            "max_frames": int(inf.get("max_frames", 5000)),
        }
        imgsz = int(inf.get("imgsz", 320))

        sources = job.get("sources") or []
        if len(sources) <= 1:
            path = sources[0]["path"] if sources else ""
            samples, meta = adaptive_sample_video(path, **sample_kw)
            job["meta"] = meta
            from .analyzer import run_analysis

            analysis = run_analysis(
                samples,
                job_id=job_id,
                profile=job["profile"],
                meters_per_pixel=float(job["meters_per_pixel"]),
                max_machinery_kmh=float(job["max_machinery_kmh"]),
                max_person_kmh=float(job["max_person_kmh"]),
                min_distance_m=float(job["min_distance_m"]),
                heatmap_path=_job_dir(job_id) / "heatmap.jpg",
                progress_cb=lambda p, m: _set_progress(job_id, p, m),
                imgsz=imgsz,
            )
        else:
            job["meta"] = {"sources": len(sources), "multi_camera": True}
            analysis = run_multi_source_analysis(
                sources,
                job_id=job_id,
                profile=job["profile"],
                meters_per_pixel=float(job["meters_per_pixel"]),
                max_machinery_kmh=float(job["max_machinery_kmh"]),
                max_person_kmh=float(job["max_person_kmh"]),
                min_distance_m=float(job["min_distance_m"]),
                heatmap_path=_job_dir(job_id) / "heatmap.jpg",
                progress_cb=lambda p, m: _set_progress(job_id, p, m),
                sample_kw=sample_kw,
                imgsz=imgsz,
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
            "kinematics": analysis.get("kinematics") or {},
            "speed_series": analysis.get("speed_series") or [],
            "heatmap": analysis.get("heatmap", False),
            "frame_size": analysis.get("frame_size") or {},
            "sources_count": analysis.get("sources_count", len(sources)),
        }

        ref_id = job.get("reference_job_id")
        if ref_id:
            ref_job = get_job(ref_id)
            job["comparison"] = compare_jobs(job, ref_job)
        else:
            job["comparison"] = {"available": False}

        _set_progress(job_id, 90, "Consultando biblioteca de situaciones")
        knowledge_matches = match_knowledge_for_job(job)
        job["knowledge"] = apply_knowledge_insights(job, knowledge_matches)
        reinforced = reinforce_knowledge_from_job(job, knowledge_matches)
        if reinforced:
            job["knowledge"]["reinforced_entries"] = reinforced

        _set_progress(job_id, 92, "Generando informes")

        narrative = maybe_enrich_with_llm(job)
        if narrative:
            job["llm_narrative"] = narrative
        job["report_md"] = build_report_markdown(job)
        job["committee_md"] = committee_section(job)
        full_md = job["report_md"] + "\n\n" + job["committee_md"]
        (_job_dir(job_id) / "report.md").write_text(full_md, encoding="utf-8")
        (_job_dir(job_id) / "committee.md").write_text(job["committee_md"], encoding="utf-8")
        try:
            export_report_pdf({**job, "report_md": full_md}, _job_dir(job_id) / "report.pdf")
        except Exception as pdf_exc:
            logger.warning("PDF forense omitido para %s: %s", job_id, pdf_exc)
            job["pdf_error"] = str(pdf_exc)
        try:
            export_case_bundle(job, _job_dir(job_id) / "case_bundle.zip")
        except Exception as bundle_exc:
            logger.warning("Bundle forense omitido para %s: %s", job_id, bundle_exc)
            job["bundle_error"] = str(bundle_exc)

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


def export_job_ehs(job_id: str) -> list[dict[str, Any]]:
    job = get_job(job_id)
    if not job:
        return [{"ok": False, "error": "Trabajo no encontrado"}]
    results = push_to_ehs(job)
    job["ehs_push"] = results
    job["updated_at"] = datetime.now(UTC).isoformat()
    _save_job(job)
    return results


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


def heatmap_path(job_id: str) -> Path | None:
    p = _job_dir(job_id) / "heatmap.jpg"
    return p if p.is_file() else None


def report_pdf_path(job_id: str) -> Path | None:
    p = _job_dir(job_id) / "report.pdf"
    return p if p.is_file() else None


def case_bundle_path(job_id: str) -> Path | None:
    p = _job_dir(job_id) / "case_bundle.zip"
    return p if p.is_file() else None


def committee_md_path(job_id: str) -> Path | None:
    p = _job_dir(job_id) / "committee.md"
    return p if p.is_file() else None
