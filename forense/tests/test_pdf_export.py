"""Tests exportación PDF forense."""

from __future__ import annotations

from pathlib import Path

from forense.app.pdf_export import export_report_pdf


def test_export_structured_pdf(tmp_path: Path):
    from forense.app.event_feedback import ensure_event_ids
    from forense.app.report_sections import build_report_sections

    job = {
        "id": "pdfjob01",
        "title": "PDF estructurado",
        "site": "Faena",
        "template_name": "General",
        "analysis": {
            "timeline": ensure_event_ids(
                [{"type": "epp", "time_sec": 1.0, "time_label": "00:01", "message": "Sin casco"}]
            ),
            "keyframes": [],
            "kinematics": {},
            "speed_series": [],
        },
        "comparison": {"available": False},
        "knowledge": {},
    }
    structured = build_report_sections(job)
    out = tmp_path / "structured.pdf"
    assert export_report_pdf({**job, "report_md": "# fallback"}, out) is True
    assert out.stat().st_size > 500


def test_export_report_pdf_long_lines(tmp_path: Path):
    long_word = "x" * 200
    job = {
        "title": "Caso con líneas largas",
        "report_md": (
            "# Titulo del informe\n\n"
            f"Linea con palabra enorme: {long_word}\n\n"
            "> Aviso legal extendido " + ("importante " * 40) + "\n"
            "## Seccion secundaria\n"
            "Contenido normal del analisis forense."
        ),
    }
    out = tmp_path / "report.pdf"
    assert export_report_pdf(job, out) is True
    assert out.stat().st_size > 500
