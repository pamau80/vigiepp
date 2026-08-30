"""Tests comparación incidente vs referencia."""

from __future__ import annotations

from forense.app.comparison import compare_jobs


def test_compare_jobs_with_reference():
    incident = {
        "id": "inc1",
        "analysis": {
            "event_count": 5,
            "kinematics": {
                "track_speeds": [{"max_kmh": 20}],
                "speed_violations": [{"message": "x"}],
                "proximity_events": [],
            },
        },
    }
    reference = {
        "id": "ref1",
        "title": "Escenario seguro",
        "analysis": {
            "event_count": 2,
            "kinematics": {
                "track_speeds": [{"max_kmh": 10}],
                "speed_violations": [],
                "proximity_events": [],
            },
        },
    }
    comp = compare_jobs(incident, reference)
    assert comp["available"] is True
    assert comp["delta_events"] == 3
    assert comp["delta_violations"] == 1
    assert comp["risk_delta_score"] > 0


def test_compare_jobs_no_reference():
    assert compare_jobs({"analysis": {}}, None)["available"] is False
