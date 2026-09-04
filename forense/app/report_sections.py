"""Informe estructurado (ICAM-lite) para UI y exportación."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from .event_feedback import active_timeline, apply_review_state, build_review_audit, ensure_event_ids
from .expert_report import section_barrier_analysis, section_expert_recommendations, section_observed_facts
from .report import (
    DISCLAIMER,
    _narrative_block,
    _section_comparison,
    _section_dismissed_events,
    _section_executive_alerts,
    _section_focus,
    _section_kinematics,
    _section_knowledge,
    _section_speed_charts,
    _section_timeline,
)
from .timeline_evidence import enrich_timeline_evidence
from .video_ai import format_video_ai_markdown


def _prep_timelines(job: dict[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    analysis = job.get("analysis") or {}
    raw_timeline = analysis.get("timeline") or []
    keyframes = analysis.get("keyframes") or []
    feedback = job.get("event_feedback") or {}
    timeline = enrich_timeline_evidence(ensure_event_ids(raw_timeline), keyframes)
    timeline = apply_review_state(timeline, feedback)
    report_timeline = active_timeline(timeline, feedback)
    return timeline, report_timeline, feedback


def build_report_sections(job: dict[str, Any]) -> dict[str, Any]:
    """Secciones del informe para renderizado en tarjetas (UI)."""
    meta = job.get("meta") or {}
    analysis = job.get("analysis") or {}
    timeline, report_timeline, feedback = _prep_timelines(job)
    kin = analysis.get("kinematics") or {}
    comp = job.get("comparison") or {}
    knowledge = job.get("knowledge") or {}
    title = job.get("title") or "Incidente sin título"
    site = job.get("site") or "Faena"
    now = datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")

    duration = meta.get("duration_sec")
    if duration is not None:
        duration_txt = f"{duration:.1f} s"
    elif int(analysis.get("sources_count") or 1) > 1:
        duration_txt = "multi-cámara"
    else:
        duration_txt = "—"
    frames_txt = meta.get("sampled_frames", "—")
    cameras_txt = (
        f" · {analysis.get('sources_count', 1)} cámaras"
        if int(analysis.get("sources_count") or 1) > 1
        else ""
    )

    exec_md = (
        f"Se analizó un video de **{duration_txt}** ({frames_txt} frames muestreados{cameras_txt}).  \n"
        f"Se detectaron **{len(report_timeline)} eventos** relevantes "
        f"(excluye falsos positivos descartados por el operador).\n\n"
        f"{_section_executive_alerts(report_timeline, job)}"
        f"{_section_focus(job)}"
    )

    sections: list[dict[str, Any]] = [
        {"id": "executive", "title": "Resumen ejecutivo", "content_md": exec_md.strip()},
        {
            "id": "video_ai",
            "title": "Interpretación visual IA",
            "content_md": format_video_ai_markdown(job.get("video_ai")).strip(),
        },
        {
            "id": "facts",
            "title": "Hechos observados",
            "content_md": section_observed_facts(report_timeline).strip(),
        },
        {
            "id": "hypotheses",
            "title": "Hipótesis contribuyentes",
            "content_md": _narrative_block({**job, "analysis": {**analysis, "timeline": report_timeline}}).strip(),
            "note": "Requieren validación con entrevistas y peritaje.",
        },
        {
            "id": "barriers",
            "title": "Barreras que podrían haber fallado",
            "content_md": section_barrier_analysis(report_timeline, job).strip(),
        },
        {
            "id": "comparison",
            "title": "Comparación vs referencia",
            "content_md": _section_comparison(comp).strip(),
        },
        {
            "id": "knowledge",
            "title": "Biblioteca de situaciones",
            "content_md": _section_knowledge(knowledge).strip(),
        },
        {
            "id": "kinematics",
            "title": "Cinemática y velocidades",
            "content_md": _section_kinematics(kin, job).strip(),
        },
        {
            "id": "speed_charts",
            "title": "Gráficos de velocidad",
            "content_md": _section_speed_charts(analysis.get("speed_series") or []).strip(),
        },
        {
            "id": "timeline",
            "title": "Secuencia cronológica",
            "content_md": (
                _section_timeline(report_timeline) + _section_dismissed_events(timeline, feedback)
            ).strip(),
        },
        {
            "id": "recommendations",
            "title": "Recomendaciones preventivas",
            "content_md": section_expert_recommendations(report_timeline, job).strip(),
        },
        {
            "id": "limitations",
            "title": "Limitaciones del análisis",
            "content_md": (
                "- Muestreo adaptivo (~2–10 fps efectivos): pueden existir eventos entre frames no analizados.\n"
                f"- Velocidades y distancias requieren calibración m/px ({job.get('meters_per_pixel', '—')} m/px).\n"
                "- Identidad de trabajadores no se infiere salvo enrolamiento previo y rostro visible.\n"
                "- Este informe **no reemplaza** investigación con entrevistas, testigos ni peritaje oficial."
            ),
        },
    ]

    return {
        "title": title,
        "site": site,
        "generated_at": now,
        "build": job.get("build"),
        "template": job.get("template_name") or job.get("template_id"),
        "disclaimer": DISCLAIMER,
        "event_count": len(report_timeline),
        "sections": [s for s in sections if (s.get("content_md") or "").strip()],
        "review_audit": build_review_audit(job),
    }
