"""Post-proceso de detecciones: umbrales por clase, NMS y conflictos +/-."""

from __future__ import annotations

from typing import Any, Iterable

import cv2
import numpy as np

PRECISION_MODES = ("alta", "equilibrada", "sensible")

# Piso de confianza por categoría (SafetyVision). Alta precisión sube los negativos
# para no inventar incumplimientos; casco/chaleco quedan un poco más bajos porque
# son objetos chicos y críticos.
CLASS_CONF_FLOOR: dict[str, float] = {
    "persona": 0.38,
    "casco": 0.28,
    "chaleco": 0.30,
    "lentes": 0.38,
    "guantes": 0.40,
    "mascarilla": 0.38,
    "arnes": 0.40,
    "zapatos": 0.42,
    "buzo": 0.38,
    "casaca": 0.36,
    "pantalon": 0.38,
    "reflectante": 0.40,
    "vestimenta": 0.36,
    "sin_casco": 0.50,
    "sin_chaleco": 0.50,
    "sin_lentes": 0.52,
    "sin_guantes": 0.52,
    "sin_arnes": 0.50,
    "sin_mascarilla": 0.52,
    "caida": 0.55,
}

PRECISION_SHIFT: dict[str, float] = {
    "alta": 0.08,
    "equilibrada": 0.0,
    "sensible": -0.07,
}

POS_NEG_PAIRS: tuple[tuple[str, str], ...] = (
    ("casco", "sin_casco"),
    ("chaleco", "sin_chaleco"),
    ("lentes", "sin_lentes"),
    ("guantes", "sin_guantes"),
    ("arnes", "sin_arnes"),
    ("mascarilla", "sin_mascarilla"),
)


def normalize_precision(raw: str | None) -> str:
    key = (raw or "").strip().lower()
    if key in ("alta", "high", "strict", "precision"):
        return "alta"
    if key in ("sensible", "recall", "low"):
        return "sensible"
    return "equilibrada"


def enhance_bgr(frame: np.ndarray) -> np.ndarray:
    """CLAHE suave: webcam de portería / luz irregular sin quemar el color."""
    if frame is None or frame.size == 0:
        return frame
    lab = cv2.cvtColor(frame, cv2.COLOR_BGR2LAB)
    luminance, a_ch, b_ch = cv2.split(lab)
    clahe = cv2.createCLAHE(clipLimit=1.8, tileGridSize=(8, 8))
    merged = cv2.merge((clahe.apply(luminance), a_ch, b_ch))
    return cv2.cvtColor(merged, cv2.COLOR_LAB2BGR)


def _iou(a: list[float], b: list[float]) -> float:
    ax1, ay1, ax2, ay2 = a
    bx1, by1, bx2, by2 = b
    ix1, iy1 = max(ax1, bx1), max(ay1, by1)
    ix2, iy2 = min(ax2, bx2), min(ay2, by2)
    inter = max(0.0, ix2 - ix1) * max(0.0, iy2 - iy1)
    if inter <= 0:
        return 0.0
    area_a = max(0.0, ax2 - ax1) * max(0.0, ay2 - ay1)
    area_b = max(0.0, bx2 - bx1) * max(0.0, by2 - by1)
    union = area_a + area_b - inter
    return inter / union if union > 0 else 0.0


def _area_frac(box: list[float], fw: float, fh: float) -> float:
    x1, y1, x2, y2 = box
    return max(0.0, x2 - x1) * max(0.0, y2 - y1) / max(1.0, fw * fh)


def _nms(dets: list[dict[str, Any]], iou_thr: float = 0.45) -> list[dict[str, Any]]:
    ordered = sorted(dets, key=lambda d: float(d.get("confidence") or 0), reverse=True)
    kept: list[dict[str, Any]] = []
    for det in ordered:
        if any(_iou(det["box"], k["box"]) >= iou_thr for k in kept):
            continue
        kept.append(det)
    return kept


def refine_detections(
    dets: Iterable[dict[str, Any]],
    frame_w: float,
    frame_h: float,
    precision: str = "equilibrada",
) -> list[dict[str, Any]]:
    """Filtra falsos positivos chicos, aplica piso por clase y NMS por categoría."""
    mode = normalize_precision(precision)
    shift = PRECISION_SHIFT[mode]
    fw = max(1.0, float(frame_w))
    fh = max(1.0, float(frame_h))
    by_cat: dict[str, list[dict[str, Any]]] = {}
    for raw in dets:
        det = dict(raw)
        cat = str(det.get("category") or "")
        conf = float(det.get("confidence") or 0)
        box = [float(x) for x in det["box"]]
        det["box"] = box
        floor = max(0.18, CLASS_CONF_FLOOR.get(cat, 0.35) + shift)
        if conf < floor:
            continue
        frac = _area_frac(box, fw, fh)
        tiny_ok = {"casco", "lentes", "mascarilla"}
        min_frac = 0.0012 if cat in tiny_ok else 0.0035
        if cat.startswith("sin_") or cat == "caida":
            min_frac = 0.0025
        if cat == "persona":
            min_frac = 0.012
        if frac < min_frac:
            continue
        if frac > 0.88 and cat != "persona":
            continue
        by_cat.setdefault(cat, []).append(det)

    out: list[dict[str, Any]] = []
    for cat, group in by_cat.items():
        out.extend(_nms(group, 0.48))
    return resolve_pos_neg_conflicts(out)


def resolve_pos_neg_conflicts(dets: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Si casco y SIN casco se pisan, gana el de mayor confianza (desempate: positivo)."""
    drop: set[int] = set()
    indexed = list(enumerate(dets))
    for pos_cat, neg_cat in POS_NEG_PAIRS:
        positives = [(i, d) for i, d in indexed if d.get("category") == pos_cat]
        negatives = [(i, d) for i, d in indexed if d.get("category") == neg_cat]
        for pi, pd in positives:
            for ni, nd in negatives:
                if pi in drop or ni in drop:
                    continue
                if _iou(pd["box"], nd["box"]) < 0.12:
                    continue
                pconf = float(pd.get("confidence") or 0)
                nconf = float(nd.get("confidence") or 0)
                if pconf + 0.04 >= nconf:
                    drop.add(ni)
                else:
                    drop.add(pi)
    return [d for i, d in indexed if i not in drop]
