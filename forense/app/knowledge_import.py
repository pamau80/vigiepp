"""Importación de situaciones externas a la biblioteca Forense (semillas, OSHA, taxonomías)."""

from __future__ import annotations

import json
import logging
import re
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

from .knowledge import bulk_import_knowledge

logger = logging.getLogger("vigiepp.forense.knowledge_import")

_SEEDS_PATH = Path(__file__).with_name("knowledge_seeds.json")
_OSHA_SAMPLES_PATH = Path(__file__).with_name("knowledge_osha_samples.json")
_LABORDATA_ACCIDENT = "https://labordata.bunkum.us/osha_enforcement/accident.json"
_DOL_OSHA_ACCIDENT = "https://api.dol.gov/V1/Health%20and%20Safety/dol.osha.enforcement/accident"
_HTTP_TIMEOUT = 25
_USER_AGENT = "VigiEPP-Forense/1.0 (knowledge-import; +https://github.com/pamau80/vigiepp)"

IMPORT_CATALOG: list[dict[str, Any]] = [
    {
        "id": "seeds",
        "name": "Plantillas iSafety / HFACS / BBS",
        "description": "Situaciones curadas en español por industria (sin video).",
        "endpoint": "/api/forense/knowledge/import/seeds",
    },
    {
        "id": "osha_crane",
        "name": "OSHA — grúas e izaje",
        "description": "Casos reales de accidentes con grúas (Labor Data / OSHA IMIS).",
        "endpoint": "/api/forense/knowledge/import/osha",
        "default_keywords": ["CRANE", "HOIST", "LIFT"],
        "default_industry": "portuario",
    },
    {
        "id": "osha_maritime",
        "name": "OSHA — marítimo y muelle",
        "description": "Incidentes portuarios, barcos y estiba.",
        "endpoint": "/api/forense/knowledge/import/osha",
        "default_keywords": ["MARITIME", "SHIP", "DOCK", "STEVEDORE"],
        "default_industry": "portuario",
    },
    {
        "id": "osha_forklift",
        "name": "OSHA — montacargas y bodega",
        "description": "Colisiones y actos inseguros con montacargas.",
        "endpoint": "/api/forense/knowledge/import/osha",
        "default_keywords": ["FORKLIFT", "PALLET", "WAREHOUSE"],
        "default_industry": "bodega",
    },
    {
        "id": "osha_construction",
        "name": "OSHA — construcción",
        "description": "Caídas, golpes y actos inseguros en obra.",
        "endpoint": "/api/forense/knowledge/import/osha",
        "default_keywords": ["CONSTRUCTION", "SCAFFOLD", "FALL"],
        "default_industry": "construccion",
    },
    {
        "id": "osha_ppe",
        "name": "OSHA — EPP",
        "description": "Incumplimientos de casco, arnés y protección personal.",
        "endpoint": "/api/forense/knowledge/import/osha",
        "default_keywords": ["HELMET", "HARNESS", "PPE", "RESPIRATOR"],
        "default_industry": "general",
    },
]

_OSHA_KEYWORD_INDUSTRY: list[tuple[str, str]] = [
    ("MARITIME", "portuario"),
    ("SHIP", "portuario"),
    ("DOCK", "portuario"),
    ("PORT", "portuario"),
    ("STEVEDORE", "portuario"),
    ("CONTAINER", "portuario"),
    ("FORKLIFT", "bodega"),
    ("WAREHOUSE", "bodega"),
    ("PALLET", "bodega"),
    ("MINING", "mineria"),
    ("MINE", "mineria"),
    ("CONSTRUCTION", "construccion"),
    ("SCAFFOLD", "construccion"),
    ("CRANE", "portuario"),
    ("HOIST", "construccion"),
]

_OSHA_KEYWORD_SITUATION: list[tuple[str, str]] = [
    ("STRUCK BY", "collision"),
    ("COLLISION", "collision"),
    ("CRUSH", "collision"),
    ("FALL", "fall_risk"),
    ("SCAFFOLD", "fall_risk"),
    ("HELMET", "epp_violation"),
    ("HARNESS", "epp_violation"),
    ("PPE", "epp_violation"),
    ("RESPIRATOR", "epp_violation"),
    ("PROXIMITY", "proximity"),
    ("LINE OF FIRE", "proximity"),
    ("ZONE", "zone_intrusion"),
    ("SPEED", "speed_excess"),
    ("NEAR MISS", "near_miss"),
]


