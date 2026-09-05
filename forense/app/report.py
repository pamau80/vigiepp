"""Generación de informe forense (plantilla + LLM opcional)."""

from __future__ import annotations

import json
import os
import urllib.request
from datetime import UTC, datetime
from typing import Any

from .expert_report import section_barrier_analysis, section_expert_recommendations, section_observed_facts
from .event_feedback import active_timeline, apply_review_state, ensure_event_ids
from .i18n_es_cl import label_event_type, label_kind, label_severity
from .timeline_evidence import enrich_timeline_evidence
from .video_ai import format_video_ai_markdown


DISCLAIMER = (
    "Este documento fue generado por **VigiEPP Forense** (inteligencia artificial). "
    "Reconstruye hechos observables en el video analizado. "
    "**No constituye peritaje legal, dictamen de mutualidad ni investigación oficial.** "
    "Requiere validación por personal de prevención de riesgos o autoridad competente."
)


def _section_timeline(timeline: list[dict[str, Any]]) -> str:
    if not timeline:
        return "_No se registraron eventos automáticos en el muestreo analizado._\n"
    lines = [
        "| Hora | Tipo | Severidad | Observación | Evidencia |",
        "|------|------|-----------|-------------|-----------|",
    ]
    for ev in timeline[:200]:
        ev_ref = f"`{ev['evidence_image']}`" if ev.get("evidence_image") else "—"
        lines.append(
            f"| {ev.get('time_label', '—')} | {label_event_type(ev.get('type', ''))} | "
            f"{label_severity(ev.get('severity', ''))} | "
            f"{(ev.get('message') or '').replace('|', '/')} | {ev_ref} |"
        )
    if len(timeline) > 200:
        lines.append(f"\n_… y {len(timeline) - 200} eventos adicionales._")
    return "\n".join(lines) + "\n"


def _section_kinematics(kin: dict[str, Any], job: dict[str, Any]) -> str:
    speeds = kin.get("track_speeds") or []
    if not speeds:
        return "_No se estimaron velocidades (sin tracks persona/maquinaria suficientes)._\n"
    lines = [
        f"Límites configurados: maquinaria **{job.get('max_machinery_kmh', '—')} km/h**, "
        f"persona **{job.get('max_person_kmh', '—')} km/h**, "
        f"distancia mínima **{job.get('min_distance_m', '—')} m**.",
        "",
        "| N° seg. | Tipo | Máx. km/h | Prom. km/h |",
        "|---------|------|-----------|------------|",
    ]
    for ts in speeds[:30]:
        lines.append(
            f"| #{ts.get('track_id')} | {label_kind(ts.get('kind', ''))} | {ts.get('max_kmh')} | {ts.get('avg_kmh')} |"
        )
    violations = kin.get("speed_violations") or []
    if violations:
        lines.append("\n**Excesos de velocidad estimados:**\n")
        for v in violations:
            lines.append(f"- {v.get('message')}")
    prox = kin.get("proximity_events") or []
    if prox:
        lines.append("\n**Proximidad persona–maquinaria:**\n")
        for p in prox[:20]:
            lines.append(f"- {p.get('message')}")
    return "\n".join(lines) + "\n"


def _section_dismissed_events(timeline: list[dict[str, Any]], feedback: dict[str, Any]) -> str:
    dismissed = [e for e in timeline if e.get("review_status") == "dismissed"]
    if not dismissed:
        return ""
    lines = ["\n### Eventos descartados por el operador (no cuentan en el análisis)\n"]
    for ev in dismissed[:30]:
        note = (ev.get("review_note") or "").strip()
        note_txt = f" — _{note}_" if note else ""
        lines.append(
            f"- {ev.get('time_label', '—')} · {label_event_type(ev.get('type', ''))}: "
            f"{(ev.get('message') or '').replace('|', '/')}{note_txt}"
        )
    return "\n".join(lines) + "\n"


def _section_executive_alerts(timeline: list[dict[str, Any]], job: dict[str, Any]) -> str:
    from .timeline_evidence import critical_alerts_summary

    alerts = critical_alerts_summary(timeline, job)
    if not alerts:
        return ""
    lines = ["### Hallazgos prioritarios\n"]
    for a in alerts[:10]:
        when = a.get("time_label") or "—"
        msg = (a.get("message") or "").strip()
        lines.append(f"- **{a.get('label', 'Alerta')}** ({when}): {msg}")
    return "\n".join(lines) + "\n"


