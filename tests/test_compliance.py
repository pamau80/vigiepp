"""Tests reglas de cumplimiento EPP."""

from __future__ import annotations

from app.compliance import evaluate


def test_evaluate_empty_detections():
    result = evaluate([], "general")
    assert result.overall_compliant is True


def test_evaluate_person_missing_casco():
    dets = [
        {"label": "Person", "confidence": 0.9, "box": [10, 10, 200, 400]},
    ]
    result = evaluate(dets, "general", required_override=["casco"])
    assert result.overall_compliant is False
    assert result.persons[0].missing