def list_import_catalog() -> list[dict[str, Any]]:
    packs = load_seed_packs()
    catalog = list(IMPORT_CATALOG)
    for pack in packs:
        catalog.append(
            {
                "id": f"seed_pack:{pack['id']}",
                "name": pack.get("name", pack["id"]),
                "description": pack.get("description", ""),
                "endpoint": "/api/forense/knowledge/import/seeds",
                "pack_id": pack["id"],
                "count": len(pack.get("entries") or []),
            }
        )
    return catalog


def load_seed_packs() -> list[dict[str, Any]]:
    if not _SEEDS_PATH.is_file():
        return []
    data = json.loads(_SEEDS_PATH.read_text(encoding="utf-8"))
    return data.get("packs") or []


def _http_get_json(url: str, headers: dict[str, str] | None = None) -> dict[str, Any]:
    hdrs = {"Accept": "application/json", "User-Agent": _USER_AGENT, **(headers or {})}
    req = urllib.request.Request(url, headers=hdrs)
    with urllib.request.urlopen(req, timeout=_HTTP_TIMEOUT) as resp:
        return json.loads(resp.read().decode("utf-8"))


def load_osha_samples() -> list[dict[str, Any]]:
    if not _OSHA_SAMPLES_PATH.is_file():
        return []
    data = json.loads(_OSHA_SAMPLES_PATH.read_text(encoding="utf-8"))
    return list(data.get("records") or [])


def _filter_osha_rows_by_keywords(rows: list[dict[str, Any]], keywords: list[str]) -> list[dict[str, Any]]:
    if not keywords:
        return rows
    kws = [k.upper() for k in keywords if k.strip()]
    out: list[dict[str, Any]] = []
    for row in rows:
        blob = f"{row.get('event_keyword') or ''} {row.get('event_desc') or ''} {row.get('abstract_text') or ''}".upper()
        if any(k in blob for k in kws):
            out.append(row)
    return out


def _title_case_words(text: str, max_len: int = 120) -> str:
    text = re.sub(r"\s+", " ", (text or "").strip())
    if not text or text.upper() in ("NONE", "N/A"):
        return ""
    if len(text) <= max_len:
        return text[0].upper() + text[1:] if text else text
    return text[: max_len - 1].rstrip() + "…"


def _map_osha_industry(keywords: str, event_desc: str, default: str) -> str:
    blob = f"{keywords} {event_desc}".upper()
    for needle, industry in _OSHA_KEYWORD_INDUSTRY:
        if needle in blob:
            return industry
    return default


def _map_osha_situation(keywords: str, event_desc: str) -> str:
    blob = f"{keywords} {event_desc}".upper()
    for needle, stype in _OSHA_KEYWORD_SITUATION:
        if needle in blob:
            return stype
    return "unsafe_act"


def osha_row_to_entry(row: dict[str, Any], *, default_industry: str = "general") -> dict[str, Any] | None:
    event_desc = (row.get("event_desc") or "").strip()
    abstract = (row.get("abstract_text") or "").strip()
    keywords = (row.get("event_keyword") or "").strip()
    summary_nr = row.get("summary_nr")
    if not event_desc and not abstract:
        return None
    title = _title_case_words(event_desc or abstract.split(".")[0], 120)
    if not title:
        return None
    parts = [p for p in (abstract, event_desc, f"Palabras clave: {keywords.replace(',', ', ')}") if p and p.upper() != "NONE"]
    description = " ".join(dict.fromkeys(parts))[:3800]
    industry = _map_osha_industry(keywords, event_desc, default_industry)
    situation_type = _map_osha_situation(keywords, event_desc)
    tags = [t.strip().lower() for t in keywords.split(",") if t.strip()][:12]
    labels = ["osha", "fatality"] if (row.get("fatality") or "").upper() == "X" else ["osha"]
    event_date = (row.get("event_date") or "")[:10]
    return {
        "title": title,
        "situation_type": situation_type,
        "description": description,
        "industry": industry,
        "labels": labels,
        "event_types": ["action", situation_type],
        "tags": tags,
        "source": "osha",
        "source_id": f"osha:{summary_nr}",
        "meta": {"event_date": event_date, "summary_nr": summary_nr},
    }


