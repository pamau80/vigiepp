"""Tracking ligero por IoU para análisis forense."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

PERSON_KW = ("person", "human", "persona", "worker")
MACHINERY_KW = ("forklift", "montacargas", "lift", "pallet", "crane", "grua", "grúa", "truck", "vehicle")


def _iou(a: list[float], b: list[float]) -> float:
    ax1, ay1, ax2, ay2 = a
    bx1, by1, bx2, by2 = b
    ix1, iy1 = max(ax1, bx1), max(ay1, by1)
    ix2, iy2 = min(ax2, bx2), min(ay2, by2)
    iw, ih = max(0.0, ix2 - ix1), max(0.0, iy2 - iy1)
    inter = iw * ih
    if inter <= 0:
        return 0.0
    area_a = max(0.0, ax2 - ax1) * max(0.0, ay2 - ay1)
    area_b = max(0.0, bx2 - bx1) * max(0.0, by2 - by1)
    union = area_a + area_b - inter
    return inter / union if union > 0 else 0.0


def _centroid(box: list[float]) -> tuple[float, float]:
    x1, y1, x2, y2 = box
    return ((x1 + x2) / 2.0, (y1 + y2) / 2.0)


def _classify(label: str) -> str:
    low = (label or "").lower()
    if any(k in low for k in MACHINERY_KW):
        return "machinery"
    if any(k in low for k in PERSON_KW):
        return "person"
    return "other"


@dataclass
class TrackPoint:
    time_sec: float
    cx: float
    cy: float
    label: str
    confidence: float


@dataclass
class Track:
    track_id: int
    kind: str
    label: str
    points: list[TrackPoint] = field(default_factory=list)

    def last_box_centroid(self) -> tuple[float, float] | None:
        if not self.points:
            return None
        p = self.points[-1]
        return (p.cx, p.cy)


class IoUTracker:
    def __init__(self, iou_threshold: float = 0.25, max_gap: int = 8) -> None:
        self.iou_threshold = iou_threshold
        self.max_gap = max_gap
        self._tracks: dict[int, Track] = {}
        self._next_id = 1
        self._missed: dict[int, int] = {}

    def update(self, time_sec: float, detections: list[dict[str, Any]]) -> list[Track]:
        assigned: set[int] = set()
        for det in detections:
            box = det.get("box")
            if not box or len(box) != 4:
                continue
            label = str(det.get("label_es") or det.get("label") or "")
            kind = _classify(label)
            if kind == "other":
                continue
            cx, cy = _centroid(box)
            conf = float(det.get("confidence") or 0)
            best_id, best_iou = None, 0.0
            for tid, track in self._tracks.items():
                if tid in assigned or track.kind != kind:
                    continue
                last = track.points[-1] if track.points else None
                if not last:
                    continue
                # Aproximar última caja con punto (IoU débil por tamaño fijo)
                pseudo = [last.cx - 20, last.cy - 40, last.cx + 20, last.cy + 40]
                score = _iou(box, pseudo)
                if score > best_iou:
                    best_iou, best_id = score, tid
            if best_id is not None and best_iou >= self.iou_threshold:
                tr = self._tracks[best_id]
                tr.points.append(TrackPoint(time_sec, cx, cy, label, conf))
                assigned.add(best_id)
                self._missed[best_id] = 0
            else:
                tid = self._next_id
                self._next_id += 1
                self._tracks[tid] = Track(tid, kind, label, [TrackPoint(time_sec, cx, cy, label, conf)])
                assigned.add(tid)
                self._missed[tid] = 0

        for tid in list(self._tracks.keys()):
            if tid not in assigned:
                self._missed[tid] = self._missed.get(tid, 0) + 1
                if self._missed[tid] > self.max_gap:
                    del self._tracks[tid]
                    self._missed.pop(tid, None)
        return list(self._tracks.values())

    def all_tracks(self) -> list[Track]:
        return list(self._tracks.values())
