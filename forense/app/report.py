"""Generación de informe forense (plantilla + LLM opcional)."""

from __future__ import annotations

import json
import os
import urllib.request
from datetime import UTC, datetime
from typing import Any


DISCLAIMER = (
    "Este documento fue generado por **VigiEPP Forense** (inteligencia artificial). "
    "Reconstruye hechos observables en el video analizado. "
    "**No constituye peritaje legal, dictamen de mutualidad ni investigación oficial.** "
    "Requiere validación por personal de prevención de riesgos o autoridad competente."
)


def _section_timeline(timeline: list[dict[str, Any]]) -> str:
    if not timeline:
        return "_No se registraron eventos automáticos en el muestreo analizado._\n"
    lines = ["| Hora | Tipo | Severidad | Observación |", "|------|------|-----------|-------------|"]
    for ev in timeline[:200]:
        lines.append(
            f"| {ev.get('time_label', '—')} | {ev.get('type', '—')} | {ev.get('severity', '—')} | "
            f"{(ev.get('message') or '').replace('|', '/')} |"
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
        "| Track | Tipo | Máx km/h | Prom km/h |",
        "|-------|------|----------|-----------|",
    ]
    for ts in speeds[:30]:
        lines.append(
            f"| #{ts.get('track_id')} | {ts.get('kind')} | {ts.get('max_kmh')} | {ts.get('avg_kmh')} |"
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


def build_report_markdown(job: dict[str, Any]) -> str:
    meta = job.get("meta") or {}
    analysis = job.get("analysis") or {}
    timeline = analysis.get("timeline") or []
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
Se detectaron **{analysis.get('event_count', 0)} eventos** relevantes.

## 2. Comparación vs escenario de referencia

{_section_comparison(comp)}

## 2b. Coincidencias con biblioteca de situaciones

{_section_knowledge(knowledge)}

## 3. Cinemática y velocidades

{_section_kinematics(kin, job)}

## 4. Gráficos de velocidad

{_section_speed_charts(analysis.get('speed_series') or [])}

## 5. Secuencia cronológica

{_section_timeline(timeline)}

## 6. Hechos observables (automáticos)

Los eventos provienen del motor VigiEPP (EPP, zonas, Acciones, tracking) con muestreo adaptivo.

## 7. Hipótesis contribuyentes (asistido IA)

{_narrative_block(job)}

## 8. Recomendaciones preventivas

- Revisar señalética y delimitación de zonas restringidas en el sector del incidente.
- Reforzar distanciamiento persona–maquinaria y límites de velocidad en vías internas.
- Verificar cumplimiento EPP en el tramo horario del evento.
- Capacitar supervisores en uso del monitoreo en vivo para evitar recurrencia.

## 9. Limitaciones del análisis

- Muestreo adaptivo (~2–10 fps efectivos): pueden existir eventos entre frames no analizados.
- Velocidades y distancias requieren calibración `m/px` ({job.get('meters_per_pixel', '—')} m/px en este análisis).
- Identidad de trabajadores no se infiere salvo enrolamiento previo y rostro visible.
- Este informe **no reemplaza** investigación con entrevistas, testigos ni peritaje oficial.

---

_VigiEPP Forense · Informe IA de accidentes e incidentes_
"""
    return body


def _narrative_block(job: dict[str, Any]) -> str:
    llm = (job.get("llm_narrative") or "").strip()
    if llm:
        return llm
    timeline = (job.get("analysis") or {}).get("timeline") or []
    if not timeline:
        return "_Sin eventos suficientes para inferir factores contribuyentes._"
    types = {e.get("type") for e in timeline}
    comp = job.get("comparison") or {}
    parts = []
    if "epp_non_compliant" in types:
        parts.append("- Posible factor: incumplimiento de EPP detectado antes o durante el evento.")
    if "action" in types:
        parts.append("- Posible factor: proximidad o conducta insegura según reglas Acciones.")
    if "proximity" in types or "speed_violation" in types:
        parts.append("- Posible factor: exceso de velocidad o proximidad crítica persona–maquinaria.")
    if "zone" in types:
        parts.append("- Posible factor: tránsito por zona no autorizada o de riesgo.")
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
    boosted = knowledge.get("boosted_events") or 0
    conjectures = knowledge.get("conjectures") or 0
    if conjectures:
        lines.append(f"\n_{conjectures} conjetura(s) de aprendizaje (similitud parcial)._")
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
