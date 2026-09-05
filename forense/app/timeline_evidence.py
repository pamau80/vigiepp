"""Evidencia por evento y alertas prioritarias (todos los tipos de incidente)."""

from __future__ import annotations

from typing import Any

from .i18n_es_cl import label_event_type

# Tipos que merecen destacarse en el panel superior (cualquier faena)
_PRIORITY_TYPES = frozenset(
    {
        "fire",
        "smoke",
        "epp_reflective",
        "epp_non_compliant",
        "emergency_response",
        "proximity",
        "speed_violation",
        "action",
        "fall_risk",
        "unsafe_act",
        "zone",
        "collision",
        "knowledge_match",
    }
)

_SEVERITY_RANK = {"critical": 0, "high": 1, "medium": 2, "low": 3}

# Campos IA visual → tipo de evento (esquema general + compatibilidad legacy)
_VISION_FIELD_MAP: tuple[tuple[str, str, str], ...] = (
    ("epp_y_ropa", "epp_non_compliant", "EPP y ropa (IA visual)"),
    ("epp_chaleco_reflectante", "epp_reflective", "Ropa reflectante (IA visual)"),
    ("ropa_reflectante", "epp_reflective", "Ropa reflectante (IA visual)"),
    ("maquinaria_proximidad", "proximity", "Maquinaria y proximidad (IA visual)"),
    ("conducta_y_caidas", "action", "Conducta y caídas (IA visual)"),
    ("zonas_y_carga", "zone", "Zonas y carga (IA visual)"),
    ("energia_fuego_humo", "fire", "Fuego o humo (IA visual)"),
    ("fuego_contenedor", "fire", "Fuego (IA visual)"),
    ("humo", "smoke", "Humo (IA visual)"),
    ("respuesta_emergencia", "emergency_response", "Respuesta emergencia (IA visual)"),
    ("brigada_incendios", "emergency_response", "Respuesta emergencia (IA visual)"),
)


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
    """Primera ocurrencia por tipo — EPP, proximidad, zonas, fuego, etc."""
    job = job or {}
    seen: set[str] = set()
    alerts: list[dict[str, Any]] = []
    for ev in sorted(timeline or [], key=lambda e: float(e.get("time_sec") or 0)):
        if ev.get("review_status") == "dismissed":
            continue
        etype = str(ev.get("type") or "")
        if etype not in _PRIORITY_TYPES or etype in seen:
            continue
        seen.add(etype)
        alerts.append(
            {
                "type": etype,
                "label": label_event_type(etype),
                "severity": ev.get("severity") or "high",
                "time_sec": ev.get("time_sec"),
                "time_label": ev.get("time_label"),
                "message": ev.get("message"),
                "evidence_image": ev.get("evidence_image"),
                "source": ev.get("source") or "automático",
            }
        )

    va = (job.get("video_ai") or {}).get("parsed") or {}
    for field, etype, label in _VISION_FIELD_MAP:
        val = va.get(field)
        if not val or etype in seen:
            continue
        if isinstance(val, str) and val.strip().lower() in {"no observable", "no visible", "ninguno", "n/a", "-"}:
            continue
        seen.add(etype)
        sev = "critical" if etype in {"fire", "smoke", "collision"} else "high"
        alerts.append(
            {
                "type": etype,
                "label": label,
                "severity": sev,
                "time_sec": None,
                "time_label": None,
                "message": str(val),
                "evidence_image": None,
                "source": "vision_ai",
            }
        )

    alerts.sort(
        key=lambda a: (
            _SEVERITY_RANK.get(str(a.get("severity")), 9),
            float(a.get("time_sec") if a.get("time_sec") is not None else 1e9),
        )
    )
    return alerts
