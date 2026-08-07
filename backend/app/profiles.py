"""Perfiles de cumplimiento por tipo de faena / industria."""

from __future__ import annotations

from typing import TypedDict


class IndustryProfile(TypedDict):
    id: str
    name: str
    description: str
    required: list[str]
    optional: list[str]
    alert_message: str


# Claves internas alineadas al detector (casco, chaleco, lentes, guantes, arnes, persona)
PROFILES: dict[str, IndustryProfile] = {
    "portuario": {
        "id": "portuario",
        "name": "Faena portuaria",
        "description": "Muelles, patios de contenedores y zonas de carga.",
        "required": ["casco", "chaleco"],
        "optional": ["lentes", "guantes"],
        "alert_message": "Acceso a zona portuaria sin EPP completo",
    },
    "construccion": {
        "id": "construccion",
        "name": "Construcción",
        "description": "Obras civiles, andamios y frentes de trabajo.",
        "required": ["casco", "chaleco"],
        "optional": ["lentes", "guantes"],
        "alert_message": "Trabajador en obra sin EPP obligatorio",
    },
    "mineria": {
        "id": "mineria",
        "name": "Minería",
        "description": "Faenas mineras, patios de equipos y accesos.",
        "required": ["casco", "chaleco", "lentes"],
        "optional": ["guantes", "arnes"],
        "alert_message": "Incumplimiento EPP en zona minera",
    },
    "escuela": {
        "id": "escuela",
        "name": "Escuela / taller",
        "description": "Talleres técnicos, laboratorios y zonas de práctica.",
        "required": ["lentes"],
        "optional": ["casco", "guantes"],
        "alert_message": "Estudiante o personal sin protección en taller",
    },
    "general": {
        "id": "general",
        "name": "General / demo",
        "description": "Perfil amplio para demostraciones comerciales.",
        "required": ["casco", "chaleco"],
        "optional": ["lentes", "guantes", "arnes"],
        "alert_message": "Incumplimiento de EPP detectado",
    },
}


def list_profiles() -> list[IndustryProfile]:
    return list(PROFILES.values())


def get_profile(profile_id: str) -> IndustryProfile:
    return PROFILES.get(profile_id, PROFILES["general"])