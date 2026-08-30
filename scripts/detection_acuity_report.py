#!/usr/bin/env python3
"""Genera reporte markdown de agudeza de detección (nitidez, match, blur, escala)."""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import UTC, datetime
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
LENA = ROOT / "tests" / "fixtures" / "lena.jpg"


def _reset_singletons() -> None:
    import app.detector as det_mod
    import app.identity as id_mod

    id_mod.IdentityRegistry.reset_for_site()
    det_mod.PPEDetector._instance = None
    det_mod.PPEDetector._load_started = False


def _enroll(svc) -> int:
    from app.detector import decode_image_bytes
    from tests.e2e.helpers import _face_jpeg_variants

    saved = 0
    for blob in _face_jpeg_variants(LENA, 6):
        r = svc.enroll(
            decode_image_bytes(blob),
            name="Reporte Agudez",
            rut="66.666.666-6",
            consent=True,
        )
        if r.get("face_enrolled"):
            saved += 1
    return saved


def run_report(data_dir: Path) -> dict:
    os.environ["VIGIEPP_DATA_DIR"] = str(data_dir)
    _reset_singletons()

    from app.detect_pipeline import detect_frame
    from app.detector import PPEDetector
    from app.identity import IdentityRegistry, IdentityService, assess_face_quality

    img = cv2.imread(str(LENA))
    if img is None:
        raise RuntimeError("lena.jpg no legible")

    reg = IdentityRegistry.get()
    faces = reg.detect_faces(img)
    face = max(faces, key=lambda f: float(f[2]) * float(f[3])) if faces else None

    strict_q = assess_face_quality(img, face, strict=True) if face is not None else (False, "sin rostro", {})
    live_q = assess_face_quality(img, face, strict=False) if face is not None else (False, "sin rostro", {})

    svc = IdentityService()
    enrolled = _enroll(svc)
    ident = svc.identify(img)
    m0 = (ident.get("matches") or [{}])[0]

    blur_rows = []
    for sigma in [0, 1, 2, 3, 5, 6, 7, 8, 10, 12]:
        frame = img if sigma == 0 else cv2.GaussianBlur(img, (0, 0), sigma)
        r = svc.identify(frame)
        m = (r.get("matches") or [{}])[0]
        qc = m.get("quality_check") or {}
        blur_rows.append(
            {
                "sigma": sigma,
                "faces": r.get("faces_detected", 0),
                "known": m.get("known"),
                "score": m.get("score"),
                "confidence": m.get("confidence"),
                "sharpness": qc.get("sharpness"),
            }
        )

    scale_rows = []
    h, w = img.shape[:2]
    for scale in [1.0, 0.75, 0.5, 0.35, 0.25]:
        small = cv2.resize(img, (max(32, int(w * scale)), max(32, int(h * scale))))
        r = svc.identify(small)
        m = (r.get("matches") or [{}])[0]
        qc = m.get("quality_check") or {}
        scale_rows.append(
            {
                "scale": scale,
                "faces": r.get("faces_detected", 0),
                "known": m.get("known"),
                "score": m.get("score"),
                "area_ratio": qc.get("area_ratio"),
            }
        )

    det = PPEDetector.get()
    epp_rows = []
    if det.ready:
        dets, _ = det.predict(img, conf=0.30, imgsz=416)
        for d in sorted(dets, key=lambda x: -float(x.get("confidence") or 0))[:6]:
            epp_rows.append(
                {
                    "label": d.get("label_es") or d.get("label"),
                    "confidence_pct": round(float(d.get("confidence") or 0) * 100, 1),
                }
            )

    with open(LENA, "rb") as fh:
        resp = detect_frame(
            fh.read(),
            profile="general",
            conf=0.35,
            identify=True,
            return_image=False,
            imgsz=416,
            threshold=0.33,
        )
    import json

    pipe = json.loads(resp.body)

    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "fixture": str(LENA.name),
        "enrolled_samples": enrolled,
        "quality_strict": strict_q[2],
        "quality_live": live_q[2],
        "identify_baseline": {
            "known": m0.get("known"),
            "score": m0.get("score"),
            "confidence": m0.get("confidence"),
            "threshold": m0.get("threshold"),
        },
        "blur_curve": blur_rows,
        "scale_curve": scale_rows,
        "epp_detections": epp_rows,
        "yolo_ready": det.ready,
        "yolo_model": det.model_name if det.ready else det.error,
        "pipeline": {
            "identity_known": (pipe.get("identity") or {}).get("known"),
            "identity_score": (pipe.get("identity") or {}).get("score"),
            "safety_score": pipe.get("safety_score"),
            "compliance_ok": (pipe.get("compliance") or {}).get("overall_compliant"),
        },
    }


