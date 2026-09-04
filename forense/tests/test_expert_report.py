"""Tests informe experto y evidencia en timeline."""

from __future__ import annotations

from forense.app.expert_report import section_barrier_analysis, section_expert_recommendations, section_observed_facts
from forense.app.timeline_evidence import critical_alerts_summary, enrich_timeline_evidence
from forense.app.vision_timeline import events_from_vision_parsed


def test_enrich_timeline_links_keyframe():
    timeline = [{"time_sec": 10.0, "time_label": "00:00:10", "type": "proximity", "message": "cerca"}]
    kf = [{"time_sec": 10.2, "time_label": "00:00:10", "image": "kf_001.jpg"}]
    out = enrich_timeline_evidence(timeline, kf)
    assert out[0].get("evidence_image") == "kf_001.jpg"


def test_critical_alerts_all_types():
    timeline = [
        {"type": "proximity", "severity": "high", "time_sec": 1, "time_label": "00:00:01", "message": "cerca"},
        {"type": "epp_non_compliant", "severity": "high", "time_sec": 2, "time_label": "00:00:02", "message": "sin epp"},
        {"type": "fire", "severity": "critical", "time_sec": 3, "time_label": "00:00:03", "message": "llamas"},
    ]
    alerts = critical_alerts_summary(timeline)
    types = {a["type"] for a in alerts}
    assert "proximity" in types
    assert "epp_non_compliant" in types
    assert "fire" in types


def test_barrier_section_proximity_and_epp():
    timeline = [{"type": "proximity"}, {"type": "epp_non_compliant"}]
    md = section_barrier_analysis(timeline, {})
    assert "Segregación" in md
    assert "EPP" in md


def test_recommendations_multi_type():
    timeline = [{"type": "speed_violation"}, {"type": "zone"}]
    md = section_expert_recommendations(timeline, {})
    assert "velocidad" in md.lower() or "zonas" in md.lower()


def test_vision_general_schema():
    parsed = {
        "epp_y_ropa": "Trabajador sin casco",
        "maquinaria_proximidad": "Retroceso sin guía",
        "energia_fuego_humo": "no observable",
    }
    events = events_from_vision_parsed(parsed, frames_used=[{"time_sec": 1.0, "time_label": "00:00:01"}])
    types = {e["type"] for e in events}
    assert "epp_non_compliant" in types
    assert "proximity" in types
    assert "fire" not in types
