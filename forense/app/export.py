"""Exportación EHS y comité paritario."""

from __future__ import annotations

import json
import zipfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


def build_ehs_incident(job: dict[str, Any]) -> dict[str, Any]:
    from .event_feedback import build_review_audit

    analysis = job.get("analysis") or {}
    kin = analysis.get("kinematics") or {}
    audit = build_review_audit(job)
    dismissed = sum(1 for e in audit if e.get("verdict") == "dismissed")
    confirmed = sum(1 for e in audit if e.get("verdict") == "confirmed")
    return {
        "ts": datetime.now(UTC).isoformat(),
        "site": job.get("site") or "",
        "summary": f"[Forense IA] {job.get('title') or 'Incidente'} — {analysis.get('event_count', 0)} eventos",
        "compliant": False,
        "missing": [],
        "worker_name": None,
        "worker_rut": None,
        "worker_id": None,
        "profile": job.get("profile"),
        "evidence_id": job.get("id"),
        "forense": {
            "job_id": job.get("id"),
            "build": job.get("build"),
            "violations": len(kin.get("speed_violations") or []) + len(kin.get("proximity_events") or []),
            "comparison": job.get("comparison"),
            "events_reviewed": len(audit),
            "events_confirmed": confirmed,
            "events_dismissed": dismissed,
            "review_audit": audit[:30],
        },
    }


def push_to_ehs(job: dict[str, Any]) -> list[dict[str, Any]]:
    """Reutiliza conectores EHS de VigiEPP (solo lectura)."""
    try:
        from app import ehs_connectors as ehs_mod

        return ehs_mod.push_incident(build_ehs_incident(job))
    except Exception as exc:  # noqa: BLE001
        return [{"ok": False, "error": str(exc)}]


def committee_section(job: dict[str, Any]) -> str:
    comp = job.get("comparison") or {}
    kin = (job.get("analysis") or {}).get("kinematics") or {}
    lines = [
        "## Informe Comité Paritario (borrador IA)",
        "",
        f"**Caso:** {job.get('title')}",
        f"**Faena:** {job.get('site')}",
        f"**Fecha análisis:** {job.get('updated_at', '')[:10]}",
        "",
        "### Hechos observables",
        f"- Eventos registrados en video: **{(job.get('analysis') or {}).get('event_count', 0)}**",
        f"- Violaciones cinemáticas: **{len(kin.get('speed_violations') or [])}**",
        f"- Eventos proximidad crítica: **{len(kin.get('proximity_events') or [])}**",
        "",
    ]
    if comp.get("available"):
        lines.extend(
            [
                "### Comparación vs escenario de referencia",
                f"- Referencia: {comp.get('reference_title')} (`{comp.get('reference_job_id')}`)",
                f"- {comp.get('summary')}",
                f"- Interpretación: {comp.get('interpretation')}",
                "",
            ]
        )
    audit = []
    try:
        from .event_feedback import build_review_audit

        audit = build_review_audit(job)
    except Exception:
        audit = []
    if audit:
        lines.extend(["### Revisiones del operador (auditoría)", ""])
        for entry in audit[:15]:
            verdict = entry.get("verdict") or ""
            when = (entry.get("reviewed_at") or "")[:10]
            lines.append(
                f"- {verdict}: {entry.get('time_label', '—')} — {(entry.get('message') or '')[:80]} "
                f"({entry.get('reviewed_by', 'admin')}, {when})"
            )
        lines.append("")
    lines.extend(
        [
            "### Medidas sugeridas (preventivas)",
            "- Revisar procedimiento de tránsito en sector del evento.",
            "- Reforzar capacitación en distanciamiento persona–maquinaria.",
            "- Verificar señalética y delimitación de zonas.",
            "",
            "> Borrador para comité paritario. Validar con prevencionista antes de presentar.",
            "",
        ]
    )
    return "\n".join(lines)


def export_case_bundle(job: dict[str, Any], out_path: Path) -> bool:
    job_dir = out_path.parent
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(out_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for name in ("job.json", "report.md", "report.pdf"):
            p = job_dir / name
            if p.is_file():
                zf.write(p, arcname=name)
        zf.writestr(
            "ehs_incident.json",
            json.dumps(build_ehs_incident(job), ensure_ascii=False, indent=2),
        )
        charts = (job.get("analysis") or {}).get("speed_series")
        if charts:
            zf.writestr("speed_series.json", json.dumps(charts, ensure_ascii=False, indent=2))
        from .event_feedback import build_review_audit

        audit = build_review_audit(job)
        if audit:
            zf.writestr("review_audit.json", json.dumps(audit, ensure_ascii=False, indent=2))
    return out_path.is_file()
