"""Tests informe estructurado, matching IA y refocus multi-cámara."""

from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

from forense.app.event_feedback import ensure_event_ids, match_events_for_query
from forense.app.jobs import dismiss_matching_events, refocus_job, review_event
from forense.app.main import app
from forense.app.report_sections import build_report_sections


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("VIGIEPP_FORENSE", "1")
    monkeypatch.setenv("VIGIEPP_FORENSE_LICENSE", "dev")
    monkeypatch.setenv("VIGIEPP_AUTH", "1")
    monkeypatch.setenv("VIGIEPP_ADMIN_PIN", "vigiepp")
    return TestClient(app)


def _login(client: TestClient) -> None:
    res = client.post("/api/forense/auth/login", json={"pin": "vigiepp"})
    assert res.status_code == 200


def test_match_events_for_query():
    timeline = ensure_event_ids(
        [
            {"type": "proximity", "message": "Posible proximidad crítica persona–maquinaria"},
            {"type": "epp", "message": "Sin casco visible"},
        ]
    )
    matches = match_events_for_query("proximidad persona maquinaria", timeline)
    assert len(matches) == 1
    assert matches[0]["type"] == "proximity"


def test_build_report_sections_structure():
    job = {
        "id": "aabbccddeeff",
        "title": "Caso demo",
        "site": "Faena",
        "template_name": "General",
        "analysis": {
            "timeline": ensure_event_ids(
                [{"type": "epp", "time_sec": 1.0, "time_label": "00:01", "message": "Sin casco"}]
            ),
            "keyframes": [],
            "kinematics": {},
            "speed_series": [],
        },
        "comparison": {"available": False},
        "knowledge": {},
    }
    report = build_report_sections(job)
    assert report["title"] == "Caso demo"
    assert report["sections"]
    ids = {s["id"] for s in report["sections"]}
    assert "executive" in ids
    assert "facts" in ids
    assert "recommendations" in ids


def test_report_sections_api(client, tmp_path, monkeypatch):
    job_id = "112233445566"
    job = {
        "id": job_id,
        "title": "API sections",
        "site": "Faena",
        "status": "done",
        "analysis": {"timeline": [], "keyframes": []},
        "template_name": "General",
    }
    monkeypatch.setattr("forense.app.jobs.JOBS_DIR", tmp_path)
    monkeypatch.setattr("forense.app.jobs._jobs", {job_id: job})
    _login(client)
    res = client.get(f"/api/forense/jobs/{job_id}/report-sections")
    assert res.status_code == 200
    assert res.json()["report"]["sections"]


def test_review_audit_api(client, tmp_path, monkeypatch):
    job_id = "223344556677"
    timeline = ensure_event_ids([{"type": "fall", "time_sec": 2.0, "time_label": "00:02", "message": "Caída"}])
    eid = timeline[0]["event_id"]
    job = {
        "id": job_id,
        "title": "Audit",
        "site": "Faena",
        "status": "done",
        "analysis": {"timeline": timeline, "keyframes": []},
        "event_feedback": {
            eid: {
                "verdict": "confirmed",
                "note": "visto",
                "at": "2026-09-04T12:00:00+00:00",
                "reviewed_by": "admin",
                "type": "fall",
                "message": "Caída",
            }
        },
        "template_name": "General",
    }
    monkeypatch.setattr("forense.app.jobs.JOBS_DIR", tmp_path)
    monkeypatch.setattr("forense.app.jobs._jobs", {job_id: job})
    _login(client)
    res = client.get(f"/api/forense/jobs/{job_id}/review-audit.json")
    assert res.status_code == 200
    data = res.json()
    assert len(data["entries"]) == 1
    assert data["entries"][0]["reviewed_by"] == "admin"


def test_dismiss_matching_events(tmp_path, monkeypatch):
    job_id = "334455667788"
    timeline = ensure_event_ids(
        [
            {"type": "proximity", "time_sec": 1.0, "message": "Proximidad crítica detectada"},
            {"type": "epp", "time_sec": 2.0, "message": "Sin guantes"},
        ]
    )
    job = {
        "id": job_id,
        "title": "match",
        "site": "Faena",
        "status": "done",
        "analysis": {"timeline": timeline, "keyframes": []},
        "template_name": "General",
    }
    monkeypatch.setattr("forense.app.jobs.JOBS_DIR", tmp_path)
    monkeypatch.setattr("forense.app.jobs._jobs", {job_id: job})
    monkeypatch.setattr("forense.app.jobs._regenerate_job_outputs", lambda _jid: None)

    updated, ids = dismiss_matching_events(job_id, "proximidad crítica", reviewed_by="admin")
    assert len(ids) >= 1
    assert updated["event_feedback"][ids[0]]["reviewed_by"] == "admin"


def test_refocus_accepts_multi_camera(tmp_path, monkeypatch):
    job_id = "445566778899"
    src0 = tmp_path / job_id / "sources" / "cam0.mp4"
    src1 = tmp_path / job_id / "sources" / "cam1.mp4"
    src0.parent.mkdir(parents=True)
    src0.write_bytes(b"x")
    src1.write_bytes(b"x")
    job = {
        "id": job_id,
        "title": "multi",
        "site": "Faena",
        "status": "done",
        "profile": "epp_completo",
        "template_id": "general",
        "meters_per_pixel": 0.045,
        "max_machinery_kmh": 15,
        "max_person_kmh": 8,
        "min_distance_m": 2,
        "sources": [
            {"label": "Cám. 1", "path": str(src0)},
            {"label": "Cám. 2", "path": str(src1)},
        ],
        "analysis": {"timeline": [], "keyframes": []},
    }
    monkeypatch.setattr("forense.app.jobs.JOBS_DIR", tmp_path)
    monkeypatch.setattr("forense.app.jobs._jobs", {job_id: job})
    started = refocus_job(
        job_id,
        focus_description="zona",
        focus_from_sec=1.0,
        focus_until_sec=3.0,
        camera_index=1,
    )
    assert started["focus_camera_index"] == 1
    assert started["status"] == "processing"


def test_refocus_all_cameras(tmp_path, monkeypatch):
    job_id = "556677889900"
    src0 = tmp_path / job_id / "sources" / "cam0.mp4"
    src1 = tmp_path / job_id / "sources" / "cam1.mp4"
    src0.parent.mkdir(parents=True)
    src0.write_bytes(b"x")
    src1.write_bytes(b"x")
    job = {
        "id": job_id,
        "title": "multi-all",
        "site": "Faena",
        "status": "done",
        "profile": "epp_completo",
        "template_id": "general",
        "meters_per_pixel": 0.045,
        "max_machinery_kmh": 15,
        "max_person_kmh": 8,
        "min_distance_m": 2,
        "sources": [
            {"label": "Cám. 1", "path": str(src0)},
            {"label": "Cám. 2", "path": str(src1)},
        ],
        "analysis": {"timeline": [], "keyframes": []},
    }
    monkeypatch.setattr("forense.app.jobs.JOBS_DIR", tmp_path)
    monkeypatch.setattr("forense.app.jobs._jobs", {job_id: job})
    started = refocus_job(
        job_id,
        focus_description="zona",
        focus_from_sec=1.0,
        focus_until_sec=3.0,
        all_cameras=True,
    )
    assert started["focus_all_cameras"] is True
    assert started["status"] == "processing"
