"""Análisis de conducta en faena: caídas, peleas probables y situaciones sospechosas.

Heurísticas sobre detecciones YOLO + zonas — no reemplaza supervisión humana.
Para precisión en agresión/conflictos se requiere modelo de pose/acción entrenado
con video real de la faena (fase posterior).
"""

from __future__ import annotations

import math
from typing import Any


def _person_boxes(detections: list[dict[str, Any]]) -> list[list[float]]:
    out: list[list[float]] = []
    for d in detections:
        lab = str(d.get("label") or "").lower()
        les = str(d.get("label_es") or "").lower()
        cat = str(d.get("category") or "").lower()
        if not d.get("box"):
            continue
        if "person" in lab or "persona" in les or cat == "persona":
            out.append([float(x) for x in d["box"]])
    return out


def _center(box: list[float]) -> tuple[float, float]:
    return (box[0] + box[2]) / 2, (box[1] + box[3]) / 2


def _iou(a: list[float], b: list[float]) -> float:
    ix1, iy1 = max(a[0], b[0]), max(a[1], b[1])
    ix2, iy2 = min(a[2], b[2]), min(a[3], b[3])
    inter = max(0.0, ix2 - ix1) * max(0.0, iy2 - iy1)
    if inter <= 0:
        return 0.0
    area_a = max(1.0, (a[2] - a[0]) * (a[3] - a[1]))
    area_b = max(1.0, (b[2] - b[0]) * (b[3] - b[1]))
    return inter / (area_a + area_b - inter)


def _dist(a: list[float], b: list[float]) -> float:
    ax, ay = _center(a)
    bx, by = _center(b)
    return math.hypot(ax - bx, ay - by)


def _fall_detected(detections: list[dict[str, Any]]) -> bool:
    for d in detections:
        cat = str(d.get("category") or "").lower()
        lab = str(d.get("label") or "").lower()
        if cat == "caida" or "fall" in lab:
            return float(d.get("confidence") or 0) >= 0.45
    return False


def evaluate_behavior(
    detections: list[dict[str, Any]],
    *,
    zone_hits: list[dict[str, Any]] | None = None,
    persons: list[dict[str, Any]] | None = None,
    frame_w: int = 0,
    frame_h: int = 0,
) -> dict[str, Any]:
    """Devuelve alertas de conducta y eventos estructurados para el ojo vigilia."""
    alerts: list[str] = []
    events: list[dict[str, Any]] = []
    severity = "ok"

    if _fall_detected(detections):
        alerts.append("Caída detectada — revisar de inmediato")
        events.append({"type": "caida", "severity": "critical", "detail": "Modelo reportó caída"})
        severity = "critical"

    boxes = _person_boxes(detections)
    if len(boxes) >= 2 and frame_w > 0 and frame_h > 0:
        scale = max(frame_w, frame_h) * 0.12
        for i in range(len(boxes)):
            for j in range(i + 1, len(boxes)):
                a, b = boxes[i], boxes[j]
                iou = _iou(a, b)
                dist = _dist(a, b)
                if iou >= 0.32:
                    alerts.append("Posible altercado: personas superpuestas")
                    events.append(
                        {
                            "type": "pelea_probable",
                            "severity": "high",
                            "detail": f"IoU={iou:.2f}",
                            "boxes": [a, b],
                        }
                    )
                    severity = "high" if severity != "critical" else severity
                elif dist < scale and iou >= 0.08:
                    alerts.append("Proximidad agresiva: personas muy cerca")
                    events.append(
                        {
                            "type": "proximidad_agresiva",
                            "severity": "medium",
                            "detail": f"dist={dist:.0f}px",
                            "boxes": [a, b],
                        }
                    )
                    if severity == "ok":
                        severity = "medium"

    # Zona restringida + EPP incompleto = merodeo / acceso indebido sospechoso
    restricted_hits = [h for h in (zone_hits or []) if h.get("zone_type") == "restricted"]
    if restricted_hits and persons:
        for p in persons:
            if not p.get("compliant"):
                miss = ", ".join(p.get("missing") or []) or "EPP"
                alerts.append(f"Merodeo sospechoso en zona restringida sin EPP ({miss})")
                events.append(
                    {
                        "type": "merodeo",
                        "severity": "high",
                        "detail": miss,
                        "person_id": p.get("person_id"),
                    }
                )
                if severity in ("ok", "medium"):
                    severity = "high"

    # Multitud en vía de vehículos (near-miss social)
    vehicle_hits = [h for h in (zone_hits or []) if h.get("zone_type") == "vehicle_lane"]
    if len(boxes) >= 3 and vehicle_hits:
        alerts.append("Aglomeración en vía de vehículos — riesgo de conflicto")
        events.append({"type": "aglomeracion", "severity": "medium", "detail": f"{len(boxes)} personas"})
        if severity == "ok":
            severity = "medium"

    seen: set[str] = set()
    uniq_alerts: list[str] = []
    for a in alerts:
        if a not in seen:
            seen.add(a)
            uniq_alerts.append(a)

    return {
        "alerts": uniq_alerts,
        "events": events,
        "severity": severity,
        "person_count": len(boxes),
    }
