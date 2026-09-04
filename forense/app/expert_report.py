"""Secciones de informe experto (ICAM-lite) para Forense."""

from __future__ import annotations

from typing import Any

from .i18n_es_cl import label_event_type, label_severity

_FACT_SOURCES = frozenset({"detector", "scene_cv", "vision_ai", None})


def _is_fact(ev: dict[str, Any]) -> bool:
    src = ev.get("source")
    if src in _FACT_SOURCES or src is None:
        return True
    return ev.get("type") in {"fire", "smoke", "epp_reflective", "emergency_response", "epp_non_compliant", "zone", "proximity", "speed_violation"}


def section_observed_facts(timeline: list[dict[str, Any]]) -> str:
    facts = [e for e in timeline if _is_fact(e)]
    if not facts:
        return "_No se registraron hechos automáticos con evidencia en el muestreo._\n"
    lines = [
        "Hechos **directamente observables** en video (detector, visión de escena o IA visual). "
        "No implican culpa ni conclusión legal.",
        "",
        "| Hora | Tipo | Severidad | Hecho | Evidencia |",
        "|------|------|-----------|-------|-----------|",
    ]
    for ev in facts[:80]:
        ev_img = ev.get("evidence_image")
        ev_txt = f"Captura `{ev_img}`" if ev_img else "—"
        src = ev.get("source") or "automático"
        msg = (ev.get("message") or "").replace("|", "/")
        lines.append(
            f"| {ev.get('time_label', '—')} | {label_event_type(ev.get('type', ''))} | "
            f"{label_severity(ev.get('severity', ''))} | {msg} | {ev_txt} ({src}) |"
        )
    if len(facts) > 80:
        lines.append(f"\n_… y {len(facts) - 80} hechos adicionales en la secuencia cronológica._")
    return "\n".join(lines) + "\n"


def section_barrier_analysis(timeline: list[dict[str, Any]], job: dict[str, Any]) -> str:
    types = {e.get("type") for e in timeline}
    barriers: list[str] = []
    if types & {"fire", "smoke"}:
        barriers.append(
            "- **Barrera de control de energía/material inflamable:** posible falla en detección temprana, "
            "almacenamiento o respuesta ante ignición (contenedor, baterías, carga)."
        )
        barriers.append(
            "- **Barrera de respuesta a emergencias:** verificar activación de plan, brigada, evacuación y "
            "delimitación de zona caliente."
        )
    if types & {"epp_reflective", "epp_non_compliant"}:
        barriers.append(
            "- **Barrera de supervisión EPP:** posible falla en verificación de chaleco reflectante y "
            "elementos obligatorios antes de ingreso a zona de riesgo."
        )
    if types & {"proximity", "speed_violation"}:
        barriers.append(
            "- **Barrera de segregación persona–maquinaria:** límites de velocidad, señalética o "
            "banksman/guía insuficientes."
        )
    if types & {"action", "fall_risk", "unsafe_act"}:
        barriers.append(
            "- **Barrera de procedimiento / comportamiento:** reglas de trabajo seguro o capacitación "
            "podrían no haberse cumplido en el tramo analizado."
        )
    if types & {"zone"}:
        barriers.append("- **Barrera de delimitación de zonas:** acceso no controlado a área restringida.")
    if types & {"emergency_response"}:
        barriers.append(
            "- **Barrera de coordinación de emergencia:** evaluar si la respuesta fue oportuna y acorde al plan."
        )
    knowledge = job.get("knowledge") or {}
    for m in (knowledge.get("matches") or [])[:2]:
        if not m.get("conjecture"):
            barriers.append(
                f"- **Patrón histórico en biblioteca («{m.get('title')}'):** revisar si las medidas "
                f"aprendidas en casos similares estaban implementadas."
            )
    if not barriers:
        return (
            "_Sin suficientes eventos para proponer barreras. Ampliar ventana de análisis o "
            "usar interpretación visual IA._\n"
        )
    return "\n".join(barriers) + "\n"


def section_expert_recommendations(timeline: list[dict[str, Any]], job: dict[str, Any]) -> str:
    types = {e.get("type") for e in timeline}
    recs: list[str] = []
    va = (job.get("video_ai") or {}).get("parsed") or {}
    for r in va.get("recomendaciones") or []:
        recs.append(f"- {r}")
    if types & {"fire", "smoke"}:
        recs.extend(
            [
                "- Aislar y enfriar zona; no ingresar sin EPP bomberil y evaluación de atmósfera.",
                "- Revisar plan de emergencia, simulacros y disponibilidad de brigada/extintores.",
                "- Investigar causa raíz de ignición (carga, baterías, trabajo en caliente).",
            ]
        )
    if types & {"epp_reflective", "epp_non_compliant"}:
        recs.append("- Reforzar control de EPP en acceso a patio/muelle (chaleco reflectante obligatorio).")
    if types & {"proximity", "speed_violation"}:
        recs.extend(
            [
                "- Reforzar distanciamiento persona–maquinaria y límites de velocidad en vías internas.",
                "- Evaluar uso de banksman en maniobras de retroceso.",
            ]
        )
    if types & {"emergency_response"}:
        recs.append("- Documentar tiempos de respuesta de brigada y lecciones aprendidas del simulacro real.")
    if not recs:
        recs = [
            "- Revisar señalética y delimitación de zonas en el sector del incidente.",
            "- Verificar cumplimiento EPP en el tramo horario del evento.",
            "- Capacitar supervisores en uso del monitoreo en vivo para evitar recurrencia.",
        ]
    # dedupe preserving order
    seen: set[str] = set()
    unique: list[str] = []
    for r in recs:
        key = r.lower()[:60]
        if key in seen:
            continue
        seen.add(key)
        unique.append(r)
    return "\n".join(unique[:12]) + "\n"
