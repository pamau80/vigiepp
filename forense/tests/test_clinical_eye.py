"""Tests ojo clínico — evaluación del instante."""

from __future__ import annotations

from forense.app.clinical_eye import clinical_progress_message, evaluate_instant_audit


def test_evaluate_idle_without_frame():
    out = evaluate_instant_audit(None)
    assert out["level"] == "idle"
    assert "Esperando" in out["headline"]


def test_evaluate_alert_on_proximity():
    frame = {
        "time_sec": 5.0,
        "time_label": "00:00:05",
        "counts": {"persons": 1, "vehicles": 1},
        "tracks": [
            {"track_id": 1, "kind": "person", "cx": 10, "cy": 10},
            {"track_id": 2, "kind": "machinery", "cx": 20, "cy": 20},
        ],
        "speeds": [{"track_id": 2, "speed_kmh": 12}],
        "proximity": [
            {
                "person_track": 1,
                "machinery_track": 2,
                "distance_m": 0.8,
                "alert": True,
            }
        ],
        "detections": [{"label": "person", "kind": "person", "confidence": 0.9, "box": [0, 0, 1, 1]}],
    }
    out = evaluate_instant_audit(frame, min_distance_m=2.0)
    assert out["level"] == "alert"
    assert "Proximidad crítica" in out["headline"]
    assert out["sections"]


def test_evaluate_warn_on_speed():
    frame = {
        "time_sec": 2.0,
        "time_label": "00:00:02",
        "counts": {"persons": 0, "vehicles": 1},
        "tracks": [{"track_id": 3, "kind": "machinery", "cx": 5, "cy": 5}],
        "speeds": [{"track_id": 3, "speed_kmh": 22}],
        "proximity": [],
        "detections": [],
    }
    out = evaluate_instant_audit(frame, max_machinery_kmh=15)
    assert out["level"] == "warn"
    assert "Exceso velocidad" in out["headline"]


def test_events_near_in_audit():
    frame = {
        "time_sec": 10.0,
        "time_label": "00:00:10",
        "counts": {"persons": 1, "vehicles": 0},
        "tracks": [],
        "speeds": [],
        "proximity": [],
        "detections": [],
    }
    timeline = [
        {"time_sec": 10.2, "type": "proximity", "message": "Persona cerca de máquina", "severity": "high"},
        {"time_sec": 20.0, "type": "speed_violation", "message": "Lejos", "severity": "medium"},
    ]
    out = evaluate_instant_audit(frame, timeline=timeline, time_sec=10.0)
    assert len(out["events_near"]) == 1
    titles = [s["title"] for s in out["sections"]]
    assert "Eventos en este instante" in titles


def test_clinical_progress_message():
    assert "revisión forense" in clinical_progress_message("En cola")
    assert "fotograma" in clinical_progress_message("Cám. 1: frame 3/10")
    assert "velocidades" in clinical_progress_message("Calculando cinemática y mapa de calor")
