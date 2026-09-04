"""Convierte hallazgos de IA visual en eventos de línea de tiempo."""

from __future__ import annotations

from typing import Any


def merge_vision_timeline(
    existing: list[dict[str, Any]],
    vision_events: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    if not vision_events:
        return list(existing)
    seen = {(e.get("type"), (e.get("message") or "")[:80]) for e in existing}
    merged = list(existing)
    for ev in vision_events:
        key = (ev.get("type"), (ev.get("message") or "")[:80])
        if key in seen:
            continue
        seen.add(key)
        merged.append(ev)
    merged.sort(key=lambda e: float(e.get("time_sec") or 0))
    return merged


def events_from_vision_parsed(
    parsed: dict[str, Any] | None,
    *,
    frames_used: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    """Traduce JSON de visión a eventos forenses."""
    if not parsed:
        return []
    events: list[dict[str, Any]] = []
    t0 = float((frames_used or [{}])[0].get("time_sec") or 0)
    t_label = (frames_used or [{}])[0].get("time_label") or "00:00:00"

    def add(ev_type: str, msg: str, severity: str = "high") -> None:
        if not msg or not str(msg).strip():
            return
        events.append(
            {
                "time_sec": t0,
                "time_label": t_label,
                "type": ev_type,
                "severity": severity,
                "message": str(msg).strip(),
                "source": "vision_ai",
            }
        )

    # Campos estructurados de emergencia
    fuego = parsed.get("fuego_contenedor") or parsed.get("fuego")
    if fuego:
        add("fire", f"IA visual: {fuego}", "critical")
    humo = parsed.get("humo") or parsed.get("humo_visible")
    if humo:
        add("smoke", f"IA visual: {humo}", "high")
    epp = parsed.get("epp_chaleco_reflectante") or parsed.get("ropa_reflectante")
    if epp:
        add("epp_reflective", f"IA visual: {epp}", "high")
    brigada = parsed.get("brigada_incendios") or parsed.get("respuesta_emergencia")
    if brigada:
        add("emergency_response", f"IA visual: {brigada}", "medium")

    for r in parsed.get("riesgos") or []:
        rl = str(r).lower()
        if any(k in rl for k in ("fuego", "llama", "incendio", "humo")):
            add("fire", f"Riesgo visible: {r}", "critical")
        elif any(k in rl for k in ("chaleco", "reflect", "alta visibilidad", "epp")):
            add("epp_reflective", f"Riesgo EPP: {r}", "high")
        elif any(k in rl for k in ("brigada", "bomber", "emergenc")):
            add("emergency_response", f"Respuesta emergencia: {r}", "medium")

    for item in parsed.get("secuencia") or []:
        if not isinstance(item, dict):
            continue
        obs = str(item.get("observacion") or "")
        ol = obs.lower()
        hora = item.get("hora") or t_label
        ts = t0
        if isinstance(item.get("time_sec"), (int, float)):
            ts = float(item["time_sec"])
        if any(k in ol for k in ("fuego", "llama", "incendio", "contenedor en llamas")):
            events.append(
                {
                    "time_sec": ts,
                    "time_label": hora,
                    "type": "fire",
                    "severity": "critical",
                    "message": obs,
                    "source": "vision_ai",
                }
            )
        elif "humo" in ol:
            events.append(
                {
                    "time_sec": ts,
                    "time_label": hora,
                    "type": "smoke",
                    "severity": "high",
                    "message": obs,
                    "source": "vision_ai",
                }
            )
        elif any(k in ol for k in ("chaleco", "reflect", "ropa flúor", "alta visibilidad")):
            events.append(
                {
                    "time_sec": ts,
                    "time_label": hora,
                    "type": "epp_reflective",
                    "severity": "high",
                    "message": obs,
                    "source": "vision_ai",
                }
            )
        elif any(k in ol for k in ("brigada", "bombero", "emergenc", "extintor")):
            events.append(
                {
                    "time_sec": ts,
                    "time_label": hora,
                    "type": "emergency_response",
                    "severity": "medium",
                    "message": obs,
                    "source": "vision_ai",
                }
            )
    return events