def build_report_markdown(job: dict[str, Any]) -> str:
    meta = job.get("meta") or {}
    analysis = job.get("analysis") or {}
    raw_timeline = analysis.get("timeline") or []
    keyframes = analysis.get("keyframes") or []
    feedback = job.get("event_feedback") or {}
    timeline = enrich_timeline_evidence(ensure_event_ids(raw_timeline), keyframes)
    timeline = apply_review_state(timeline, feedback)
    report_timeline = active_timeline(timeline, feedback)
    kin = analysis.get("kinematics") or {}
    comp = job.get("comparison") or {}
    knowledge = job.get("knowledge") or {}
    tpl_name = job.get("template_name") or "General"
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

    body = f"""# Informe forense IA — {title}

**Sitio:** {site}  
**Generado:** {now}  
**Producto:** VigiEPP Forense · {job.get('build', 'p4')}  
**Plantilla:** {tpl_name}

---

> {DISCLAIMER}

## 1. Resumen ejecutivo

Se analizó un video de **{duration_txt}** ({frames_txt} frames muestreados{cameras_txt}).  
Se detectaron **{len(report_timeline)} eventos** relevantes (excluye falsos positivos descartados por el operador).

{_section_executive_alerts(report_timeline, job)}

{_section_focus(job)}

## 1b. Interpretación visual IA (fotogramas clave)

{format_video_ai_markdown(job.get('video_ai'))}

## 2. Hechos observados (evidencia en video)

{section_observed_facts(report_timeline, job)}

## 3. Hipótesis contribuyentes (requieren validación)

{_narrative_block({**job, "analysis": {**analysis, "timeline": report_timeline}})}

> _Las hipótesis son inferencias asistidas por IA. Deben contrastarse con entrevistas, registros y peritaje._

## 4. Barreras que podrían haber fallado

{section_barrier_analysis(report_timeline, job)}

## 5. Comparación vs escenario de referencia

{_section_comparison(comp)}

## 5b. Coincidencias con biblioteca de situaciones

{_section_knowledge(knowledge)}

## 6. Cinemática y velocidades

{_section_kinematics(kin, job)}

## 7. Gráficos de velocidad

{_section_speed_charts(analysis.get('speed_series') or [])}

## 8. Secuencia cronológica (con evidencia)

{_section_timeline(report_timeline)}

{_section_dismissed_events(timeline, feedback)}

## 9. Recomendaciones preventivas (experto)

{section_expert_recommendations(report_timeline, job)}

## 10. Limitaciones del análisis

- Muestreo adaptivo (~2–10 fps efectivos): pueden existir eventos entre frames no analizados.
- Velocidades y distancias requieren calibración `m/px` ({job.get('meters_per_pixel', '—')} m/px en este análisis).
- Identidad de trabajadores no se infiere salvo enrolamiento previo y rostro visible.
- Este informe **no reemplaza** investigación con entrevistas, testigos ni peritaje oficial.

---

_VigiEPP Forense · Informe IA de accidentes e incidentes_
"""
    return body


def _narrative_block(job: dict[str, Any]) -> str:
    from .expert_report import _relevant_event_types

    llm = (job.get("llm_narrative") or "").strip()
    if llm:
        return llm
    timeline = (job.get("analysis") or {}).get("timeline") or []
    if not timeline:
        return "_Sin eventos suficientes para inferir factores contribuyentes._"

    all_types = {e.get("type") for e in timeline}
    relevant_types = _relevant_event_types(job)

    if relevant_types:
        primary_types = all_types & relevant_types
        secondary_types = all_types - primary_types
    else:
        primary_types = all_types
        secondary_types = set()

    comp = job.get("comparison") or {}
    parts = []
    title_lower = (job.get("title") or "").lower()

    if "epp_non_compliant" in primary_types or "epp_reflective" in primary_types:
        parts.append("- Posible factor: incumplimiento de EPP detectado antes o durante el evento.")
    if "proximity" in primary_types or "speed_violation" in primary_types:
        parts.append("- Posible factor: proximidad crítica o exceso de velocidad persona–maquinaria.")
    if "action" in primary_types or "unsafe_act" in primary_types:
        parts.append("- Posible factor: conducta o acto inseguro según reglas de faena.")
    if "fall_risk" in primary_types:
        parts.append("- Posible factor: riesgo de caída o postura insegura en el tramo analizado.")
    if "zone" in primary_types:
        parts.append("- Posible factor: tránsito por zona restringida o exposición a línea de fuego/carga.")
    if ("fire" in primary_types or "smoke" in primary_types) or (
        ("fire" in all_types or "smoke" in all_types) and ("fuego" in title_lower or "incendio" in title_lower)
    ):
        parts.append("- Posible factor: fuego o humo visible — evaluar controles de ignición y respuesta.")
    if "emergency_response" in primary_types:
        parts.append("- Posible factor: respuesta de emergencia en curso — documentar tiempos y coordinación.")
    if "collision" in primary_types:
        parts.append("- Posible factor: colisión o cruce de trayectorias en el sector.")

    if secondary_types and len(parts) < 4:
        context_added = False
        if ("epp_non_compliant" in secondary_types or "epp_reflective" in secondary_types) and not any("EPP" in p for p in parts):
            parts.append("- _(Contexto)_ Incumplimiento de EPP observado, puede no estar directamente relacionado.")
            context_added = True
        if ("proximity" in secondary_types or "speed_violation" in secondary_types) and not any("proximidad" in p for p in parts) and not context_added:
            parts.append("- _(Contexto)_ Proximidad persona-maquinaria observada en el video.")

    if comp.get("available"):
        parts.append("- Posible factor: desviación respecto al escenario de referencia analizado.")
    knowledge = job.get("knowledge") or {}
    for m in (knowledge.get("matches") or [])[:3]:
        parts.append(
            f"- Posible factor (biblioteca): patrón «{m.get('title')}» — {m.get('description') or m.get('situation_label')}."
        )
    return "\n".join(parts) if parts else "_Revisar secuencia cronológica manualmente._"


