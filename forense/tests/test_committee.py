"""Tests informe CPHS enriquecido."""

from __future__ import annotations

from forense.app.committee import committee_section


def test_committee_section_cphs_enriched():
    job = {
        "title": "Near miss pala",
        "site": "Faena Norte",
        "template_id": "mineria",
        "template_name": "Minería / faena",
        "updated_at": "2026-08-30T00:00:00Z",
        "build": "forense-p12",
        "llm_status": "offline",
        "analysis": {
            "event_count": 5,
            "frames_analyzed": 120,
            "sources_count": 2,
            "timeline": [
                {"type": "proximity", "severity": "high"},
                {"type": "epp_non_compliant", "severity": "medium"},
            ],
            "kinematics": {
                "speed_violations": [{"message": "Exceso camión"}],
                "proximity_events": [{"message": "Proximidad crítica"}],
            },
        },
        "knowledge": {
            "matches": [
                {
                    "title": "Retroceso sin spotter",
                    "situation_label": "Proximidad",
                    "confidence_pct": 72,
                    "description": "Patrón frecuente en faena.",
                }
            ]
        },
        "comparison": {"available": False},
    }
    md = committee_section(job)
    assert "CPHS en terreno" in md
    assert "DS N° 54/69" in md
    assert "Plan de seguimiento CPHS" in md
    assert "Retroceso sin spotter" in md
    assert "segregación peatón" in md
    assert "sin API LLM" in md


def test_committee_section_construccion_industry():
    job = {
        "title": "Andamio",
        "site": "Obra",
        "template_id": "construccion",
        "template_name": "Construcción",
        "updated_at": "2026-01-01T00:00:00Z",
        "analysis": {
            "event_count": 1,
            "timeline": [{"type": "zone"}],
            "kinematics": {},
        },
        "knowledge": {"matches": []},
        "comparison": {"available": False},
    }
    md = committee_section(job)
    assert "andamios" in md.lower() or "Andamio" in md
