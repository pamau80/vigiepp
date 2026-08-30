"""Exportación PDF del informe forense."""

from __future__ import annotations

from pathlib import Path
from typing import Any


def export_report_pdf(job: dict[str, Any], out_path: Path) -> bool:
    try:
        from fpdf import FPDF
    except ImportError:
        return _export_minimal_pdf(job, out_path)

    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 10, "VigiEPP Forense - Informe IA", ln=True)
    pdf.set_font("Helvetica", "", 10)
    pdf.multi_cell(0, 6, _plain_text(job.get("title") or "Caso"))
    pdf.ln(4)
    pdf.set_font("Helvetica", "I", 9)
    pdf.multi_cell(
        0,
        5,
        "Informe generado por IA. No constituye peritaje legal. Requiere validacion humana.",
    )
    pdf.ln(6)
    pdf.set_font("Helvetica", "", 10)
    body = job.get("report_md") or ""
    for line in body.splitlines():
        line = _plain_text(line)
        if line.startswith("# "):
            pdf.ln(4)
            pdf.set_font("Helvetica", "B", 12)
            pdf.multi_cell(0, 6, line[2:])
            pdf.set_font("Helvetica", "", 10)
        elif line.startswith("## "):
            pdf.ln(3)
            pdf.set_font("Helvetica", "B", 11)
            pdf.multi_cell(0, 6, line[3:])
            pdf.set_font("Helvetica", "", 10)
        elif line.startswith(">"):
            pdf.set_font("Helvetica", "I", 9)
            pdf.multi_cell(0, 5, line.lstrip("> ").strip())
            pdf.set_font("Helvetica", "", 10)
        elif line.strip():
            pdf.multi_cell(0, 5, line)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    pdf.output(str(out_path))
    return out_path.is_file()


def _export_minimal_pdf(job: dict[str, Any], out_path: Path) -> bool:
    """Fallback sin fpdf2: PDF mínimo con texto plano embebido."""
    text = _plain_text(job.get("report_md") or "Sin contenido")
    lines = text.splitlines()[:120]
    content = "\\n".join(lines)
    stream = f"BT /F1 10 Tf 50 750 Td ({content[:3000]}) Tj ET"
    pdf_bytes = (
        b"%PDF-1.4\n1 0 obj<< /Type /Catalog /Pages 2 0 R>>endobj\n"
        b"2 0 obj<< /Type /Pages /Kids [3 0 R] /Count 1>>endobj\n"
        b"3 0 obj<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
        b"/Contents 4 0 R /Resources<< /Font<< /F1 5 0 R>>>>>>endobj\n"
        b"4 0 obj<< /Length " + str(len(stream)).encode() + b" >>stream\n" + stream.encode("latin-1", "replace")
        + b"\nendstream endobj\n"
        b"5 0 obj<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica>>endobj\n"
        b"xref\n0 6\n0000000000 65535 f \n"
        b"trailer<< /Size 6 /Root 1 0 R>>\nstartxref\n0\n%%EOF"
    )
    out_path.write_bytes(pdf_bytes)
    return True


def _plain_text(s: str) -> str:
    return (
        s.replace("**", "")
        .replace("*", "")
        .replace("`", "")
        .replace("|", " ")
        .encode("latin-1", "replace")
        .decode("latin-1")
    )
