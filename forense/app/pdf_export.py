"""Exportación PDF del informe forense."""

from __future__ import annotations

from pathlib import Path
from typing import Any


def export_report_pdf(job: dict[str, Any], out_path: Path) -> bool:
    try:
        from .report_sections import build_report_sections

        structured = build_report_sections(job)
        if structured.get("sections"):
            return _export_structured_pdf(structured, out_path)
    except Exception:
        pass
    return _export_markdown_pdf(job, out_path)


def _export_structured_pdf(report: dict[str, Any], out_path: Path) -> bool:
    try:
        from fpdf import FPDF
    except ImportError:
        job = {"title": report.get("title"), "report_md": _structured_to_text(report)}
        return _export_markdown_pdf(job, out_path)

    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.set_margins(15, 15, 15)
    pdf.add_page()
    w = pdf.w - pdf.l_margin - pdf.r_margin

    pdf.set_font("Helvetica", "B", 16)
    pdf.multi_cell(w, 10, _plain_text(f"VigiEPP Forense — {report.get('title') or 'Caso'}"))
    pdf.set_font("Helvetica", "", 10)
    pdf.multi_cell(w, 5, _plain_text(f"{report.get('site') or ''} · {report.get('generated_at') or ''}"))
    pdf.ln(3)
    pdf.set_font("Helvetica", "I", 9)
    pdf.multi_cell(w, 5, _plain_text(report.get("disclaimer") or ""))
    pdf.ln(6)

    for section in report.get("sections") or []:
        pdf.set_font("Helvetica", "B", 11)
        pdf.multi_cell(w, 6, _plain_text(section.get("title") or ""))
        pdf.set_font("Helvetica", "", 9)
        if section.get("note"):
            pdf.set_font("Helvetica", "I", 8)
            pdf.multi_cell(w, 5, _plain_text(section["note"]))
            pdf.set_font("Helvetica", "", 9)
        for line in (section.get("content_md") or "").splitlines():
            line = _plain_text(line.replace("**", "").replace("`", "").replace("|", " "))
            if not line.strip():
                pdf.ln(2)
                continue
            if line.startswith("### "):
                pdf.set_font("Helvetica", "B", 10)
                pdf.multi_cell(w, 5, _wrap_line(line[4:], 95))
                pdf.set_font("Helvetica", "", 9)
            elif line.startswith("## "):
                pdf.set_font("Helvetica", "B", 10)
                pdf.multi_cell(w, 5, _wrap_line(line[3:], 95))
                pdf.set_font("Helvetica", "", 9)
            else:
                pdf.multi_cell(w, 5, _wrap_line(line, 110))
        pdf.ln(4)

    audit = report.get("review_audit") or []
    if audit:
        pdf.add_page()
        pdf.set_font("Helvetica", "B", 12)
        pdf.multi_cell(w, 7, "Auditoria de revisiones del operador")
        pdf.ln(3)
        pdf.set_font("Helvetica", "", 9)
        for entry in audit[:40]:
            verdict = entry.get("verdict") or ""
            when = (entry.get("reviewed_at") or "")[:16].replace("T", " ")
            line = (
                f"{verdict} · {entry.get('time_label') or '—'} · "
                f"{entry.get('message') or ''} · {entry.get('reviewed_by') or 'admin'} · {when}"
            )
            if entry.get("note"):
                line += f" — {entry['note']}"
            pdf.multi_cell(w, 5, _wrap_line(_plain_text(line), 110))

    out_path.parent.mkdir(parents=True, exist_ok=True)
    pdf.output(str(out_path))
    return out_path.is_file()


def _structured_to_text(report: dict[str, Any]) -> str:
    lines = [f"# {report.get('title')}", ""]
    for section in report.get("sections") or []:
        lines.append(f"## {section.get('title')}")
        lines.append(section.get("content_md") or "")
        lines.append("")
    return "\n".join(lines)


def _export_markdown_pdf(job: dict[str, Any], out_path: Path) -> bool:
    try:
        from fpdf import FPDF
    except ImportError:
        return _export_minimal_pdf(job, out_path)

    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.set_margins(15, 15, 15)
    pdf.add_page()
    effective_w = pdf.w - pdf.l_margin - pdf.r_margin
    pdf.set_font("Helvetica", "B", 16)
    pdf.multi_cell(effective_w, 10, _plain_text("VigiEPP Forense - Informe IA"))
    pdf.set_font("Helvetica", "", 10)
    pdf.multi_cell(effective_w, 6, _plain_text(job.get("title") or "Caso"))
    pdf.ln(4)
    pdf.set_font("Helvetica", "I", 9)
    pdf.multi_cell(
        effective_w,
        5,
        "Informe generado por IA. No constituye peritaje legal. Requiere validacion humana.",
    )
    pdf.ln(6)
    pdf.set_font("Helvetica", "", 10)
    body = job.get("report_md") or ""
    for line in body.splitlines():
        line = _plain_text(line)
        if not line.strip():
            pdf.ln(2)
            continue
        if line.startswith("# "):
            pdf.ln(4)
            pdf.set_font("Helvetica", "B", 12)
            pdf.multi_cell(effective_w, 6, _wrap_line(line[2:], 80))
            pdf.set_font("Helvetica", "", 10)
        elif line.startswith("## "):
            pdf.ln(3)
            pdf.set_font("Helvetica", "B", 11)
            pdf.multi_cell(effective_w, 6, _wrap_line(line[3:], 90))
            pdf.set_font("Helvetica", "", 10)
        elif line.startswith(">"):
            pdf.set_font("Helvetica", "I", 9)
            pdf.multi_cell(effective_w, 5, _wrap_line(line.lstrip("> ").strip(), 100))
            pdf.set_font("Helvetica", "", 10)
        else:
            pdf.multi_cell(effective_w, 5, _wrap_line(line, 110))
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


def _wrap_line(text: str, width: int) -> str:
    """Parte líneas largas para evitar fallos de FPDF con palabras enormes."""
    text = text.strip()
    if len(text) <= width:
        return text
    parts: list[str] = []
    while text:
        if len(text) <= width:
            parts.append(text)
            break
        cut = text.rfind(" ", 0, width)
        if cut <= 0:
            cut = width
        parts.append(text[:cut].strip())
        text = text[cut:].strip()
    return "\n".join(parts)
