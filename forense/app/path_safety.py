"""Validación de rutas y segmentos para evitar path traversal."""

from __future__ import annotations

import re
from pathlib import Path

_JOB_ID_RE = re.compile(r"^[a-f0-9]{8,32}$")
_ENTRY_ID_RE = re.compile(r"^kn-[a-f0-9]{8,12}$")


def safe_job_id(job_id: str) -> str | None:
    raw = (job_id or "").strip()
    if not raw or not _JOB_ID_RE.fullmatch(raw):
        return None
    return raw


def safe_entry_id(entry_id: str) -> str | None:
    raw = (entry_id or "").strip()
    if not raw or not _ENTRY_ID_RE.fullmatch(raw):
        return None
    return raw


def safe_keyframe_name(name: str) -> str | None:
    raw = (name or "").strip()
    if not raw or raw in {".", ".."}:
        return None
    if "/" in raw or "\\" in raw or ".." in raw:
        return None
    base = Path(raw).name
    if base != raw or not base:
        return None
    if not re.fullmatch(r"kf_\d{3}\.jpg", base):
        return None
    return base


def resolve_under(base: Path, *parts: str) -> Path | None:
    try:
        root = base.resolve()
        target = root.joinpath(*parts).resolve()
        if not target.is_relative_to(root):
            return None
        return target
    except (OSError, ValueError):
        return None
