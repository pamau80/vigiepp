"""Tests exportación PDF forense."""

from __future__ import annotations

from pathlib import Path

from forense.app.pdf_export import export_report_pdf


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
