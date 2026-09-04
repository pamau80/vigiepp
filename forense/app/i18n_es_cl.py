"""Etiquetas en español de Chile para informes y API Forense."""

from __future__ import annotations

STATUS_LABELS: dict[str, str] = {
    "queued": "en cola",
    "processing": "procesando",
    "done": "completado",
    "error": "error",
}

KIND_LABELS: dict[str, str] = {
    "person": "persona",
    "machinery": "maquinaria",
    "other": "otro",
}

EVENT_TYPE_LABELS: dict[str, str] = {
    "action": "acción",
    "epp_non_compliant": "incumplimiento EPP",
    "zone": "zona restringida",
    "speed_violation": "exceso de velocidad",
    "proximity": "proximidad crítica",
    "knowledge_match": "coincidencia biblioteca",
    "knowledge_conjecture": "conjetura biblioteca",
    "collision": "colisión",
    "fall_risk": "riesgo de caída",
    "unsafe_act": "acto inseguro",
    "fire": "incendio / llamas",
    "smoke": "humo",
    "epp_reflective": "sin ropa reflectante",
    "emergency_response": "respuesta de emergencia",
    "collision": "colisión / golpe",
}

SEVERITY_LABELS: dict[str, str] = {
    "critical": "crítica",
    "high": "alta",
    "medium": "media",
    "low": "baja",
}


def label_event_type(code: str) -> str:
    return EVENT_TYPE_LABELS.get(code, (code or "—").replace("_", " "))


def label_kind(code: str) -> str:
    return KIND_LABELS.get(code, code or "—")


def label_severity(code: str) -> str:
    return SEVERITY_LABELS.get(code, code or "—")
