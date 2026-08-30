"""Registro de escaneos: persona + cumplimiento EPP."""

from __future__ import annotations

import json
import threading
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from typing import Any

from .paths import data_dir

DATA_DIR = data_dir()
EVENTS_FILE = DATA_DIR / "scan_events.jsonl"
_lock = threading.Lock()


@dataclass
class ScanEvent:
    ts: str
    worker_name: str | None
    worker_rut: str | None
    worker_id: str | None
    profile: str
    compliant: bool
    summary: str
    missing: list[str]
    detections: list[str]
    evidence_id: str | None = None


def log_scan(event: ScanEvent) -> None:
    global DATA_DIR, EVENTS_FILE
    DATA_DIR = data_dir()
    EVENTS_FILE = DATA_DIR / "scan_events.jsonl"
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with _lock, EVENTS_FILE.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(asdict(event), ensure_ascii=False) + "\n")


def purge_older_than(cutoff: datetime) -> int:
    """Elimina líneas de scan_events.jsonl anteriores a cutoff."""
    global DATA_DIR, EVENTS_FILE
    DATA_DIR = data_dir()
    EVENTS_FILE = DATA_DIR / "scan_events.jsonl"
    if not EVENTS_FILE.exists():
        return 0
    removed = 0
    kept: list[str] = []
    with _lock:
        for line in EVENTS_FILE.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                row = json.loads(line)
                ts = row.get("ts") or ""
                dt = datetime.fromisoformat(ts)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=UTC)
                if dt < cutoff:
                    removed += 1
                    continue
            except (json.JSONDecodeError, ValueError):
                pass
            kept.append(line)
        if removed:
            EVENTS_FILE.write_text("\n".join(kept) + ("\n" if kept else ""), encoding="utf-8")
    return removed


def recent_scans(limit: int = 20) -> list[dict[str, Any]]:
    global EVENTS_FILE
    EVENTS_FILE = data_dir() / "scan_events.jsonl"
    if not EVENTS_FILE.exists():
        return []
    with _lock:
        lines = EVENTS_FILE.read_text(encoding="utf-8").strip().splitlines()
    out: list[dict[str, Any]] = []
    for line in reversed(lines[-limit * 2 :]):
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            continue
        if len(out) >= limit:
            break
    return out
