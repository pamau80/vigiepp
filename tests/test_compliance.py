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


def test_hardhat_label_counts_as_casco():
    dets = [{"label": "Hardhat", "confidence": 0.75, "box": [20, 20, 120, 120]}]
    result = evaluate(dets, "general", required_override=["casco"])
    assert "casco" in result.persons[0].present


def test_custom_trained_class_maps_to_ppe_family():
    dets = [{"label": "guantes_nitrilo_azul", "confidence": 0.8, "box": [10, 10, 90, 90]}]
    result = evaluate(dets, "epp_completo", required_override=["guantes"])
    assert "guantes" in result.persons[0].present
