"""Estadísticas e informes a partir de escaneos y trabajadores."""

from __future__ import annotations

import csv
import io
import json
from collections import Counter, defaultdict
from datetime import UTC, datetime, timedelta
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
        return datetime.fromisoformat(ts)
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
        cutoff = datetime.now(UTC) - timedelta(days=days)
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
        base = (int(w["ok"]) / t) * 100
        # Recidiva: muchos fallos bajan más el score individual
        recidiva = min(15.0, (int(w["bad"]) / t) * 20.0)
        w["safety_score"] = round(max(0.0, base - recidiva * 0.25), 1)
    days_sorted = sorted(by_day.items(), key=lambda x: x[0], reverse=True)[:14]
    rate = round((ok / total) * 100, 1) if total else 0.0

    # Safety Score global ponderado (no solo compliance_rate)
    CRITICAL = {
        "casco",
        "hardhat",
        "helmet",
        "arnés",
        "arnes",
        "chaleco",
        "safety vest",
        "vest",
        "lentes",
        "goggles",
    }
    critical_hits = 0
    for item, count in missing_counter.items():
        low = str(item).lower()
        if any(c in low for c in CRITICAL):
            critical_hits += int(count)
    unknown_ratio = (unknown / total) if total else 0.0
    critical_ratio = (critical_hits / max(1, bad)) if bad else 0.0
    penalty_unknown = min(20.0, unknown_ratio * 40.0)
    penalty_critical = min(25.0, critical_ratio * 25.0)
    # Promedio de scores por trabajador (si hay)
    if ranking:
        avg_worker = sum(float(w.get("safety_score") or 0) for w in ranking) / len(ranking)
        blended = rate * 0.55 + avg_worker * 0.45
    else:
        blended = rate
    safety_score = round(max(0.0, min(100.0, blended - penalty_unknown - penalty_critical)), 1)

    return {
        "ok": True,
        "range_days": days,
        "profile": profile,
        "generated_at": datetime.now(UTC).isoformat(),
        "totals": {
            "scans": total,
            "compliant": ok,
            "non_compliant": bad,
            "compliance_rate": rate,
            "safety_score": safety_score,
            "safety_breakdown": {
                "compliance_rate": rate,
                "penalty_unknown": round(penalty_unknown, 1),
                "penalty_critical_missing": round(penalty_critical, 1),
                "unknown_scans": unknown,
                "critical_missing_events": critical_hits,
            },
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
            "evidence_id",
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
                s.get("evidence_id") or "",
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
    br = t.get("safety_breakdown") or {}
    lines = [
        title or f"Informe VigiEPP — últimos {days} días",
        f"Generado: {stats['generated_at']}",
        "",
        f"Escaneos: {t['scans']}",
        f"Cumple: {t['compliant']}",
        f"No cumple: {t['non_compliant']}",
        f"Tasa cumplimiento: {t['compliance_rate']}%",
        f"Safety Score: {t.get('safety_score', t['compliance_rate'])}/100",
        f"  - Penaliz. desconocidos: -{br.get('penalty_unknown', 0)}",
        f"  - Penaliz. EPP crítico: -{br.get('penalty_critical_missing', 0)}",
        f"Personas enroladas: {t['workers_enrolled']}",
        f"Escaneos sin identidad: {t.get('unknown_scans', 0)}",
        "",
        "EPP faltante más frecuente:",
    ]
    for m in stats["missing_epp"][:8]:
        lines.append(f"  - {m['item']}: {m['count']}")
    lines.append("")
    lines.append("Trabajadores (score / fallas):")
    for w in stats["worker_ranking"][:10]:
        lines.append(
            f"  - {w['name']} ({w.get('rut') or 's/RUT'}): "
            f"score {w.get('safety_score', '—')} · {w['bad']}/{w['total']} fallas"
        )
    lines.append("")
    lines.append("Últimos incumplimientos con evidencia:")
    bad_recent = [s for s in (stats.get("recent") or []) if not s.get("compliant")][:12]
    if not bad_recent:
        lines.append("  (sin incumplimientos en el rango)")
    for s in bad_recent:
        evid = s.get("evidence_id") or "—"
        lines.append(
            f"  - {s.get('ts', '')[:19]} · {s.get('worker_name') or 'Desconocido'} · "
            f"{', '.join(s.get('missing') or []) or s.get('summary') or '—'} · evidencia {evid}"
        )
    lines.append("")
    lines.append("— Fin del informe VigiEPP —")

    html = _printable_html(
        title=title or f"Informe VigiEPP — {days}d",
        generated=stats["generated_at"],
        totals=t,
        breakdown=br,
        missing=stats["missing_epp"][:8],
        ranking=stats["worker_ranking"][:10],
        bad_recent=bad_recent,
        days=days,
        profile=profile,
    )
    return {
        "ok": True,
        "title": title or f"Informe VigiEPP — {days}d",
        "days": days,
        "profile": profile,
        "stats": stats,
        "text": "\n".join(lines),
        "html": html,
    }


def _printable_html(
    *,
    title: str,
    generated: str,
    totals: dict[str, Any],
    breakdown: dict[str, Any],
    missing: list[dict[str, Any]],
    ranking: list[dict[str, Any]],
    bad_recent: list[dict[str, Any]],
    days: int,
    profile: str | None,
) -> str:
    def esc(x: Any) -> str:
        return (
            str(x if x is not None else "")
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
        )

    miss_rows = "".join(
        f"<tr><td>{esc(m.get('item'))}</td><td>{esc(m.get('count'))}</td></tr>" for m in missing
    ) or "<tr><td colspan='2'>Sin datos</td></tr>"
    rank_rows = "".join(
        f"<tr><td>{esc(w.get('name'))}</td><td>{esc(w.get('rut'))}</td>"
        f"<td>{esc(w.get('safety_score'))}</td><td>{esc(w.get('bad'))}/{esc(w.get('total'))}</td></tr>"
        for w in ranking
    ) or "<tr><td colspan='4'>Sin datos</td></tr>"
    evid_rows = "".join(
        f"<tr><td>{esc(str(s.get('ts') or '')[:19])}</td><td>{esc(s.get('worker_name') or 'Desconocido')}</td>"
        f"<td>{esc(', '.join(s.get('missing') or []) or s.get('summary'))}</td>"
        f"<td>{('<a href=\"/api/evidence/' + esc(s.get('evidence_id')) + '\" target=\"_blank\">ver</a>') if s.get('evidence_id') else '—'}</td></tr>"
        for s in bad_recent
    ) or "<tr><td colspan='4'>Sin incumplimientos</td></tr>"

    return f"""<!DOCTYPE html>
<html lang="es"><head><meta charset="utf-8"/>
<title>{esc(title)}</title>
<style>
  body {{ font-family: Georgia, serif; color: #111; margin: 28px; }}
  h1 {{ font-size: 22px; margin: 0 0 6px; }}
  .meta {{ color: #444; font-size: 13px; margin-bottom: 18px; }}
  .grid {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px; margin: 14px 0 22px; }}
  .metric {{ border: 1px solid #ddd; padding: 10px; }}
  .metric b {{ display: block; font-size: 22px; }}
  table {{ width: 100%; border-collapse: collapse; margin: 8px 0 20px; font-size: 13px; }}
  th, td {{ border: 1px solid #ddd; padding: 6px 8px; text-align: left; }}
  th {{ background: #f4f4f4; }}
  @media print {{ body {{ margin: 12mm; }} a {{ color: inherit; text-decoration: none; }} }}
</style></head><body>
<h1>{esc(title)}</h1>
<p class="meta">Generado {esc(generated)} · rango {esc(days)}d{(' · perfil ' + esc(profile)) if profile else ''}</p>
<div class="grid">
  <div class="metric"><b>{esc(totals.get('scans'))}</b><span>Escaneos</span></div>
  <div class="metric"><b>{esc(totals.get('compliance_rate'))}%</b><span>Cumplimiento</span></div>
  <div class="metric"><b>{esc(totals.get('safety_score'))}</b><span>Safety Score</span></div>
  <div class="metric"><b>{esc(totals.get('non_compliant'))}</b><span>Incumplimientos</span></div>
</div>
<p class="meta">Penalizaciones: desconocidos -{esc(breakdown.get('penalty_unknown', 0))} · EPP crítico -{esc(breakdown.get('penalty_critical_missing', 0))}</p>
<h2>EPP faltante</h2>
<table><thead><tr><th>Ítem</th><th>Cantidad</th></tr></thead><tbody>{miss_rows}</tbody></table>
<h2>Ranking trabajadores</h2>
<table><thead><tr><th>Nombre</th><th>RUT</th><th>Score</th><th>Fallas</th></tr></thead><tbody>{rank_rows}</tbody></table>
<h2>Incumplimientos recientes</h2>
<table><thead><tr><th>Fecha</th><th>Persona</th><th>Detalle</th><th>Evidencia</th></tr></thead><tbody>{evid_rows}</tbody></table>
<p class="meta">Documento generado por VigiEPP · imprimir / Guardar como PDF desde el navegador.</p>
</body></html>"""

