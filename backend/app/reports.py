"""Estadísticas e informes a partir de escaneos y trabajadores."""

from __future__ import annotations

import csv
import io
import json
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from .paths import data_dir
from .scanlog import EVENTS_FILE, _lock, recent_scans  # noqa: F401


def _workers_file() -> Path:
    return data_dir() / "workers.json"


def _events_file() -> Path:
    return data_dir() / "scan_events.jsonl"


def _parse_ts(ts: str | None) -> datetime | None:
    if not ts:
        return None
    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except ValueError:
        return None


def load_all_scans(limit: int | None = None) -> list[dict[str, Any]]:
    events = _events_file()
    if not events.exists():
        return []
    with _lock:
        lines = events.read_text(encoding="utf-8").strip().splitlines()
    out: list[dict[str, Any]] = []
    for line in reversed(lines):
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            continue
        if limit is not None and len(out) >= limit:
            break
    return out


def load_workers() -> list[dict[str, Any]]:
    workers_file = _workers_file()
    if not workers_file.exists():
        return []
    try:
        data = json.loads(workers_file.read_text(encoding="utf-8"))
        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            if isinstance(data.get("workers"), list):
                return data["workers"]
            return list(data.values())
    except (json.JSONDecodeError, OSError):
        return []
    return []


def filter_scans(
    scans: list[dict[str, Any]],
    *,
    days: int | None = None,
    profile: str | None = None,
    compliant: bool | None = None,
    worker_id: str | None = None,
) -> list[dict[str, Any]]:
    cutoff = None
    if days is not None and days > 0:
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    out = []
    for s in scans:
        ts = _parse_ts(s.get("ts"))
        if cutoff and (ts is None or ts < cutoff):
            continue
        if profile and s.get("profile") != profile:
            continue
        if compliant is not None and bool(s.get("compliant")) != compliant:
            continue
        if worker_id and s.get("worker_id") != worker_id:
            continue
        out.append(s)
    return out


def compute_stats(days: int = 30, profile: str | None = None) -> dict[str, Any]:
    scans = filter_scans(load_all_scans(), days=days, profile=profile)
    workers = load_workers()
    total = len(scans)
    ok = sum(1 for s in scans if s.get("compliant"))
    bad = total - ok
    by_day: dict[str, dict[str, int]] = defaultdict(lambda: {"total": 0, "ok": 0, "bad": 0})
    by_profile: Counter[str] = Counter()
    by_worker: dict[str, dict[str, Any]] = {}
    missing_counter: Counter[str] = Counter()
    unknown = 0

    for s in scans:
        ts = _parse_ts(s.get("ts"))
        day = ts.date().isoformat() if ts else "sin-fecha"
        by_day[day]["total"] += 1
        if s.get("compliant"):
            by_day[day]["ok"] += 1
        else:
            by_day[day]["bad"] += 1
        by_profile[str(s.get("profile") or "—")] += 1
        for m in s.get("missing") or []:
            missing_counter[str(m)] += 1
        wid = s.get("worker_id") or s.get("worker_rut") or s.get("worker_name") or "desconocido"
        if not s.get("worker_id") and not s.get("worker_name"):
            unknown += 1
        slot = by_worker.setdefault(
            str(wid),
            {
                "name": s.get("worker_name") or "Desconocido",
                "rut": s.get("worker_rut"),
                "total": 0,
                "ok": 0,
                "bad": 0,
            },
        )
        slot["total"] += 1
        if s.get("compliant"):
            slot["ok"] += 1
        else:
            slot["bad"] += 1

    ranking = sorted(by_worker.values(), key=lambda x: (x["bad"], x["total"]), reverse=True)
    for w in ranking:
        t = max(1, int(w["total"]))
        w["safety_score"] = round((int(w["ok"]) / t) * 100, 1)
    days_sorted = sorted(by_day.items(), key=lambda x: x[0], reverse=True)[:14]
    rate = round((ok / total) * 100, 1) if total else 0.0

    return {
        "ok": True,
        "range_days": days,
        "profile": profile,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "totals": {
            "scans": total,
            "compliant": ok,
            "non_compliant": bad,
            "compliance_rate": rate,
            "safety_score": rate,
            "workers_enrolled": len(workers),
            "unknown_scans": unknown,
        },
        "by_day": [{"day": d, **v} for d, v in days_sorted],
        "by_profile": [{"profile": k, "count": v} for k, v in by_profile.most_common()],
        "missing_epp": [{"item": k, "count": v} for k, v in missing_counter.most_common(12)],
        "worker_ranking": ranking[:20],
        "recent": scans[:25],
    }


def export_csv(
    days: int | None = 30,
    *,
    only_non_compliant: bool = False,
    profile: str | None = None,
) -> str:
    scans = filter_scans(
        load_all_scans(),
        days=days,
        profile=profile,
        compliant=False if only_non_compliant else None,
    )
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(
        [
            "fecha_utc",
            "nombre",
            "rut",
            "worker_id",
            "perfil",
            "cumple",
            "resumen",
            "faltantes",
        ]
    )
    for s in scans:
        writer.writerow(
            [
                s.get("ts"),
                s.get("worker_name"),
                s.get("worker_rut"),
                s.get("worker_id"),
                s.get("profile"),
                "SI" if s.get("compliant") else "NO",
                s.get("summary"),
                ";".join(s.get("missing") or []),
            ]
        )
    return buf.getvalue()


def build_printable_report(
    days: int = 7,
    *,
    profile: str | None = None,
    title: str | None = None,
) -> dict[str, Any]:
    stats = compute_stats(days=days, profile=profile)
    t = stats["totals"]
    lines = [
        title or f"Informe VigiEPP — últimos {days} días",
        f"Generado: {stats['generated_at']}",
        "",
        f"Escaneos: {t['scans']}",
        f"Cumple: {t['compliant']}",
        f"No cumple: {t['non_compliant']}",
        f"Tasa cumplimiento: {t['compliance_rate']}%",
        f"Personas enroladas: {t['workers_enrolled']}",
        "",
        "EPP faltante más frecuente:",
    ]
    for m in stats["missing_epp"][:8]:
        lines.append(f"  - {m['item']}: {m['count']}")
    lines.append("")
    lines.append("Trabajadores con más incumplimientos:")
    for w in stats["worker_ranking"][:10]:
        lines.append(f"  - {w['name']} ({w.get('rut') or 's/RUT'}): {w['bad']}/{w['total']}")
    return {
        "ok": True,
        "title": title or f"Informe VigiEPP — {days}d",
        "days": days,
        "profile": profile,
        "stats": stats,
        "text": "\n".join(lines),
    }
