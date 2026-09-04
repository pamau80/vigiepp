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
from .focus_analysis import analyze_focus_window, merge_focus_keyframes, merge_focus_timeline as merge_focus_timeline_window
from .vision_timeline import events_from_vision_parsed, merge_vision_timeline
from .knowledge import apply_knowledge_insights, match_knowledge_for_job, reinforce_knowledge_from_job
from .multi_source import run_multi_source_analysis
from .path_safety import resolve_under, safe_job_id, safe_keyframe_name
from .pdf_export import export_report_pdf
from .report import build_report_markdown, maybe_enrich_with_llm
from .sampler import adaptive_sample_video, enrich_focus_window
from .event_feedback import (
    active_timeline,
    apply_review_state,
    ensure_event_ids,
    record_dismissal,
    remove_suppression_for_event,
    review_summary,
)
from .timeline_evidence import enrich_timeline_evidence
from .templates import inference_settings, resolve_template
from .video_formats import resolve_source_path, video_extension

logger = logging.getLogger("vigiepp.forense.jobs")
_lock = threading.Lock()
_jobs: dict[str, dict[str, Any]] = {}


def _job_dir(job_id: str) -> Path:
    safe = safe_job_id(job_id)
    if not safe:
        raise ValueError("job_id inválido")
    return JOBS_DIR / safe


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
    if not safe_job_id(job_id):
        return None
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


