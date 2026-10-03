"""Informe enriquecido para Comité Paritario de Higiene y Seguridad (CPHS)."""

from __future__ import annotations

from collections import Counter
from typing import Any

# Medidas preventivas por industria (alineadas a DS 54/69 — funciones CPHS)
_INDUSTRY_MEASURES: dict[str, list[str]] = {
    "mineria": [
        "Revisar segregación peatón–equipo móvil en vías de acarreo y zonas de carga.",
        "Verificar señalética, delimitación y comunicación operador–terreno en puntos ciegos.",
        "Auditar cumplimiento EPP (casco, calzado, lentes) en turnos de mayor accidentabilidad.",
    ],
    "portuario": [
        "Inspeccionar zonas de giro de grúas, spreaders y tránsito mixto en muelle.",
        "Reforzar procedimiento de comunicación operador–estibador en maniobras.",
        "Verificar delimitación de áreas Ro-Ro y cubierta con barreras físicas.",
    ],
    "bodega": [
        "Revisar velocidad de montacargas y señalización en cruces ciegos.",
        "Auditar uso de chaleco reflectante y calzado de seguridad en pasillos.",
        "Capacitar en regla de prioridad peatón–vehículo en zonas de carga/descarga.",
    ],
    "construccion": [
        "Inspeccionar andamios, barandas y arneses en trabajos en altura.",
        "Verificar delimitación de radio de giro de maquinaria móvil en frentes activos.",
        "Revisar apuntalamiento y señalización en excavaciones.",
    ],
    "parking": [
        "Reforzar procedimiento de retroceso con spotter en rampas y patios.",
        "Verificar señalética de tránsito mixto peatón–vehículo.",
        "Auditar velocidad máxima en patios logísticos.",
    ],
    "general": [
        "Revisar procedimiento de tránsito en sector del evento.",
        "Reforzar capacitación en distanciamiento persona–maquinaria.",
        "Verificar señalética y delimitación de zonas restringidas.",
    ],
}

_EVENT_MEASURES: dict[str, str] = {
    "epp_non_compliant": "Instruir trabajadores en uso correcto de EPP (función CPHS art. DS 54).",
    "proximity": "Implementar medidas de distanciamiento persona–maquinaria y roles de spotter.",
    "speed_violation": "Revisar límites de velocidad interna y señalización en vías de circulación.",
    "zone": "Delimitar y señalizar zonas restringidas; reforzar permisos de ingreso.",
    "action": "Revisar reglas de conducta insegura detectadas por monitoreo Acciones.",
    "knowledge_match": "Comparar con situaciones similares en biblioteca de aprendizaje de la faena.",
}


def _timeline_summary(timeline: list[dict[str, Any]]) -> dict[str, int]:
    counts: Counter[str] = Counter()
    for ev in timeline:
        t = str(ev.get("type") or "other")
        counts[t] += 1
    return dict(counts)


def _industry_key(job: dict[str, Any]) -> str:
    tid = (job.get("template_id") or "general").strip().lower()
    return tid if tid in _INDUSTRY_MEASURES else "general"


