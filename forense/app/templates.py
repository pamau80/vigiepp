"""Plantillas por industria — límites y perfiles predefinidos."""

from __future__ import annotations

from typing import Any

TEMPLATES: dict[str, dict[str, Any]] = {
    "mineria": {
        "id": "mineria",
        "name": "Minería / faena subterránea",
        "profile": "mineria",
        "max_machinery_kmh": 12.0,
        "max_person_kmh": 6.0,
        "min_distance_m": 3.0,
        "meters_per_pixel": 0.05,
        "intro": "Análisis bajo perfil minería: maquinaria pesada, zonas restringidas y EPP crítico.",
    },
    "portuario": {
        "id": "portuario",
        "name": "Portuario / patio contenedores",
        "profile": "portuario",
        "max_machinery_kmh": 18.0,
        "max_person_kmh": 8.0,
        "min_distance_m": 2.5,
        "meters_per_pixel": 0.045,
        "intro": "Análisis portuario: tránsito de equipos, grúas y peatones en muelle.",
    },
    "bodega": {
        "id": "bodega",
        "name": "Bodega / centro de distribución",
        "profile": "epp_completo",
        "max_machinery_kmh": 15.0,
        "max_person_kmh": 8.0,
        "min_distance_m": 2.0,
        "meters_per_pixel": 0.04,
        "intro": "Análisis logístico: montacargas, pasillos y zonas de carga.",
    },
    "construccion": {
        "id": "construccion",
        "name": "Construcción / obra civil",
        "profile": "construccion",
        "max_machinery_kmh": 10.0,
        "max_person_kmh": 6.0,
        "min_distance_m": 2.5,
        "meters_per_pixel": 0.048,
        "intro": "Análisis en obra: maquinaria móvil, trabajos en altura y EPP.",
    },
    "general": {
        "id": "general",
        "name": "General / EPP completo",
        "profile": "epp_completo",
        "max_machinery_kmh": 15.0,
        "max_person_kmh": 8.0,
        "min_distance_m": 2.0,
        "meters_per_pixel": 0.045,
        "intro": "Análisis general de faena industrial.",
    },
}


def list_templates() -> list[dict[str, Any]]:
    return [{"id": k, "name": v["name"], "profile": v["profile"]} for k, v in TEMPLATES.items()]


def resolve_template(template_id: str | None) -> dict[str, Any]:
    key = (template_id or "general").strip().lower()
    return dict(TEMPLATES.get(key) or TEMPLATES["general"])
