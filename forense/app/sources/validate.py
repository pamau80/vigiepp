"""Validación previa de lotes de conocimiento."""

from __future__ import annotations

from typing import Any

from ..knowledge import find_by_source_id
from .schema import normalize_record, validate_record


def validate_records(
    records: list[dict[str, Any]],
    *,
    default_industry: str = "general",
    check_duplicates: bool = True,
) -> dict[str, Any]:
    """Valida registros sin guardar; reporta duplicados por source+source_id."""
    valid: list[dict[str, Any]] = []
    invalid: list[dict[str, Any]] = []
    duplicates: list[dict[str, Any]] = []

    for i, raw in enumerate(records):
        rec = normalize_record(raw, default_industry=default_industry)
        issues = validate_record(rec)
        item = {"index": i, "title": rec.get("title"), "source_id": rec.get("source_id"), "issues": issues}
        if issues:
            invalid.append(item)
            continue
        if check_duplicates and rec.get("source_id"):
            existing = find_by_source_id(rec.get("source") or "", rec["source_id"])
            if existing:
                duplicates.append({**item, "existing_id": existing.get("id")})
                continue
        valid.append(rec)

    return {
        "ok": True,
        "total": len(records),
        "valid_count": len(valid),
        "invalid_count": len(invalid),
        "duplicate_count": len(duplicates),
        "valid": valid[:50],
        "invalid": invalid[:30],
        "duplicates": duplicates[:30],
    }