def fetch_osha_labordata(
    *,
    keywords: list[str],
    limit_per_keyword: int = 15,
    fatality_only: bool = False,
) -> list[dict[str, Any]]:
    """Descarga accidentes OSHA vía Labor Data; si falla, usa paquete local."""
    rows: list[dict[str, Any]] = []
    seen: set[int] = set()
    live_ok = False

    for kw in keywords:
        kw = (kw or "").strip().upper()
        if not kw:
            continue
        params: dict[str, str] = {
            "_size": str(min(max(limit_per_keyword, 1), 50)),
            "event_keyword__contains": kw,
        }
        if fatality_only:
            params["fatality"] = "X"
        url = f"{_LABORDATA_ACCIDENT}?{urllib.parse.urlencode(params)}"
        try:
            payload = _http_get_json(url)
            live_ok = True
        except Exception as exc:
            logger.warning("OSHA fetch falló para %s: %s", kw, exc)
            continue
        for row in payload.get("rows") or []:
            sn = row.get("summary_nr")
            if sn in seen:
                continue
            seen.add(sn)
            rows.append(row)

    if not live_ok and not rows:
        samples = _filter_osha_rows_by_keywords(load_osha_samples(), keywords)
        cap = limit_per_keyword * max(len(keywords), 1)
        logger.info("Usando %d registros OSHA locales (labordata no disponible)", len(samples[:cap]))
        return samples[:cap]

    return rows


def fetch_osha_dol(
    *,
    keywords: list[str],
    limit: int = 20,
    api_key: str,
) -> list[dict[str, Any]]:
    """OSHA oficial (api.dol.gov) — requiere VIGIEPP_FORENSE_DOL_API_KEY."""
    if not api_key:
        return []
    rows: list[dict[str, Any]] = []
    for kw in keywords[:3]:
        params = urllib.parse.urlencode({"limit": min(limit, 50), "event_keyword": kw})
        url = f"{_DOL_OSHA_ACCIDENT}?{params}"
        try:
            payload = _http_get_json(url, headers={"X-API-KEY": api_key})
        except Exception as exc:
            logger.warning("DOL OSHA fetch falló: %s", exc)
            continue
        data = payload.get("data") or payload.get("rows") or []
        if isinstance(data, list):
            rows.extend(data)
    return rows


def import_osha(
    *,
    keywords: list[str] | None = None,
    limit_per_keyword: int = 12,
    default_industry: str = "general",
    fatality_only: bool = False,
    skip_existing: bool = True,
    dol_api_key: str | None = None,
) -> dict[str, Any]:
    kws = [k.strip().upper() for k in (keywords or ["CRANE", "FORKLIFT", "FALL"]) if k.strip()]
    raw = fetch_osha_labordata(
        keywords=kws,
        limit_per_keyword=limit_per_keyword,
        fatality_only=fatality_only,
    )
    if dol_api_key:
        raw.extend(fetch_osha_dol(keywords=kws, limit=limit_per_keyword, api_key=dol_api_key))

    records: list[dict[str, Any]] = []
    for row in raw:
        entry = osha_row_to_entry(row, default_industry=default_industry)
        if entry:
            records.append(entry)

    result = bulk_import_knowledge(records, skip_existing=skip_existing)
    result["fetched"] = len(raw)
    result["keywords"] = kws
    result["source"] = "osha"
    result["live_fetch"] = any(
        r.get("summary_nr") not in {s.get("summary_nr") for s in load_osha_samples()} for r in raw
    ) if raw else False
    return result


def import_seeds(
    *,
    pack_id: str | None = None,
    industry: str | None = None,
    limit: int | None = None,
    skip_existing: bool = True,
) -> dict[str, Any]:
    packs = load_seed_packs()
    if not packs:
        return {"imported": 0, "skipped": 0, "errors": ["Archivo de semillas no encontrado"], "source": "seed"}

    records: list[dict[str, Any]] = []
    industry_filter = (industry or "").strip().lower()

    for pack in packs:
        if pack_id and pack.get("id") != pack_id:
            continue
        for item in pack.get("entries") or []:
            if industry_filter and (item.get("industry") or "general").lower() != industry_filter:
                continue
            rec = dict(item)
            rec.setdefault("source", "seed")
            if not rec.get("source_id"):
                rec["source_id"] = f"seed:{pack.get('id')}:{rec.get('title', '')[:40]}"
            records.append(rec)

    if limit and limit > 0:
        records = records[:limit]

    result = bulk_import_knowledge(records, skip_existing=skip_existing)
    result["source"] = "seed"
    result["pack_id"] = pack_id
    result["candidates"] = len(records)
    return result
