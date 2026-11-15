"""Sincronización de fuentes externas hacia biblioteca Forense."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from ..config import DOL_API_KEY
from ..knowledge import bulk_import_knowledge
from ..knowledge_import import import_osha, import_seeds
from .live_fetch import fetch_live_records
from .registry import get_source
from .schema import normalize_record
from .validate import validate_records

logger = logging.getLogger("vigiepp.forense.sources.sync")

_APP_DIR = Path(__file__).resolve().parent.parent


def _load_curated_json(filename: str) -> list[dict[str, Any]]:
    path = _APP_DIR / filename
    if not path.is_file():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    return list(data.get("records") or [])


def _import_curated_records(
    records: list[dict[str, Any]],
    *,
    source: str,
    default_industry: str,
    skip_existing: bool,
) -> dict[str, Any]:
    normalized: list[dict[str, Any]] = []
    for raw in records:
        rec = normalize_record({**raw, "source": raw.get("source") or source}, default_industry=default_industry)
        if rec["title"]:
            normalized.append(rec)
    result = bulk_import_knowledge(normalized, skip_existing=skip_existing)
    result["candidates"] = len(records)
    result["source"] = source
    return result


def _collect_source_records(src: dict[str, Any], *, limit: int | None = None) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Carga registros candidatos de una fuente sin importar."""
    connector = src.get("connector")
    industry = src.get("industry") or "general"
    meta: dict[str, Any] = {}
    records: list[dict[str, Any]] = []

    if connector == "seeds":
        from ..knowledge_import import load_seed_packs

        packs = load_seed_packs()
        pack_id = src.get("pack_id")
        industry_filter = industry if not pack_id else ""
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
        return records, meta

    if connector == "curated_json":
        source_id = src.get("id") or ""
        if src.get("live_fetch"):
            live = fetch_live_records(source_id, limit=limit)
            meta = {k: v for k, v in live.items() if k not in ("records", "ok")}
            records.extend(live.get("records") or [])
        curated = _load_curated_json(src.get("json_file") or "")
        if limit and limit > 0 and records:
            remaining = max(0, limit - len(records))
            curated = curated[:remaining] if remaining else []
        elif limit and limit > 0 and not records:
            curated = curated[:limit]
        records.extend(curated)
        return records, meta

    return records, meta


def preview_source(source_id: str, *, limit: int | None = 20) -> dict[str, Any]:
    """Valida registros de una fuente sin importarlos (preview para UI)."""
    src = get_source(source_id)
    if not src:
        return {"ok": False, "error": f"Fuente desconocida: {source_id}"}
    industry = src.get("industry") or "general"
    if src.get("connector") == "osha":
        return {
            "ok": True,
            "source_id": source_id,
            "preview": "limited",
            "message": "OSHA se valida al sincronizar (fetch remoto).",
        }
    records, meta = _collect_source_records(src, limit=limit)
    validation = validate_records(records, default_industry=industry, check_duplicates=True)
    return {
        "ok": True,
        "source_id": source_id,
        "candidates": len(records),
        **validation,
        **meta,
    }


def sync_source(
    source_id: str,
    *,
    limit: int | None = None,
    skip_existing: bool = True,
    fatality_only: bool = False,
) -> dict[str, Any]:
    """Importa una fuente registrada al catálogo."""
    src = get_source(source_id)
    if not src:
        return {"ok": False, "error": f"Fuente desconocida: {source_id}"}

    connector = src.get("connector")
    industry = src.get("industry") or "general"

    if connector == "seeds":
        result = import_seeds(
            pack_id=src.get("pack_id"),
            industry=industry if not src.get("pack_id") else None,
            limit=limit,
            skip_existing=skip_existing,
        )
        result["ok"] = True
        result["source_id"] = source_id
        return result

    if connector == "osha":
        keywords = list(src.get("keywords") or [])
        limit_kw = min(limit or 12, 50)
        result = import_osha(
            keywords=keywords,
            limit_per_keyword=limit_kw,
            default_industry=industry,
            fatality_only=fatality_only,
            skip_existing=skip_existing,
            dol_api_key=DOL_API_KEY or None,
        )
        result["ok"] = True
        result["source_id"] = source_id
        return result

    if connector == "curated_json":
        records: list[dict[str, Any]] = []
        live_meta: dict[str, Any] = {}
        if src.get("live_fetch"):
            live = fetch_live_records(source_id, limit=limit)
            live_meta = {k: v for k, v in live.items() if k not in ("records", "ok")}
            records.extend(live.get("records") or [])
        curated = _load_curated_json(src.get("json_file") or "")
        if limit and limit > 0 and records:
            remaining = max(0, limit - len(records))
            curated = curated[:remaining] if remaining else []
        elif limit and limit > 0 and not records:
            curated = curated[:limit]
        records.extend(curated)
        source_name = source_id.split("_")[0] if "_" in source_id else source_id
        result = _import_curated_records(
            records,
            source=source_name,
            default_industry=industry,
            skip_existing=skip_existing,
        )
        result["ok"] = True
        result["source_id"] = source_id
        result["json_file"] = src.get("json_file")
        result.update(live_meta)
        if src.get("live_fetch") and not live.get("ok"):
            result["live_fallback"] = True
            result["live_error"] = live.get("error")
        return result

    return {"ok": False, "error": f"Conector no implementado: {connector}"}


def sync_all_by_industry(
    industry: str,
    *,
    limit_per_source: int = 15,
    skip_existing: bool = True,
) -> dict[str, Any]:
    """Sincroniza todas las fuentes de una industria."""
    from .registry import SYNC_SOURCES

    ind = industry.strip().lower()
    results: list[dict[str, Any]] = []
    total_imported = 0
    for src in SYNC_SOURCES:
        if (src.get("industry") or "general") != ind:
            continue
        r = sync_source(src["id"], limit=limit_per_source, skip_existing=skip_existing)
        results.append({"source_id": src["id"], **r})
        total_imported += int(r.get("imported") or 0)
    return {"ok": True, "industry": ind, "total_imported": total_imported, "results": results}
