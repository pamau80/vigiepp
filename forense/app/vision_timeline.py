"""Convierte hallazgos de IA visual en eventos de línea de tiempo."""

from __future__ import annotations

from typing import Any

from .timeline_evidence import _VISION_FIELD_MAP


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


def _skip_val(val: Any) -> bool:
    if not val:
        return True
    return str(val).strip().lower() in {"no observable", "no visible", "ninguno", "n/a", "-"}


def events_from_vision_parsed(
    parsed: dict[str, Any] | None,
    *,
    frames_used: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    """Traduce JSON de visión a eventos forenses (cualquier tipo de incidente)."""
    if not parsed:
        return []
    events: list[dict[str, Any]] = []
    t0 = float((frames_used or [{}])[0].get("time_sec") or 0)
    t_label = (frames_used or [{}])[0].get("time_label") or "00:00:00"

    def add(ev_type: str, msg: str, severity: str = "high") -> None:
        if _skip_val(msg):
            return
        events.append(
            {
                "time_sec": t0,
                "time_label": t_label,
                "type": ev_type,
                "severity": severity,
                "message": f"IA visual: {str(msg).strip()}",
                "source": "vision_ai",
            }
        )

    for field, etype, _label in _VISION_FIELD_MAP:
        val = parsed.get(field)
        if _skip_val(val):
            continue
        sev = "critical" if etype in {"fire", "smoke", "collision"} else "high"
        add(etype, val, sev)

    for item in parsed.get("secuencia") or []:
        if not isinstance(item, dict):
            continue
        obs = str(item.get("observacion") or "").strip()
        if not obs:
            continue
        hora = item.get("hora") or t_label
        ts = float(item["time_sec"]) if isinstance(item.get("time_sec"), (int, float)) else t0
        ol = obs.lower()
        etype = "action"
        sev = "medium"
        if any(k in ol for k in ("fuego", "llama", "incendio", "humo")):
            etype, sev = ("fire" if "humo" not in ol else "smoke"), "critical"
        elif any(k in ol for k in ("chaleco", "reflect", "epp", "casco", "sin ")):
            etype, sev = "epp_non_compliant", "high"
        elif any(k in ol for k in ("proxim", "maquin", "retroceso", "camión", "grúa", "cerca")):
            etype, sev = "proximity", "high"
        elif any(k in ol for k in ("caída", "caida", "tropez", "atrap")):
            etype, sev = "fall_risk", "high"
        elif any(k in ol for k in ("zona", "restring", "carga suspend", "línea de fuego", "linea de fuego")):
            etype, sev = "zone", "high"
        elif any(k in ol for k in ("brigada", "emergenc", "bomber", "extintor")):
            etype, sev = "emergency_response", "medium"
        events.append(
            {
                "time_sec": ts,
                "time_label": hora,
                "type": etype,
                "severity": sev,
                "message": obs,
                "source": "vision_ai",
            }
        )
    return events
