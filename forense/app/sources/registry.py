"""Catálogo de fuentes de conocimiento Forense."""

from __future__ import annotations

from typing import Any

from ..knowledge_import import load_seed_packs, list_import_catalog

# Fuentes sincronizables vía POST /knowledge/sources/sync
SYNC_SOURCES: list[dict[str, Any]] = [
    {
        "id": "seeds_all",
        "name": "Plantillas curadas (todas)",
        "description": "iSafety, HFACS, BBS y situaciones por industria en español.",
        "industry": "general",
        "connector": "seeds",
        "license": "curated_vigiepp",
        "locale": "es-CL",
    },
    {
        "id": "seeds_mining",
        "name": "Plantillas — minería",
        "description": "Equipos móviles, zonas de carga, proximidad en faena minera.",
        "industry": "mineria",
        "connector": "seeds",
        "pack_id": "mineria",
        "license": "curated_vigiepp",
        "locale": "es-CL",
    },
    {
        "id": "seeds_port",
        "name": "Plantillas — portuario",
        "description": "Grúas, estiba, spreader, Ro-Ro y tránsito en patio.",
        "industry": "portuario",
        "connector": "seeds",
        "pack_id": "portuario",
        "license": "curated_vigiepp",
        "locale": "es-CL",
    },
    {
        "id": "seeds_warehouse",
        "name": "Plantillas — bodega / CD",
        "description": "Montacargas, pasillos, cruces ciegos y carga paletizada.",
        "industry": "bodega",
        "connector": "seeds",
        "pack_id": "bodega",
        "license": "curated_vigiepp",
        "locale": "es-CL",
    },
    {
        "id": "seeds_parking",
        "name": "Plantillas — parking / patio logístico",
        "description": "Retroceso, rampas, tránsito mixto peatón–vehículo en patios.",
        "industry": "parking",
        "connector": "seeds",
        "pack_id": "parking",
        "license": "curated_vigiepp",
        "locale": "es-CL",
    },
    {
        "id": "osha_mining",
        "name": "OSHA — minería (EE.UU.)",
        "description": "Accidentes reales: equipos móviles, caída de roca, vías de acarreo.",
        "industry": "mineria",
        "connector": "osha",
        "keywords": ["MINE", "MINING", "HAUL", "MOBILE EQUIPMENT", "FALL OF GROUND"],
        "license": "public_domain_us_gov",
        "locale": "en",
    },
    {
        "id": "osha_port",
        "name": "OSHA — portuario y marítimo",
        "description": "Grúas, muelle, estiba, contenedores y barcos.",
        "industry": "portuario",
        "connector": "osha",
        "keywords": ["MARITIME", "DOCK", "STEVEDORE", "CRANE", "CONTAINER", "SHIP"],
        "license": "public_domain_us_gov",
        "locale": "en",
    },
    {
        "id": "osha_warehouse",
        "name": "OSHA — bodega y montacargas",
        "description": "Colisiones, atropellos y actos inseguros en almacenes.",
        "industry": "bodega",
        "connector": "osha",
        "keywords": ["FORKLIFT", "WAREHOUSE", "PALLET", "STRUCK BY"],
        "license": "public_domain_us_gov",
        "locale": "en",
    },
    {
        "id": "osha_parking",
        "name": "OSHA — tránsito en patio / vehículos",
        "description": "Retroceso, peatones atropellados, vehículos en patio industrial.",
        "industry": "parking",
        "connector": "osha",
        "keywords": ["REVERSING", "BACKING", "STRUCK BY", "VEHICLE", "PEDESTRIAN", "YARD"],
        "license": "public_domain_us_gov",
        "locale": "en",
    },
    {
        "id": "emcip_port",
        "name": "EMCIP — casos marítimos portuarios",
        "description": "Narrativas basadas en taxonomía EMSA/EMCIP (Ro-Ro, grúas, cubierta).",
        "industry": "portuario",
        "connector": "curated_json",
        "json_file": "knowledge_emcip_samples.json",
        "live_fetch": True,
        "license": "emcip_public_reports",
        "locale": "es",
    },
    {
        "id": "sernageomin_chile",
        "name": "SERNAGEOMIN — patrones accidentabilidad minera Chile",
        "description": "Situaciones típicas de faenas chilenas según estadísticas públicas.",
        "industry": "mineria",
        "connector": "curated_json",
        "json_file": "knowledge_sernageomin_samples.json",
        "live_fetch": True,
        "license": "public_stats_chile",
        "locale": "es-CL",
    },
    {
        "id": "hse_uk",
        "name": "HSE UK — transporte y bodega",
        "description": "Patrones RIDDOR/HSG136: segregación peatón–vehículo en faena.",
        "industry": "bodega",
        "connector": "curated_json",
        "json_file": "knowledge_hse_samples.json",
        "license": "ogl_uk",
        "locale": "en",
    },
    {
        "id": "parking_curated",
        "name": "Parking / patios — casos curados",
        "description": "Estacionamientos, rampas, patios de carga y logística urbana.",
        "industry": "parking",
        "connector": "curated_json",
        "json_file": "knowledge_parking_samples.json",
        "license": "curated_vigiepp",
        "locale": "es-CL",
    },
]

URL_ALLOWLIST_SUFFIXES: tuple[str, ...] = (
    "osha.gov",
    "dol.gov",
    "hse.gov.uk",
    "emsa.europa.eu",
    "portal.emsa.europa.eu",
    "maib.gov.uk",
    "sernageomin.cl",
    "ntsb.gov",
    "gov.uk",
    "icmm.com",
    "msha.gov",
)


def list_sources_catalog() -> dict[str, Any]:
    """Catálogo unificado: fuentes sync + import legacy + packs semilla."""
    by_industry: dict[str, int] = {}
    for src in SYNC_SOURCES:
        ind = src.get("industry") or "general"
        by_industry[ind] = by_industry.get(ind, 0) + 1
    return {
        "sources": SYNC_SOURCES,
        "legacy_import": list_import_catalog(),
        "seed_packs": [{"id": p["id"], "name": p.get("name"), "count": len(p.get("entries") or [])} for p in load_seed_packs()],
        "industries": sorted(by_industry.keys()),
        "url_allowlist": list(URL_ALLOWLIST_SUFFIXES),
    }


def get_source(source_id: str) -> dict[str, Any] | None:
    for src in SYNC_SOURCES:
        if src["id"] == source_id:
            return dict(src)
    return None
