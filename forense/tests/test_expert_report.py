"""Tests informe experto y evidencia en timeline."""

from __future__ import annotations

from forense.app.expert_report import section_barrier_analysis, section_observed_facts
from forense.app.timeline_evidence import critical_alerts_summary, enrich_timeline_evidence


def test_enrich_timeline_links_keyframe():
    timeline = [{"time_sec": 10.0, "time_label": "00:00:10", "type": "fire", "message": "fuego"}]
    kf = [{"time_sec": 10.2, "time_label": "00:00:10", "image": "kf_001.jpg"}]
    out = enrich_timeline_evidence(timeline, kf)
    assert out[0].get("evidence_image") == "kf_001.jpg"


def test_critical_alerts_groups_by_type():
    timeline = [
        {"type": "fire", "severity": "critical", "time_sec": 1, "time_label": "00:00:01", "message": "llamas"},
        {"type": "fire", "severity": "critical", "time_sec": 5, "time_label": "00:00:05", "message": "más llamas"},
        {"type": "epp_reflective", "severity": "high", "time_sec": 2, "time_label": "00:00:02", "message": "sin chaleco"},
    ]
    alerts = critical_alerts_summary(timeline)
    assert len(alerts) == 2
    assert alerts[0]["type"] == "fire"


def test_barrier_section_for_fire():
    timeline = [{"type": "fire"}, {"type": "epp_reflective"}]
    md = section_barrier_analysis(timeline, {})
    assert "emergencia" in md.lower()
    assert "EPP" in md


def test_observed_facts_table():
    timeline = [
        {
            "time_sec": 1,
            "time_label": "00:00:01",
            "type": "fire",
            "severity": "critical",
            "message": "Llamas visibles",
            "source": "scene_cv",
            "evidence_image": "kf_000.jpg",
        }
    ]
    md = section_observed_facts(timeline)
    assert "Llamas visibles" in md
    assert "kf_000.jpg" in md
