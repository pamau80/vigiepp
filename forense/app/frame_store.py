"""Almacén incremental de análisis por frame (JSONL) para revisión en video."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .config import JOBS_DIR


def frames_path(job_id: str) -> Path:
    return JOBS_DIR / job_id / "frames.jsonl"


def clear_frames(job_id: str) -> None:
    p = frames_path(job_id)
    if p.is_file():
        p.unlink()


def append_frame(job_id: str, record: dict[str, Any]) -> None:
    p = frames_path(job_id)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, ensure_ascii=False) + "\n")


def count_frames(job_id: str) -> int:
    p = frames_path(job_id)
    if not p.is_file():
        return 0
    return sum(1 for _ in p.open(encoding="utf-8"))


def read_frames(
    job_id: str,
    *,
    from_sec: float = 0.0,
    until_sec: float | None = None,
    limit: int = 800,
) -> list[dict[str, Any]]:
    p = frames_path(job_id)
    if not p.is_file():
        return []
    out: list[dict[str, Any]] = []
    for line in p.open(encoding="utf-8"):
        line = line.strip()
        if not line:
            continue
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            continue
        t = float(rec.get("time_sec") or 0)
        if t < from_sec:
            continue
        if until_sec is not None and t > until_sec:
            continue
        out.append(rec)
        if len(out) >= limit:
            break
    return out


def nearest_frame(job_id: str, time_sec: float) -> dict[str, Any] | None:
    best: dict[str, Any] | None = None
    best_dt = 1e9
    for rec in read_frames(job_id, from_sec=max(0.0, time_sec - 3.0), until_sec=time_sec + 3.0, limit=200):
        dt = abs(float(rec.get("time_sec") or 0) - time_sec)
        if dt < best_dt:
            best_dt = dt
            best = rec
    return best
