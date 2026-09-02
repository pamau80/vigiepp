"""Esquema normalizado de situaciones importadas."""

from __future__ import annotations

from typing import Any

VALID_INDUSTRIES = frozenset(
    {"general", "mineria", "portuario", "bodega", "construccion", "parking", "logistica"}
)

VALID_SITUATION_TYPES = frozenset(
    {
        "near_miss",
        "collision",
        "epp_violation",
        "zone_intrusion",
        "speed_excess",
        "proximity",
        "fall_risk",
        "unsafe_act",
        "other",
    }
)


def normalize_record(raw: dict[str, Any], *, default_industry: str = "general") -> dict[str, Any]:
    industry = (raw.get("industry") or default_industry or "general").strip().lower()
    if industry not in VALID_INDUSTRIES:
        industry = default_industry if default_industry in VALID_INDUSTRIES else "general"
    st = (raw.get("situation_type") or "other").strip().lower()
    if st not in VALID_SITUATION_TYPES:
        st = "other"
    title = (raw.get("title") or "").strip()[:200]
    description = (raw.get("description") or "").strip()[:4000]
    source = (raw.get("source") or "import").strip().lower()
    source_id = (raw.get("source_id") or "").strip() or None
    tags = [str(t).strip().lower() for t in (raw.get("tags") or []) if str(t).strip()][:20]
    labels = [str(x).strip() for x in (raw.get("labels") or []) if str(x).strip()][:20]
    event_types = [str(x).strip() for x in (raw.get("event_types") or []) if str(x).strip()][:20]
    return {
        "title": title,
        "situation_type": st,
        "description": description,
        "industry": industry,
        "tags": tags,
        "labels": labels,
        "event_types": event_types or [st],
        "source": source,
        "source_id": source_id,
        "meta": raw.get("meta") or {},
    }


def validate_record(rec: dict[str, Any]) -> list[str]:
    issues: list[str] = []
    if not (rec.get("title") or "").strip():
        issues.append("falta título")
    if len((rec.get("description") or "")) < 20:
        issues.append("descripción muy corta (< 20 caracteres)")
    ind = (rec.get("industry") or "").lower()
    if ind and ind not in VALID_INDUSTRIES:
        issues.append(f"industria desconocida: {ind}")
    st = (rec.get("situation_type") or "").lower()
    if st and st not in VALID_SITUATION_TYPES:
        issues.append(f"tipo de situación desconocido: {st}")
    return issues
