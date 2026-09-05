"""Secciones de informe experto (ICAM-lite) — cualquier tipo de incidente."""

from __future__ import annotations

from typing import Any

from .i18n_es_cl import label_event_type, label_severity

_FACT_SOURCES = frozenset({"detector", "scene_cv", "vision_ai", None})

INCIDENT_RELATED_EVENTS: dict[str, set[str]] = {
    "caida": {"fall_risk", "epp_non_compliant", "epp_reflective", "unsafe_act", "action"},
    "atropello": {"proximity", "speed_violation", "collision", "zone", "epp_reflective"},
    "golpe": {"proximity", "collision", "zone", "unsafe_act", "action"},
    "fuego": {"fire", "smoke", "emergency_response", "zone"},
    "incendio": {"fire", "smoke", "emergency_response", "zone"},
    "electrico": {"zone", "unsafe_act", "action", "epp_non_compliant"},
    "atrapamiento": {"proximity", "zone", "unsafe_act", "action"},
    "derrame": {"zone", "action", "emergency_response"},
    "general": set(),
}

def _relevant_event_types(job: dict[str, Any]) -> set[str]:
    """Retorna tipos de eventos relevantes para el tipo de incidente."""
    template = (job.get("template_id") or job.get("template_name") or "").lower()
    title = (job.get("title") or "").lower()
    focus = (job.get("focus_description") or "").lower()
    combined = f"{template} {title} {focus}"

    for incident_type, related in INCIDENT_RELATED_EVENTS.items():
        if incident_type in combined:
            return related
    return set()

_BARRIERS: dict[str, str] = {
    "fire": "**Energía / ignición:** control de materiales inflamables, detección temprana y respuesta ante fuego.",
    "smoke": "**Energía / ignición:** posible ignición o reacción en curso — verificar origen y contención.",
    "epp_non_compliant": "**Supervisión EPP:** verificación de elementos obligatorios antes y durante la faena.",
    "epp_reflective": "**Alta visibilidad:** control de chaleco/ropa reflectante en zonas de tránsito y maquinaria.",
    "proximity": "**Segregación persona–equipo:** distanciamiento, banksman o delimitación insuficientes.",
    "speed_violation": "**Control de velocidad:** límites operacionales o señalética no respetados.",
    "action": "**Procedimiento / conducta:** reglas de trabajo seguro o capacitación no aplicadas en el tramo.",
    "fall_risk": "**Prevención de caídas:** orden, limpieza, barandas o método de trabajo inadecuado.",
    "unsafe_act": "**Comportamiento seguro:** acto inseguro observable sin barrera de contención.",
    "zone": "**Delimitación de zonas:** acceso no controlado a área restringida o de riesgo.",
    "emergency_response": "**Gestión de emergencia:** coordinación y tiempos de respuesta ante el evento.",
    "collision": "**Segregación y tránsito:** cruce de trayectorias persona–vehículo o equipo.",
    "knowledge_match": "**Lecciones previas:** patrón similar ya documentado — verificar si se aplicaron medidas.",
}

_RECOMMENDATIONS: dict[str, list[str]] = {
    "fire": [
        "Aislar zona y activar plan de emergencia según procedimiento de faena.",
        "Investigar causa de ignición y condiciones de almacenamiento o trabajo en caliente.",
    ],
    "smoke": ["Identificar fuente de humo y evaluar exposición de personas en el área."],
    "epp_non_compliant": ["Reforzar control de EPP en acceso y durante la jornada en el sector."],
    "epp_reflective": ["Exigir chaleco/ropa de alta visibilidad en patios y zonas de tránsito mixto."],
    "proximity": [
        "Reforzar distanciamiento persona–maquinaria y uso de guía en maniobras.",
        "Evaluar segregación física o barreras en cruces de alto riesgo.",
    ],
    "speed_violation": ["Revisar límites de velocidad, señalética y fiscalización en vías internas."],
    "action": ["Capacitar en procedimiento específico del puesto y reforzar supervisión en terreno."],
    "fall_risk": ["Orden y aseo, barandas y método seguro para trabajos en altura o superficies irregulares."],
    "unsafe_act": ["Feedback inmediato al trabajador y registro para seguimiento preventivo."],
    "zone": ["Delimitar y señalizar zonas restringidas; controlar accesos."],
    "emergency_response": ["Documentar tiempos de respuesta y ajustar plan de emergencia si aplica."],
    "collision": ["Revisar layout de tránsito y puntos ciegos en el sector del evento."],
}


def _is_fact(ev: dict[str, Any]) -> bool:
    src = ev.get("source")
    return src in _FACT_SOURCES or src is None


