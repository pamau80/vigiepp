"""Series temporales de velocidad para gráficos."""

from __future__ import annotations

import math
from typing import Any

from .tracker import Track


def build_speed_series(tracks: list[Track], *, meters_per_pixel: float) -> list[dict[str, Any]]:
    series: list[dict[str, Any]] = []
    for tr in tracks:
        points: list[dict[str, Any]] = []
        pts = tr.points
        for i in range(1, len(pts)):
            dt = pts[i].time_sec - pts[i - 1].time_sec
            if dt <= 0.05:
                continue
            dx = (pts[i].cx - pts[i - 1].cx) * meters_per_pixel
            dy = (pts[i].cy - pts[i - 1].cy) * meters_per_pixel
            kmh = (math.hypot(dx, dy) / dt) * 3.6
            points.append({"t": round(pts[i].time_sec, 2), "kmh": round(kmh, 2)})
        if points:
            series.append(
                {
                    "track_id": tr.track_id,
                    "kind": tr.kind,
                    "label": tr.label,
                    "points": points,
                    "max_kmh": max(p["kmh"] for p in points),
                }
            )
    return series


def tracks_to_json(tracks: list[Track]) -> list[dict[str, Any]]:
    return [
        {
            "track_id": t.track_id,
            "kind": t.kind,
            "label": t.label,
            "points": [{"t": p.time_sec, "cx": p.cx, "cy": p.cy} for p in t.points],
        }
        for t in tracks
    ]
