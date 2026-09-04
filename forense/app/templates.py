"""Plantillas por industria — límites, perfiles e inferencia optimizada."""

from __future__ import annotations

from typing import Any

_DEFAULT_INFERENCE: dict[str, Any] = {
    "imgsz": 320,
    "base_interval_sec": 0.45,
    "motion_threshold": 11.0,
    "burst_interval_sec": 0.1,
    "burst_duration_sec": 4.5,
    "max_frames": 5000,
    "min_detection_confidence": 0.42,
    "min_box_area_ratio": 0.0008,
    "focus_burst_interval_sec": 0.12,
}

TEMPLATES: dict[str, dict[str, Any]] = {
    "mineria": {
        "id": "mineria",
        "name": "Minería / faena subterránea",
        "profile": "mineria",
        "max_machinery_kmh": 12.0,
        "max_person_kmh": 6.0,
        "min_distance_m": 3.0,
        "meters_per_pixel": 0.05,
        "intro": "Faena minera: equipos pesados, polvo, visibilidad reducida y zonas restringidas.",
        "inference": {**_DEFAULT_INFERENCE, "imgsz": 384, "motion_threshold": 9.0},
        "situation_focus": ["proximity", "epp_non_compliant", "zone", "speed_violation"],
    },
    "portuario": {
        "id": "portuario",
        "name": "Portuario / patio contenedores",
        "profile": "portuario",
        "max_machinery_kmh": 18.0,
        "max_person_kmh": 8.0,
        "min_distance_m": 2.5,
        "meters_per_pixel": 0.045,
        "intro": "Muelles y patios: grúas, reach stackers, tránsito mixto peatón–equipo.",
        "inference": {**_DEFAULT_INFERENCE, "imgsz": 384, "base_interval_sec": 0.4},
        "situation_focus": ["proximity", "zone", "action", "speed_violation"],
    },
    "bodega": {
        "id": "bodega",
        "name": "Bodega / centro de distribución",
        "profile": "epp_completo",
        "max_machinery_kmh": 15.0,
        "max_person_kmh": 8.0,
        "min_distance_m": 2.0,
        "meters_per_pixel": 0.04,
        "intro": "Logística: montacargas, pasillos estrechos, cruces ciegos y carga/descarga.",
        "inference": {**_DEFAULT_INFERENCE, "imgsz": 352, "motion_threshold": 10.0},
        "situation_focus": ["proximity", "action", "epp_non_compliant"],
    },
    "construccion": {
        "id": "construccion",
        "name": "Construcción / obra civil",
        "profile": "construccion",
        "max_machinery_kmh": 10.0,
        "max_person_kmh": 6.0,
        "min_distance_m": 2.5,
        "meters_per_pixel": 0.048,
        "intro": "Obra: maquinaria móvil, trabajos en altura, andamios y frentes activos.",
        "inference": {**_DEFAULT_INFERENCE, "imgsz": 384, "motion_threshold": 9.5},
        "situation_focus": ["fall_risk", "epp_non_compliant", "zone", "proximity"],
    },
    "petroquimica": {
        "id": "petroquimica",
        "name": "Petroquímica / refinería",
        "profile": "epp_completo",
        "max_machinery_kmh": 12.0,
        "max_person_kmh": 5.0,
        "min_distance_m": 3.5,
        "meters_per_pixel": 0.046,
        "intro": "Alta criticidad: áreas clasificadas, EPP completo y distanciamiento estricto.",
        "inference": {**_DEFAULT_INFERENCE, "imgsz": 384, "base_interval_sec": 0.35},
        "situation_focus": ["zone", "epp_non_compliant", "proximity"],
    },
    "energia": {
        "id": "energia",
        "name": "Energía / subestación y líneas",
        "profile": "epp_completo",
        "max_machinery_kmh": 14.0,
        "max_person_kmh": 6.0,
        "min_distance_m": 3.0,
        "meters_per_pixel": 0.05,
        "intro": "Subestaciones, salas eléctricas y mantenimiento con arnés y EPP dieléctrico.",
        "inference": {**_DEFAULT_INFERENCE, "imgsz": 352},
        "situation_focus": ["zone", "epp_non_compliant", "unsafe_act"],
    },
    "forestal": {
        "id": "forestal",
        "name": "Forestal / aserradero",
        "profile": "epp_completo",
        "max_machinery_kmh": 14.0,
        "max_person_kmh": 7.0,
        "min_distance_m": 2.5,
        "meters_per_pixel": 0.052,
        "intro": "Procesamiento madera: trozadores, cargadores y tránsito en patio.",
        "inference": {**_DEFAULT_INFERENCE, "imgsz": 352, "motion_threshold": 10.5},
        "situation_focus": ["proximity", "action", "speed_violation"],
    },
    "agroindustria": {
        "id": "agroindustria",
        "name": "Agroindustria / packing",
        "profile": "epp_completo",
        "max_machinery_kmh": 12.0,
        "max_person_kmh": 7.0,
        "min_distance_m": 2.0,
        "meters_per_pixel": 0.042,
        "intro": "Líneas de proceso, cintas, montacargas y alto flujo de personal.",
        "inference": {**_DEFAULT_INFERENCE, "imgsz": 320, "base_interval_sec": 0.4},
        "situation_focus": ["proximity", "epp_non_compliant", "action"],
    },
    "manufactura": {
        "id": "manufactura",
        "name": "Manufactura / planta industrial",
        "profile": "epp_completo",
        "max_machinery_kmh": 16.0,
        "max_person_kmh": 8.0,
        "min_distance_m": 2.0,
        "meters_per_pixel": 0.043,
        "intro": "Líneas de producción, robots colaborativos y mantenimiento en planta.",
        "inference": {**_DEFAULT_INFERENCE, "imgsz": 352},
        "situation_focus": ["zone", "proximity", "epp_non_compliant"],
    },
    "salud": {
        "id": "salud",
        "name": "Salud / hospital y clínica",
        "profile": "epp_completo",
        "max_machinery_kmh": 10.0,
        "max_person_kmh": 6.0,
        "min_distance_m": 1.5,
        "meters_per_pixel": 0.038,
        "intro": "Tránsito de camillas, equipos móviles y zonas de bioseguridad.",
        "inference": {**_DEFAULT_INFERENCE, "imgsz": 320, "motion_threshold": 12.0},
        "situation_focus": ["zone", "proximity", "unsafe_act"],
    },
    "escuela": {
        "id": "escuela",
        "name": "Educación / taller técnico",
        "profile": "escuela",
        "max_machinery_kmh": 8.0,
        "max_person_kmh": 5.0,
        "min_distance_m": 1.5,
        "meters_per_pixel": 0.04,
        "intro": "Talleres, laboratorios y prácticas con EPP básico (lentes, guantes).",
        "inference": {**_DEFAULT_INFERENCE, "imgsz": 320, "max_frames": 4000},
        "situation_focus": ["epp_non_compliant", "unsafe_act", "zone"],
    },
    "retail": {
        "id": "retail",
        "name": "Retail / centro comercial",
        "profile": "general",
        "max_machinery_kmh": 12.0,
        "max_person_kmh": 8.0,
        "min_distance_m": 1.5,
        "meters_per_pixel": 0.035,
        "intro": "Bodegas de tienda, montacargas en patio y zonas de carga trasera.",
        "inference": {**_DEFAULT_INFERENCE, "imgsz": 320},
        "situation_focus": ["proximity", "action", "zone"],
    },
    "transporte": {
        "id": "transporte",
        "name": "Transporte / terminal y patio",
        "profile": "portuario",
        "max_machinery_kmh": 20.0,
        "max_person_kmh": 8.0,
        "min_distance_m": 2.5,
        "meters_per_pixel": 0.048,
        "intro": "Terminales de buses/camiones, maniobras y peatones en patio.",
        "inference": {**_DEFAULT_INFERENCE, "imgsz": 384, "base_interval_sec": 0.38},
        "situation_focus": ["speed_violation", "proximity", "zone"],
    },
    "general": {
        "id": "general",
        "name": "General / EPP completo",
        "profile": "epp_completo",
        "max_machinery_kmh": 15.0,
        "max_person_kmh": 8.0,
        "min_distance_m": 2.0,
        "meters_per_pixel": 0.045,
        "intro": "Análisis general de faena industrial con perfil EPP completo.",
        "inference": dict(_DEFAULT_INFERENCE),
        "situation_focus": ["proximity", "epp_non_compliant", "action", "zone"],
    },
}


def list_templates() -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for v in TEMPLATES.values():
        inf = v.get("inference") or _DEFAULT_INFERENCE
        out.append(
            {
                "id": v["id"],
                "name": v["name"],
                "profile": v["profile"],
                "intro": v.get("intro", ""),
                "meters_per_pixel": v["meters_per_pixel"],
                "max_machinery_kmh": v["max_machinery_kmh"],
                "max_person_kmh": v["max_person_kmh"],
                "min_distance_m": v["min_distance_m"],
                "situation_focus": v.get("situation_focus") or [],
                "inference": inf,
            }
        )
    return sorted(out, key=lambda t: t["name"])


def resolve_template(template_id: str | None) -> dict[str, Any]:
    key = (template_id or "general").strip().lower()
    tpl = TEMPLATES.get(key) or TEMPLATES["general"]
    merged = dict(tpl)
    merged["inference"] = {**_DEFAULT_INFERENCE, **(tpl.get("inference") or {})}
    return merged


def inference_settings(template_id: str | None) -> dict[str, Any]:
    return dict(resolve_template(template_id).get("inference") or _DEFAULT_INFERENCE)
