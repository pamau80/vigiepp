"""Cinemática: velocidades y proximidad persona–maquinaria."""

from __future__ import annotations

import math
from typing import Any

from .tracker import Track, TrackPoint


def _dist_m(p1: TrackPoint, p2: TrackPoint, mpp: float) -> float:
    dx = (p1.cx - p2.cx) * mpp
    dy = (p1.cy - p2.cy) * mpp
    return math.hypot(dx, dy)


def compute_track_speeds(
    tracks: list[Track],
    *,
    meters_per_pixel: float,
) -> list[dict[str, Any]]:
    """Velocidad máxima y promedio por track (km/h)."""
    out: list[dict[str, Any]] = []
    for tr in tracks:
        speeds: list[float] = []
        pts = tr.points
        for i in range(1, len(pts)):
            dt = pts[i].time_sec - pts[i - 1].time_sec
            if dt <= 0.05:
                continue
            dm = _dist_m(pts[i - 1], pts[i], meters_per_pixel)
            speeds.append((dm / dt) * 3.6)
        if not speeds:
            continue
        out.append(
            {
                "track_id": tr.track_id,
                "kind": tr.kind,
                "label": tr.label,
                "max_kmh": round(max(speeds), 2),
                "avg_kmh": round(sum(speeds) / len(speeds), 2),
                "samples": len(speeds),
            }
        )
    return sorted(out, key=lambda x: x["max_kmh"], reverse=True)


def find_speed_violations(
    track_speeds: list[dict[str, Any]],
    *,
    max_machinery_kmh: float,
    max_person_kmh: float,
) -> list[dict[str, Any]]:
    violations: list[dict[str, Any]] = []
    for ts in track_speeds:
        limit = max_machinery_kmh if ts["kind"] == "machinery" else max_person_kmh
        if ts["kind"] == "person" and ts["max_kmh"] > limit:
            violations.append(
                {
                    "track_id": ts["track_id"],
                    "kind": "person",
                    "label": ts["label"],
                    "max_kmh": ts["max_kmh"],
                    "limit_kmh": limit,
                    "message": f"Persona #{ts['track_id']}: velocidad estimada {ts['max_kmh']} km/h (límite {limit})",
                }
            )
        elif ts["kind"] == "machinery" and ts["max_kmh"] > limit:
            violations.append(
                {
                    "track_id": ts["track_id"],
                    "kind": "machinery",
                    "label": ts["label"],
                    "max_kmh": ts["max_kmh"],
                    "limit_kmh": limit,
                    "message": f"Maquinaria #{ts['track_id']}: velocidad estimada {ts['max_kmh']} km/h (límite {limit})",
                }
            )
    return violations


def find_proximity_events(
    tracks: list[Track],
    *,
    meters_per_pixel: float,
    min_distance_m: float,
    time_tolerance: float = 0.6,
) -> list[dict[str, Any]]:
    """Near-miss: persona y maquinaria más cerca que min_distance_m."""
    persons = [t for t in tracks if t.kind == "person"]
    machines = [t for t in tracks if t.kind == "machinery"]
    events: list[dict[str, Any]] = []
    for p in persons:
        for m in machines:
            best = None
            for pp in p.points:
                for mp in m.points:
                    if abs(pp.time_sec - mp.time_sec) > time_tolerance:
                        continue
                    d = _dist_m(pp, mp, meters_per_pixel)
                    if best is None or d < best[0]:
                        best = (d, pp.time_sec)
            if best and best[0] < min_distance_m:
                events.append(
                    {
                        "time_sec": best[1],
                        "distance_m": round(best[0], 2),
                        "person_track": p.track_id,
                        "machinery_track": m.track_id,
                        "message": (
                            f"Proximidad {best[0]:.1f} m entre Persona #{p.track_id} "
                            f"y Maquinaria #{m.track_id} (límite {min_distance_m} m)"
                        ),
                    }
                )
    return events