def _section_knowledge(knowledge: dict[str, Any]) -> str:
    matches = knowledge.get("matches") or []
    if not matches:
        return "_Sin coincidencias en la biblioteca de situaciones etiquetadas._\n"
    lines = [
        f"Se encontraron **{len(matches)}** situaciones similares en la biblioteca de aprendizaje:",
        "",
    ]
    for m in matches:
        reasons = ", ".join(m.get("reasons") or [])
        lines.append(
            f"- **{m.get('title')}** ({m.get('situation_label')}) — confianza {m.get('confidence_pct', 0)}%"
        )
        if m.get("description"):
            lines.append(f"  - _{m.get('description')}_")
        if reasons:
            lines.append(f"  - Motivos: {reasons}")
    conjectures = knowledge.get("conjectures") or 0
    if conjectures:
        lines.append(f"\n_{conjectures} conjetura(s) de aprendizaje (similitud parcial)._")
    return "\n".join(lines) + "\n"


def _section_focus(job: dict[str, Any]) -> str:
    desc = (job.get("focus_description") or "").strip()
    f0 = job.get("focus_from_sec")
    f1 = job.get("focus_until_sec")
    if not desc and f0 is None:
        return ""
    lines = ["**Enfoque del operador:**"]
    if desc:
        lines.append(f"- {desc}")
    if f0 is not None and f1 is not None:
        lines.append(f"- Ventana prioritaria analizada: **{f0}s — {f1}s**")
    if job.get("strict_detection"):
        lines.append("- Modo estricto activo (menos falsos positivos del detector).")
    return "\n".join(lines) + "\n"


def _section_comparison(comp: dict[str, Any]) -> str:
    if not comp.get("available"):
        return "_Sin escenario de referencia para comparar._\n"
    return (
        f"**Referencia:** {comp.get('reference_title')} (`{comp.get('reference_job_id')}`)\n\n"
        f"- Eventos incidente: {comp.get('incident_events')} vs referencia: {comp.get('reference_events')} "
        f"(Δ {comp.get('delta_events')})\n"
        f"- Velocidad máx. incidente: {comp.get('incident_max_kmh')} km/h vs referencia: "
        f"{comp.get('reference_max_kmh')} km/h (Δ {comp.get('delta_max_kmh')})\n"
        f"- Violaciones cinemáticas: {comp.get('incident_violations')} vs {comp.get('reference_violations')}\n"
        f"- **Interpretación:** {comp.get('interpretation')}\n"
    )


def _section_speed_charts(series: list[dict[str, Any]]) -> str:
    if not series:
        return "_Sin series de velocidad (tracks insuficientes)._\n"
    lines = ["| Track | Tipo | Puntos | Máx km/h |", "|-------|------|--------|----------|"]
    for s in series[:20]:
        lines.append(
            f"| #{s.get('track_id')} | {s.get('kind')} | {len(s.get('points') or [])} | {s.get('max_kmh')} |"
        )
    lines.append("\n_Gráficos interactivos disponibles en la UI Forense._")
    return "\n".join(lines) + "\n"


def maybe_enrich_with_llm(job: dict[str, Any]) -> str | None:
    """LLM opcional vía OpenAI-compatible API."""
    api_key = os.getenv("VIGIEPP_FORENSE_OPENAI_KEY") or os.getenv("OPENAI_API_KEY")
    base = (os.getenv("VIGIEPP_FORENSE_OPENAI_BASE") or "https://api.openai.com/v1").rstrip("/")
    model = os.getenv("VIGIEPP_FORENSE_LLM_MODEL", "gpt-4o-mini")
    if not api_key:
        return None
    timeline = (job.get("analysis") or {}).get("timeline") or []
    knowledge_examples = [
        {
            "titulo": m.get("title"),
            "tipo": m.get("situation_label"),
            "descripcion": m.get("description"),
        }
        for m in (job.get("knowledge") or {}).get("matches") or []
    ]
    payload = {
        "model": model,
        "messages": [
            {
                "role": "system",
                "content": (
                    "Eres analista senior en prevención de riesgos industriales en Chile. "
                    "Redactas hipótesis contribuyentes SOLO a partir del JSON de eventos y ejemplos "
                    "de la biblioteca de situaciones. Usa condicional (podría, se observó). "
                    "Nunca concluyas negligencia ni culpa legal."
                ),
            },
            {
                "role": "user",
                "content": json.dumps(
                    {
                        "titulo": job.get("title"),
                        "sitio": job.get("site"),
                        "plantilla": job.get("template_name"),
                        "eventos": timeline[:120],
                        "situaciones_similares": knowledge_examples[:5],
                    },
                    ensure_ascii=False,
                ),
            },
        ],
        "temperature": 0.3,
    }
    req = urllib.request.Request(
        f"{base}/chat/completions",
        data=json.dumps(payload).encode(),
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read().decode())
        return data["choices"][0]["message"]["content"].strip()
    except Exception:
        return None
