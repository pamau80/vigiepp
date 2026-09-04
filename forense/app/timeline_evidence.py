"""Evidencia por evento: enlaza timeline con capturas clave."""

from __future__ import annotations

from typing import Any

_CRITICAL_TYPES = frozenset(
    {
        "fire",
        "smoke",
        "epp_reflective",
        "emergency_response",
        "epp_non_compliant",
        "proximity",
        "action",
        "fall_risk",
    }
)

_ALERT_LABELS: dict[str, str] = {
    "fire": "Incendio / llamas",
    "smoke": "Humo",
    "epp_reflective": "Sin ropa reflectante",
    "emergency_response": "Respuesta de emergencia",
    "epp_non_compliant": "Incumplimiento EPP",
    "proximity": "Proximidad crítica",
    "action": "Acción insegura",
    "fall_risk": "Riesgo de caída",
}


def enrich_timeline_evidence(
    timeline: list[dict[str, Any]],
    keyframes: list[dict[str, Any]],
    *,
    max_delta_sec: float = 1.2,
) -> list[dict[str, Any]]:
    if not timeline:
        return []
    kf_sorted = sorted(keyframes or [], key=lambda k: float(k.get("time_sec") or 0))
    out: list[dict[str, Any]] = []
    for ev in timeline:
        item = dict(ev)
        t = float(item.get("time_sec") or 0)
        best = None
        best_dt = max_delta_sec + 1
        for kf in kf_sorted:
            dt = abs(float(kf.get("time_sec") or 0) - t)
            if dt < best_dt:
                best_dt = dt
                best = kf
        if best and best_dt <= max_delta_sec and best.get("image"):
            item["evidence_image"] = best["image"]
            item["evidence_time_label"] = best.get("time_label")
        out.append(item)
    return out


def critical_alerts_summary(
    timeline: list[dict[str, Any]],
    job: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Agrupa alertas críticas para la UI (primera ocurrencia por tipo)."""
    job = job or {}
    seen: set[str] = set()
    alerts: list[dict[str, Any]] = []
    for ev in sorted(timeline or [], key=lambda e: float(e.get("time_sec") or 0)):
        etype = str(ev.get("type") or "")
        if etype not in _CRITICAL_TYPES or etype in seen:
            continue
        seen.add(etype)
        alerts.append(
            {
                "type": etype,
                "label": _ALERT_LABELS.get(etype, etype.replace("_", " ")),
                "severity": ev.get("severity") or "high",
                "time_sec": ev.get("time_sec"),
                "time_label": ev.get("time_label"),
                "message": ev.get("message"),
                "evidence_image": ev.get("evidence_image"),
            }
        )
    va = (job.get("video_ai") or {}).get("parsed") or {}
    for key, etype, label in (
        ("fuego_contenedor", "fire", "Incendio / llamas (IA visual)"),
        ("humo", "smoke", "Humo (IA visual)"),
        ("epp_chaleco_reflectante", "epp_reflective", "Sin ropa reflectante (IA visual)"),
        ("brigada_incendios", "emergency_response", "Brigada / emergencia (IA visual)"),
    ):
        if etype in seen or not va.get(key):
            continue
        seen.add(etype)
        alerts.append(
            {
                "type": etype,
                "label": label,
                "severity": "critical" if etype in {"fire", "smoke"} else "high",
                "time_sec": None,
                "time_label": None,
                "message": str(va[key]),
                "evidence_image": None,
                "source": "vision_ai",
            }
        )
    sev_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    alerts.sort(key=lambda a: (sev_order.get(str(a.get("severity")), 9), float(a.get("time_sec") or 0)))
    return alerts
