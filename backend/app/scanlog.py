"""Registro de escaneos: persona + cumplimiento EPP."""

from __future__ import annotations

import json
import threading
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

DATA_DIR = Path(__file__).resolve().parents[1] / "data"
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


def log_scan(event: ScanEvent) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with _lock:
        with EVENTS_FILE.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(asdict(event), ensure_ascii=False) + "\n")


def recent_scans(limit: int = 20) -> list[dict[str, Any]]:
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