def section_observed_facts(timeline: list[dict[str, Any]], job: dict[str, Any] | None = None) -> str:
    facts = [e for e in timeline if _is_fact(e)]
    if not facts:
        return "_No se registraron hechos automáticos con evidencia en el muestreo._\n"

    relevant_types = _relevant_event_types(job) if job else set()
    critical_types = {"fire", "smoke", "proximity", "collision", "fall_risk"}

    if relevant_types:
        primary = [e for e in facts if e.get("type") in relevant_types]
        secondary = [e for e in facts if e.get("type") not in relevant_types and e.get("type") in critical_types]
        other = [e for e in facts if e.get("type") not in relevant_types and e.get("type") not in critical_types]
    else:
        primary = facts
        secondary = []
        other = []

    lines = [
        "Hechos **directamente observables** en video (detector, reglas, visión de escena o IA visual). "
        "No implican culpa ni conclusión legal.",
        "",
        "| Hora | Tipo | Severidad | Hecho | Evidencia |",
        "|------|------|-----------|-------|-----------|",
    ]

    shown = 0
    for ev in primary[:60]:
        ev_img = ev.get("evidence_image")
        ev_txt = f"Captura `{ev_img}`" if ev_img else "—"
        src = ev.get("source") or "automático"
        msg = (ev.get("message") or "").replace("|", "/")
        lines.append(
            f"| {ev.get('time_label', '—')} | {label_event_type(ev.get('type', ''))} | "
            f"{label_severity(ev.get('severity', ''))} | {msg} | {ev_txt} ({src}) |"
        )
        shown += 1

    if secondary and shown < 70:
        for ev in secondary[:min(10, 70 - shown)]:
            ev_img = ev.get("evidence_image")
            ev_txt = f"Captura `{ev_img}`" if ev_img else "—"
            src = ev.get("source") or "automático"
            msg = (ev.get("message") or "").replace("|", "/")
            lines.append(
                f"| {ev.get('time_label', '—')} | {label_event_type(ev.get('type', ''))} | "
                f"{label_severity(ev.get('severity', ''))} | {msg} _(secundario)_ | {ev_txt} ({src}) |"
            )
            shown += 1

    total = len(primary) + len(secondary) + len(other)
    if total > shown:
        lines.append(f"\n_… y {total - shown} hechos adicionales (algunos pueden no estar directamente relacionados con el incidente)._")
    return "\n".join(lines) + "\n"


def section_barrier_analysis(timeline: list[dict[str, Any]], job: dict[str, Any]) -> str:
    relevant_types = _relevant_event_types(job)
    all_types = {e.get("type") for e in timeline}

    if relevant_types:
        types = all_types & (relevant_types | {"proximity", "collision"})
        secondary_types = all_types - types
    else:
        types = all_types
        secondary_types = set()

    barriers: list[str] = []
    for etype in sorted(types):
        text = _BARRIERS.get(str(etype))
        if text:
            barriers.append(f"- {text}")

    if secondary_types and len(barriers) < 6:
        for etype in sorted(secondary_types):
            if etype in {"fire", "smoke"} and "fuego" not in (job.get("title") or "").lower():
                continue
            text = _BARRIERS.get(str(etype))
            if text:
                barriers.append(f"- _(Contexto)_ {text}")
                if len(barriers) >= 8:
                    break

    knowledge = job.get("knowledge") or {}
    for m in (knowledge.get("matches") or [])[:2]:
        if not m.get("conjecture"):
            barriers.append(
                f"- **Patrón en biblioteca («{m.get('title')}'):** revisar medidas aprendidas en casos similares."
            )
    if not barriers:
        return (
            "_Sin eventos suficientes para analizar barreras. Ampliar ventana de análisis, "
            "re-analizar el caso o activar interpretación visual IA._\n"
        )
    return "\n".join(barriers) + "\n"


def section_expert_recommendations(timeline: list[dict[str, Any]], job: dict[str, Any]) -> str:
    relevant_types = _relevant_event_types(job)
    all_types = {e.get("type") for e in timeline}

    if relevant_types:
        primary_types = all_types & relevant_types
        secondary_types = all_types - primary_types
    else:
        primary_types = all_types
        secondary_types = set()

    recs: list[str] = []
    va = (job.get("video_ai") or {}).get("parsed") or {}
    for r in va.get("recomendaciones") or []:
        recs.append(f"- {r}")

    for etype in sorted(primary_types):
        for item in _RECOMMENDATIONS.get(str(etype), []):
            recs.append(f"- {item}")

    if len(recs) < 6 and secondary_types:
        for etype in sorted(secondary_types):
            if etype in {"fire", "smoke"} and "fuego" not in (job.get("title") or "").lower():
                continue
            for item in _RECOMMENDATIONS.get(str(etype), []):
                recs.append(f"- _(Preventivo general)_ {item}")
                if len(recs) >= 10:
                    break
            if len(recs) >= 10:
                break

    if not recs:
        recs = [
            "- Revisar señalética y delimitación de zonas en el sector del incidente.",
            "- Verificar cumplimiento EPP en el tramo horario del evento.",
            "- Reforzar supervisión en terreno y uso del monitoreo para evitar recurrencia.",
        ]
    seen: set[str] = set()
    unique: list[str] = []
    for r in recs:
        key = r.lower()[:72]
        if key in seen:
            continue
        seen.add(key)
        unique.append(r)
    return "\n".join(unique[:12]) + "\n"