def committee_section(job: dict[str, Any]) -> str:
    """Genera informe CPHS enriquecido para presentación en comité paritario."""
    comp = job.get("comparison") or {}
    analysis = job.get("analysis") or {}
    kin = analysis.get("kinematics") or {}
    knowledge = job.get("knowledge") or {}
    timeline = analysis.get("timeline") or []
    type_counts = _timeline_summary(timeline)
    industry = _industry_key(job)
    llm_status = job.get("llm_status") or "unknown"

    lines = [
        "## Informe Comité Paritario — CPHS en terreno",
        "",
        "> Borrador asistido por IA (VigiEPP Forense). Validar con prevencionista antes de presentar.",
        "> Marco: funciones del Comité Paritario según **DS N° 54/69** (instrucción, inspección, estudio EPP).",
        "",
        "### 1. Identificación del caso",
        "",
        f"| Campo | Valor |",
        f"|-------|-------|",
        f"| **Caso** | {job.get('title') or '—'} |",
        f"| **Faena / sitio** | {job.get('site') or '—'} |",
        f"| **Industria** | {job.get('template_name') or job.get('template_id') or 'General'} |",
        f"| **Fecha análisis** | {(job.get('updated_at') or '')[:10]} |",
        f"| **Build Forense** | {job.get('build', '—')} |",
        "",
        "### 2. Hechos observables (video analizado)",
        "",
        f"- Eventos registrados en video: **{analysis.get('event_count', 0)}**",
        f"- Fotogramas analizados: **{analysis.get('frames_analyzed', 0)}**",
        f"- Cámaras: **{analysis.get('sources_count', 1)}**",
        f"- Violaciones cinemáticas (velocidad): **{len(kin.get('speed_violations') or [])}**",
        f"- Eventos proximidad crítica: **{len(kin.get('proximity_events') or [])}**",
        "",
    ]

    if type_counts:
        lines.append("**Desglose por tipo de evento:**")
        lines.append("")
        for ev_type, count in sorted(type_counts.items(), key=lambda x: -x[1]):
            label = ev_type.replace("_", " ")
            lines.append(f"- {label}: **{count}**")
        lines.append("")

    if comp.get("available"):
        lines.extend(
            [
                "### 3. Comparación vs escenario de referencia",
                "",
                f"- Referencia: **{comp.get('reference_title')}** (`{comp.get('reference_job_id')}`)",
                f"- {comp.get('summary')}",
                f"- Interpretación: {comp.get('interpretation')}",
                "",
            ]
        )
    else:
        lines.extend(["### 3. Comparación vs escenario de referencia", "", "_Sin escenario de referencia cargado._", ""])

    matches = [m for m in (knowledge.get("matches") or []) if not m.get("conjecture")]
    conjectures = [m for m in (knowledge.get("matches") or []) if m.get("conjecture")]
    lines.append("### 4. Coincidencias con biblioteca de situaciones (terreno)")
    lines.append("")
    if matches:
        for m in matches[:5]:
            lines.append(
                f"- **{m.get('title')}** ({m.get('situation_label')}) — confianza {m.get('confidence_pct', 0)}%"
            )
            if m.get("description"):
                lines.append(f"  - _{m.get('description')}_")
        if conjectures:
            lines.append(f"\n_{len(conjectures)} conjetura(s) adicional(es) con similitud parcial (no concluyentes)._")
    else:
        lines.append("_Sin coincidencias confiables en biblioteca. Se recomienda enseñar esta situación desde el video._")
    lines.append("")

    lines.append("### 5. Medidas correctivas propuestas (preventivas)")
    lines.append("")
    seen: set[str] = set()
    for ev_type in type_counts:
        measure = _EVENT_MEASURES.get(ev_type)
        if measure and measure not in seen:
            lines.append(f"- {measure}")
            seen.add(measure)
    for measure in _INDUSTRY_MEASURES.get(industry, _INDUSTRY_MEASURES["general"]):
        if measure not in seen:
            lines.append(f"- {measure}")
            seen.add(measure)
    lines.append("")

    lines.extend(
        [
            "### 6. Plan de seguimiento CPHS (propuesta)",
            "",
            "| Plazo | Acción | Responsable |",
            "|-------|--------|-------------|",
            "| 7 días | Difundir hallazgos en reunión CPHS y registrar acta | Presidente CPHS |",
            "| 30 días | Verificar implementación de medidas correctivas en terreno | Prevencionista + CPHS |",
            "| 60 días | Re-inspección del sector del evento (checklist DS 54) | CPHS |",
            "| 90 días | Evaluar recurrencia y actualizar IPER si aplica | SSOMA |",
            "",
        ]
    )

    if llm_status == "offline":
        lines.append(
            "_Narrativa IA ampliada no disponible (sin API LLM en edge). "
            "El análisis se basa en detección automática + biblioteca de situaciones._"
        )
        lines.append("")
    elif llm_status == "failed":
        lines.append("_La narrativa IA ampliada no pudo generarse; revisar conectividad o clave API._")
        lines.append("")

    lines.extend(
        [
            "---",
            "",
            "**Checklist CPHS antes de presentar:**",
            "- [ ] Validado por prevencionista de riesgos",
            "- [ ] Contrastado con testigos / partes involucradas",
            "- [ ] Medidas asignadas con responsable y plazo",
            "- [ ] Registrado en acta de comité paritario",
            "",
        ]
    )
    return "\n".join(lines)