def _persist_keyframes(job_id: str, keyframes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Guarda JPEG en disco y deja solo referencias `image` en cada keyframe."""
    kf_dir = _job_dir(job_id) / "keyframes"
    kf_dir.mkdir(exist_ok=True)
    next_idx = len(list(kf_dir.glob("kf_*.jpg")))
    out: list[dict[str, Any]] = []
    for kf in keyframes:
        item = dict(kf)
        jpeg = item.pop("jpeg", None)
        if jpeg and not item.get("image"):
            name = f"kf_{next_idx:03d}.jpg"
            (kf_dir / name).write_bytes(jpeg)
            item["image"] = name
            next_idx += 1
        out.append(item)
    return out


def _regenerate_job_outputs(job_id: str) -> None:
    """Biblioteca, visión IA, informes y exportaciones tras actualizar análisis."""
    job = _jobs.get(job_id)
    if not job:
        return

    _set_progress(job_id, 90, "Consultando biblioteca de situaciones")
    knowledge_matches = match_knowledge_for_job(job)
    job["knowledge"] = apply_knowledge_insights(job, knowledge_matches)
    reinforced = reinforce_knowledge_from_job(job, knowledge_matches)
    if reinforced:
        job["knowledge"]["reinforced_entries"] = reinforced

    _set_progress(job_id, 91, "Interpretación visual IA (ventana de enfoque)")
    from .video_ai import analyze_job_with_vision

    vision = analyze_job_with_vision(job)
    if vision:
        job["video_ai"] = vision
        analysis = job.get("analysis") or {}
        v_events = events_from_vision_parsed(
            vision.get("parsed"),
            frames_used=vision.get("frames_meta"),
        )
        if v_events:
            timeline = merge_vision_timeline(analysis.get("timeline") or [], v_events)
            analysis["timeline"] = timeline
            analysis["event_count"] = len(timeline)
            job["analysis"] = analysis
    else:
        job.pop("video_ai", None)

    _set_progress(job_id, 92, "Generando informes")
    narrative = maybe_enrich_with_llm(job)
    if narrative:
        job["llm_narrative"] = narrative
    else:
        job.pop("llm_narrative", None)
    job["report_md"] = build_report_markdown(job)
    job["committee_md"] = committee_section(job)
    full_md = job["report_md"] + "\n\n" + job["committee_md"]
    job_dir = _job_dir(job_id)
    (job_dir / "report.md").write_text(full_md, encoding="utf-8")
    (job_dir / "committee.md").write_text(job["committee_md"], encoding="utf-8")
    try:
        export_report_pdf({**job, "report_md": full_md}, job_dir / "report.pdf")
    except Exception as pdf_exc:
        logger.warning("PDF forense omitido para %s: %s", job_id, pdf_exc)
        job["pdf_error"] = str(pdf_exc)
    try:
        export_case_bundle(job, job_dir / "case_bundle.zip")
    except Exception as bundle_exc:
        logger.warning("Bundle forense omitido para %s: %s", job_id, bundle_exc)
        job["bundle_error"] = str(bundle_exc)


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
    focus_description: str = "",
    focus_from_sec: float | None = None,
    focus_until_sec: float | None = None,
    strict_detection: bool = False,
) -> dict[str, Any]:
    tpl = resolve_template(template_id)
    ensure_dirs()
    job_id = uuid.uuid4().hex[:12]
    job_dir = _job_dir(job_id)
    job_dir.mkdir(parents=True, exist_ok=True)

    sources_dir = job_dir / "sources"
    sources_dir.mkdir(exist_ok=True)
    ext = video_extension(filename) or ".mp4"
    primary_path = sources_dir / f"cam0{ext}"
    primary_path.write_bytes(video_bytes)

    source_meta = [{"label": "Cám. 1", "offset_sec": 0.0, "path": str(primary_path), "filename": filename}]
    for i, extra in enumerate(extra_sources or [], start=1):
        ex_name = extra.get("filename") or "video.mp4"
        ex_ext = video_extension(ex_name) or ".mp4"
        p = sources_dir / f"cam{i}{ex_ext}"
        p.write_bytes(extra["bytes"])
        source_meta.append(
            {
                "label": extra.get("label") or f"Cám. {i + 1}",
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
        "focus_description": focus_description.strip(),
        "focus_from_sec": focus_from_sec,
        "focus_until_sec": focus_until_sec,
        "strict_detection": bool(strict_detection),
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
        ensure_web_playback(job_id)

        inf = inference_settings(job.get("template_id"))
        from .detection_filter import strict_inference_overrides

        inf = {**inf, **strict_inference_overrides(bool(job.get("strict_detection")))}
        sample_kw = {
            "base_interval_sec": inf.get("base_interval_sec", 0.45),
            "motion_threshold": inf.get("motion_threshold", 11.0),
            "burst_interval_sec": inf.get("burst_interval_sec", 0.1),
            "burst_duration_sec": inf.get("burst_duration_sec", 4.5),
            "max_frames": int(inf.get("max_frames", 5000)),
        }
        imgsz = int(inf.get("imgsz", 320))
        det_conf = float(inf.get("min_detection_confidence", 0.42))
        det_area = float(inf.get("min_box_area_ratio", 0.0008))
        focus_from = job.get("focus_from_sec")
        focus_until = job.get("focus_until_sec")
        has_focus = (
            focus_from is not None
            and focus_until is not None
            and float(focus_until) > float(focus_from)
        )

        sources = job.get("sources") or []
        if len(sources) <= 1:
            path = sources[0]["path"] if sources else ""
            samples, meta = adaptive_sample_video(path, **sample_kw)
            if has_focus:
                samples = enrich_focus_window(
                    samples,
                    path,
                    focus_from_sec=float(focus_from),
                    focus_until_sec=float(focus_until),
                    interval_sec=float(inf.get("focus_burst_interval_sec", 0.12)),
                )
                meta["focus_window"] = {
                    "from_sec": float(focus_from),
                    "until_sec": float(focus_until),
                    "extra_frames": meta.get("sampled_frames"),
                }
                meta["sampled_frames"] = len(samples)
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
                min_detection_confidence=det_conf,
                min_box_area_ratio=det_area,
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
            "tracks": analysis.get("tracks") or [],
            "frames_analyzed": analysis.get("frames_analyzed", 0),
            "heatmap": analysis.get("heatmap", False),
            "frame_size": analysis.get("frame_size") or {},
            "sources_count": analysis.get("sources_count", len(sources)),
        }
        analysis_block = job["analysis"]
        analysis_block["timeline"] = ensure_event_ids(analysis_block.get("timeline") or [])
        analysis_block["timeline"] = enrich_timeline_evidence(
            analysis_block["timeline"],
            analysis_block.get("keyframes") or [],
        )
        active = active_timeline(analysis_block["timeline"], job.get("event_feedback"))
        analysis_block["event_count"] = len(active)

        ref_id = job.get("reference_job_id")
        if ref_id:
            ref_job = get_job(ref_id)
            job["comparison"] = compare_jobs(job, ref_job)
        else:
            job["comparison"] = {"available": False}

        _regenerate_job_outputs(job_id)

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


def refocus_job(
    job_id: str,
    *,
    focus_description: str,
    focus_from_sec: float,
    focus_until_sec: float,
    strict_detection: bool | None = None,
) -> dict[str, Any]:
    """Re-analiza la ventana temporal indicada y regenera informe + IA visual."""
    job = get_job(job_id)
    if not job:
        raise FileNotFoundError("Trabajo no encontrado")
    if job.get("status") == "processing":
        raise RuntimeError("El trabajo ya está en proceso")
    sources = job.get("sources") or []
    if len(sources) != 1:
        raise ValueError("Re-enfoque disponible solo con una cámara")
    if focus_until_sec <= focus_from_sec:
        raise ValueError("La ventana de enfoque es inválida")

    video_path = sources[0].get("path") or ""
    if not video_path or not Path(video_path).is_file():
        raise FileNotFoundError("Video no encontrado")

    job["focus_description"] = focus_description.strip()
    job["focus_from_sec"] = float(focus_from_sec)
    job["focus_until_sec"] = float(focus_until_sec)
    if strict_detection is not None:
        job["strict_detection"] = bool(strict_detection)
    job["status"] = "processing"
    job["progress"] = 5
    job["progress_message"] = "Re-analizando ventana de enfoque"
    job.pop("error", None)
    job["updated_at"] = datetime.now(UTC).isoformat()
    _save_job(job)

    def in_thread() -> None:
        try:
            partial = analyze_focus_window(
                job,
                video_path,
                from_sec=float(focus_from_sec),
                until_sec=float(focus_until_sec),
                job_dir=_job_dir(job_id),
                progress_cb=lambda p, m: _set_progress(job_id, p, m),
            )
            analysis = job.get("analysis") or {}
            timeline = merge_focus_timeline_window(
                analysis.get("timeline") or [],
                partial.get("timeline") or [],
                from_sec=float(focus_from_sec),
                until_sec=float(focus_until_sec),
            )
            new_kf = _persist_keyframes(job_id, partial.get("keyframes") or [])
            keyframes = merge_focus_keyframes(
                analysis.get("keyframes") or [],
                new_kf,
                from_sec=float(focus_from_sec),
                until_sec=float(focus_until_sec),
            )
            job["analysis"] = {
                **analysis,
                "timeline": timeline,
                "keyframes": keyframes,
                "event_count": len(timeline),
                "frames_analyzed": int(analysis.get("frames_analyzed") or 0)
                + int(partial.get("frames_analyzed") or 0),
            }
            job["analysis"]["timeline"] = ensure_event_ids(job["analysis"]["timeline"])
            job["analysis"]["timeline"] = enrich_timeline_evidence(
                job["analysis"]["timeline"],
                job["analysis"]["keyframes"],
            )
            active = active_timeline(job["analysis"]["timeline"], job.get("event_feedback"))
            job["analysis"]["event_count"] = len(active)
            meta = job.get("meta") or {}
            meta["focus_refocus"] = {
                "from_sec": float(focus_from_sec),
                "until_sec": float(focus_until_sec),
                "extra_frames": int(partial.get("frames_analyzed") or 0),
                "extra_events": len(partial.get("timeline") or []),
            }
            job["meta"] = meta
            _regenerate_job_outputs(job_id)
            job["status"] = "done"
            job["progress"] = 100
            job["progress_message"] = "Re-enfoque completado"
            job["updated_at"] = datetime.now(UTC).isoformat()
            _save_job(job)
        except Exception as exc:
            logger.exception("Refocus %s falló", job_id)
            job["status"] = "error"
            job["error"] = str(exc)
            job["progress_message"] = "Error en re-enfoque"
            job["updated_at"] = datetime.now(UTC).isoformat()
            _save_job(job)

    threading.Thread(target=in_thread, daemon=True).start()
    return job


def reanalyze_job(job_id: str) -> dict[str, Any]:
    """Re-procesa el video completo con el pipeline actual (sin re-subir archivo)."""
    job = get_job(job_id)
    if not job:
        raise FileNotFoundError("Trabajo no encontrado")
    if job.get("status") == "processing":
        raise RuntimeError("El trabajo ya está en proceso")
    sources = job.get("sources") or []
    if not sources:
        raise FileNotFoundError("Sin fuentes de video")
    for src in sources:
        p = src.get("path") or ""
        if not p or not Path(p).is_file():
            raise FileNotFoundError("Video no encontrado")

    kf_dir = _job_dir(job_id) / "keyframes"
    if kf_dir.is_dir():
        shutil.rmtree(kf_dir, ignore_errors=True)
    heatmap = _job_dir(job_id) / "heatmap.jpg"
    if heatmap.is_file():
        heatmap.unlink(missing_ok=True)

    job["analysis"] = {}
    job.pop("video_ai", None)
    job.pop("llm_narrative", None)
    job["report_md"] = ""
    job["committee_md"] = ""
    job["status"] = "processing"
    job["progress"] = 2
    job["progress_message"] = "Re-analizando caso completo"
    job.pop("error", None)
    job["updated_at"] = datetime.now(UTC).isoformat()
    with _lock:
        _jobs[job_id] = job
    _save_job(job)
    threading.Thread(target=_process_job, args=(job_id,), daemon=True).start()
    return job


def review_event(
    job_id: str,
    event_id: str,
    *,
    verdict: str,
    note: str = "",
) -> dict[str, Any]:
    """Operador confirma, descarta o restaura un evento de la línea de tiempo."""
    if verdict not in {"confirmed", "dismissed", "restored"}:
        raise ValueError("verdict debe ser confirmed, dismissed o restored")
    job = get_job(job_id)
    if not job:
        raise FileNotFoundError("Trabajo no encontrado")
    analysis = job.get("analysis") or {}
    timeline = ensure_event_ids(analysis.get("timeline") or [])
    ev = next((e for e in timeline if e.get("event_id") == event_id), None)
    if not ev:
        raise FileNotFoundError("Evento no encontrado")

    feedback = dict(job.get("event_feedback") or {})
    if verdict == "restored":
        prior = feedback.pop(event_id, None)
        if prior and prior.get("verdict") == "dismissed":
            remove_suppression_for_event(ev)
    else:
        feedback[event_id] = {
            "verdict": verdict,
            "note": (note or "").strip(),
            "at": datetime.now(UTC).isoformat(),
            "type": ev.get("type"),
            "rule_id": ev.get("rule_id"),
            "message": ev.get("message"),
        }
        if verdict == "dismissed":
            record_dismissal(ev, job_id=job_id)

    job["event_feedback"] = feedback
    analysis["timeline"] = apply_review_state(timeline, feedback)
    analysis["event_count"] = len(active_timeline(timeline, feedback))
    job["analysis"] = analysis
    _regenerate_job_outputs(job_id)
    job["updated_at"] = datetime.now(UTC).isoformat()
    _save_job(job)
    return job


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
    safe_id = safe_job_id(job_id)
    safe_name = safe_keyframe_name(name)
    if not safe_id or not safe_name:
        return None
    base = JOBS_DIR / safe_id
    p = resolve_under(base, "keyframes", safe_name)
    return p if p and p.is_file() else None


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


def job_source_video_path(job_id: str, cam: int = 0) -> Path | None:
    """Archivo original subido (p. ej. AVI HEVC) — usado por OpenCV y análisis."""
    return resolve_source_path(_job_dir(job_id) / "sources", cam)


def job_video_path(job_id: str, cam: int = 0) -> Path | None:
    """MP4 H.264 listo para <video> en navegador; transcodifica bajo demanda."""
    d = _job_dir(job_id) / "sources"
    if not d.is_dir():
        return None
    from .video_transcode import web_playback_path

    return web_playback_path(d, cam)


def has_job_video(job_id: str, cam: int = 0) -> bool:
    return job_source_video_path(job_id, cam) is not None


def ensure_web_playback(job_id: str, cam: int = 0) -> Path | None:
    """Genera cam{N}_web.mp4 si el original no es reproducible en Chrome."""
    return job_video_path(job_id, cam)


def learn_event_at_timestamp(
    job_id: str,
    time_sec: float,
    *,
    title: str,
    description: str = "",
    situation_type: str = "other",
    industry: str = "general",
) -> dict[str, Any]:
    """Guarda en biblioteca un evento aprendido desde el instante del video."""
    from .knowledge import create_knowledge

    jpeg = extract_frame_jpeg(job_id, time_sec)
    if not jpeg:
        raise FileNotFoundError("No se pudo extraer frame del video")
    job = get_job(job_id)
    ind = (industry or "").strip() or (job.get("template_id") if job else "") or "general"
    return create_knowledge(
        title=title,
        situation_type=situation_type,
        description=description,
        industry=ind,
        media_bytes=jpeg,
        media_filename=f"frame_{int(time_sec)}.jpg",
        from_job_id=job_id,
        source="live",
        source_id=f"{job_id}:{time_sec:.2f}",
    )


def extract_frame_jpeg(job_id: str, time_sec: float, *, cam: int = 0) -> bytes | None:
    import cv2

    path = job_source_video_path(job_id, cam)
    if not path:
        return None
    cap = cv2.VideoCapture(str(path))
    if not cap.isOpened():
        return None
    fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
    cap.set(cv2.CAP_PROP_POS_FRAMES, int(time_sec * fps))
    ok, frame = cap.read()
    cap.release()
    if not ok or frame is None:
        return None
    ok2, buf = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), 85])
    return buf.tobytes() if ok2 else None
