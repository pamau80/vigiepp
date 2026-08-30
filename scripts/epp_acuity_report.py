#!/usr/bin/env python3
"""Reporte de agudeza EPP: casco, ropa completa, lentes, guantes."""

from __future__ import annotations

import argparse
import sys
from datetime import UTC, datetime
from pathlib import Path

import cv2

ROOT = Path(__file__).resolve().parents[1]
PPE_DIR = ROOT / "tests" / "fixtures" / "ppe"
EPP_KEYS = ("casco", "chaleco", "lentes", "guantes")
EPP_LABELS = {
    "casco": "Casco",
    "chaleco": "Ropa completa (chaleco/flúor)",
    "lentes": "Lentes",
    "guantes": "Guantes",
}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=Path("/opt/cursor/artifacts/epp-acuity-report.md"))
    args = parser.parse_args()

    sys.path[:0] = [str(ROOT / "backend"), str(ROOT)]
    from app.compliance import _category_for_label, evaluate
    from app.detector import PPEDetector

    det = PPEDetector.get()
    if not det.ready:
        print(f"YOLO no listo: {det.error}", file=sys.stderr)
        return 1

    best = {k: 0.0 for k in EPP_KEYS}
    rows: list[str] = []

    for path in sorted(PPE_DIR.glob("*.*")):
        if path.suffix.lower() not in (".jpg", ".jpeg"):
            continue
        img = cv2.imread(str(path))
        if img is None:
            continue
        dets, _ = det.predict(img, conf=0.15, imgsz=640)
        comp = evaluate(dets, "epp_completo")
        present = set(comp.persons[0].present) if comp.persons else set()
        miss = set(comp.persons[0].missing) if comp.persons else set()
        item_cells = []
        for k in EPP_KEYS:
            conf = max(
                (float(d["confidence"]) for d in dets if _category_for_label(d.get("label", "")) == k),
                default=0.0,
            )
            best[k] = max(best[k], conf)
            mark = "✓" if k in present else ("✗" if k in miss else "·")
            pct = f"{conf * 100:.0f}%" if conf else "—"
            item_cells.append(f"{mark} {pct}")
        rows.append(f"| `{path.name}` | {' | '.join(item_cells)} | {'Cumple' if comp.overall_compliant else 'Falta EPP'} |")

    lines = [
        "# Agudeza EPP — casco, ropa, lentes, guantes",
        "",
        f"Generado: {datetime.now(UTC).isoformat()}",
        f"Perfil: **EPP completo faena** · modelo: {det.model_name}",
        "",
        "## Por imagen (conf ≥15%)",
        "",
        "| Imagen | Casco | Ropa | Lentes | Guantes | Resultado |",
        "|--------|------:|-----:|-------:|--------:|-----------|",
        *rows,
        "",
        "## Máximo por categoría (todas las fotos)",
        "",
        "| Ítem | Mejor confianza |",
        "|------|----------------:|",
    ]
    for k in EPP_KEYS:
        lines.append(f"| {EPP_LABELS[k]} | {best[k] * 100:.1f}% |")

    md = "\n".join(lines) + "\n"
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(md, encoding="utf-8")
    print(md)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
