"""Tests exportación EHS y bundle."""

from __future__ import annotations

import json
import zipfile
from pathlib import Path

from forense.app.export import build_ehs_incident, committee_section, export_case_bundle


def test_build_ehs_incident_includes_review_audit():
    from forense.app.event_feedback import ensure_event_ids

    timeline = ensure_event_ids([{"type": "epp", "time_sec": 1.0, "message": "Sin casco"}])
    eid = timeline[0]["event_id"]
    job = {
        "id": "abc123",
        "title": "Near miss",
        "site": "Bodega",
        "profile": "epp_completo",
        "build": "forense-p26",
        "analysis": {"event_count": 1, "timeline": timeline, "kinematics": {"speed_violations": [], "proximity_events": []}},
        "event_feedback": {
            eid: {
                "verdict": "dismissed",
                "note": "falso",
                "at": "2026-09-04T12:00:00+00:00",
                "reviewed_by": "admin",
                "type": "epp",
                "message": "Sin casco",
            }
        },
    }
    payload = build_ehs_incident(job)
    assert payload["forense"]["events_dismissed"] == 1
    assert payload["forense"]["review_audit"]


def test_build_ehs_incident():
    job = {
        "id": "abc123",
        "title": "Near miss",
        "site": "Bodega",
        "profile": "epp_completo",
        "build": "forense-p4",
        "analysis": {"event_count": 3, "kinematics": {"speed_violations": [{}], "proximity_events": []}},
    }
    payload = build_ehs_incident(job)
    assert payload["evidence_id"] == "abc123"
    assert payload["forense"]["violations"] == 1


def test_committee_section():
    job = {
        "title": "Caso",
        "site": "Faena",
        "updated_at": "2026-08-30T00:00:00Z",
        "analysis": {"event_count": 2, "kinematics": {"speed_violations": [], "proximity_events": []}},
        "comparison": {"available": False},
    }
    md = committee_section(job)
    assert "Comité Paritario" in md


def test_export_case_bundle(tmp_path: Path):
    job_dir = tmp_path / "job1"
    job_dir.mkdir()
    (job_dir / "job.json").write_text("{}", encoding="utf-8")
    (job_dir / "report.md").write_text("# test", encoding="utf-8")
    job = {
        "id": "job1",
        "title": "T",
        "site": "S",
        "analysis": {"event_count": 0, "kinematics": {}, "speed_series": [{"track_id": 1, "points": []}]},
    }
    out = job_dir / "case_bundle.zip"
    assert export_case_bundle(job, out) is True
    with zipfile.ZipFile(out) as zf:
        names = set(zf.namelist())
        data = json.loads(zf.read("ehs_incident.json"))
    assert "job.json" in names
    assert "ehs_incident.json" in names
    assert "speed_series.json" in names
    assert data["evidence_id"] == "job1"