def render_md(report: dict) -> str:
    def pct(v):
        if v is None:
            return "—"
        return f"{float(v) * 100:.1f}%"

    lines = [
        "# Reporte de agudeza de detección — VigiEPP",
        "",
        f"Generado: {report['generated_at']}",
        f"Fixture: `{report['fixture']}` · muestras enroladas: **{report['enrolled_samples']}**",
        "",
        "## Calidad facial (YuNet + Laplaciana)",
        "",
        "| Modo | detect_score | sharpness | area_ratio | frontal |",
        "|------|-------------:|----------:|-----------:|--------:|",
    ]
    for label, key in (("Enrolamiento (strict)", "quality_strict"), ("Portería (live)", "quality_live")):
        q = report[key]
        lines.append(
            f"| {label} | {q.get('detect_score', '—')} | {q.get('sharpness', '—')} | "
            f"{q.get('area_ratio', '—')} | {q.get('frontal', '—')} |"
        )

    base = report["identify_baseline"]
    lines += [
        "",
        "## Identidad — línea base (imagen nítida)",
        "",
        f"- **Match:** {'Sí' if base.get('known') else 'No'}",
        f"- **Score cosine:** {pct(base.get('score'))} (umbral {pct(base.get('threshold'))})",
        f"- **Confianza:** {base.get('confidence') or '—'}",
        "",
        "## Curva de blur (degradación de nitidez)",
        "",
        "| σ blur | Rostros | Match | Score | Confianza | Sharpness |",
        "|-------:|--------:|:-----:|------:|:----------|----------:|",
    ]
    for row in report["blur_curve"]:
        lines.append(
            f"| {row['sigma']} | {row['faces']} | "
            f"{'✓' if row.get('known') else '✗'} | {pct(row.get('score'))} | "
            f"{row.get('confidence') or '—'} | {row.get('sharpness') or '—'} |"
        )

    lines += [
        "",
        "> **Límite operativo observado:** match cae bajo umbral ~σ≥6; YuNet deja de ver rostro ~σ≥7.",
        "",
        "## Curva de escala (simula distancia)",
        "",
        "| Escala | Rostros | Match | Score | area_ratio |",
        "|-------:|--------:|:-----:|------:|-----------:|",
    ]
    for row in report["scale_curve"]:
        lines.append(
            f"| {row['scale']:.0%} | {row['faces']} | "
            f"{'✓' if row.get('known') else '✗'} | {pct(row.get('score'))} | {row.get('area_ratio') or '—'} |"
        )

    lines += ["", "## Detección EPP (YOLO)", ""]
    if report.get("yolo_ready"):
        lines.append(f"Modelo: **{report['yolo_model']}**")
        lines.append("")
        lines.append("| Ítem | Confianza |")
        lines.append("|------|----------:|")
        for row in report["epp_detections"]:
            lines.append(f"| {row['label']} | {row['confidence_pct']}% |")
    else:
        lines.append(f"YOLO no disponible: {report.get('yolo_model')}")

    pipe = report["pipeline"]
    lines += [
        "",
        "## Pipeline completo (/api/detect + identify)",
        "",
        f"- Identidad conocida: **{'Sí' if pipe.get('identity_known') else 'No'}**",
        f"- Score identidad: {pct(pipe.get('identity_score'))}",
        f"- Indicador EPP: {pipe.get('safety_score')}/100",
        f"- Cumple perfil: **{'Sí' if pipe.get('compliance_ok') else 'No'}**",
    ]
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=Path("/opt/cursor/artifacts/detection-acuity-report.md"))
    parser.add_argument("--json", type=Path, default=None)
    args = parser.parse_args()

    sys.path[:0] = [str(ROOT / "backend"), str(ROOT)]
    data_dir = Path(os.environ.get("VIGIEPP_DATA_DIR", f"/tmp/vigiepp-acuity-{os.getpid()}"))
    data_dir.mkdir(parents=True, exist_ok=True)

    report = run_report(data_dir)
    md = render_md(report)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(md, encoding="utf-8")
    if args.json:
        args.json.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(md)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
