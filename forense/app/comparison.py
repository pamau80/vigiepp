"""Comparación incidente vs escenario de referencia (seguro)."""

from __future__ import annotations

from typing import Any


def compare_jobs(incident: dict[str, Any], reference: dict[str, Any] | None) -> dict[str, Any]:
    if not reference:
        return {"available": False}
    ia = incident.get("analysis") or {}
    ra = reference.get("analysis") or {}
    ikin = ia.get("kinematics") or {}
    rkin = ra.get("kinematics") or {}
    i_events = int(ia.get("event_count") or 0)
    r_events = int(ra.get("event_count") or 0)
    i_max = max((t.get("max_kmh") or 0) for t in (ikin.get("track_speeds") or [])) if ikin.get("track_speeds") else 0
    r_max = max((t.get("max_kmh") or 0) for t in (rkin.get("track_speeds") or [])) if rkin.get("track_speeds") else 0
    i_viol = len(ikin.get("speed_violations") or []) + len(ikin.get("proximity_events") or [])
    r_viol = len(rkin.get("speed_violations") or []) + len(rkin.get("proximity_events") or [])
    delta_events = i_events - r_events
    delta_max_speed = round(i_max - r_max, 2)
    delta_violations = i_viol - r_viol
    risk_delta = delta_events * 2 + delta_violations * 5 + max(0, delta_max_speed)
    summary_parts = []
    if delta_events > 0:
        summary_parts.append(f"+{delta_events} eventos vs referencia")
    if delta_violations > 0:
        summary_parts.append(f"+{delta_violations} violaciones cinemáticas")
    if delta_max_speed > 2:
        summary_parts.append(f"velocidad máxima +{delta_max_speed} km/h")
    return {
        "available": True,
        "reference_job_id": reference.get("id"),
        "reference_title": reference.get("title"),
        "incident_events": i_events,
        "reference_events": r_events,
        "delta_events": delta_events,
        "incident_max_kmh": i_max,
        "reference_max_kmh": r_max,
        "delta_max_kmh": delta_max_speed,
        "incident_violations": i_viol,
        "reference_violations": r_viol,
        "delta_violations": delta_violations,
        "risk_delta_score": round(risk_delta, 1),
        "summary": "; ".join(summary_parts) if summary_parts else "Sin diferencias significativas detectadas",
        "interpretation": _interpret(delta_events, delta_violations, delta_max_speed),
    }


def _interpret(de: int, dv: int, ds: float) -> str:
    if de <= 0 and dv <= 0 and ds <= 1:
        return "El incidente no muestra incremento claro respecto al escenario de referencia en el muestreo analizado."
    parts = []
    if de > 0:
        parts.append("mayor cantidad de eventos de riesgo")
    if dv > 0:
        parts.append("más violaciones de velocidad o proximidad")
    if ds > 2:
        parts.append("velocidades más altas")
    return "Respecto al escenario de referencia se observó: " + ", ".join(parts) + "."
