"""Tests revisión de eventos — confirmar / descartar falsos positivos."""

from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

from forense.app.event_feedback import (
    active_timeline,
    apply_review_state,
    ensure_event_ids,
    filter_suppressed_events,
    fingerprint_event,
    is_suppressed,
    record_dismissal,
)
from forense.app.jobs import review_event
from forense.app.main import app
from forense.app.report import build_report_markdown


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


def test_fingerprint_event_stable():
    ev = {"type": "fall", "time_sec": 12.34, "rule_id": "kin_fall", "message": "Caída detectada"}
    assert fingerprint_event(ev, 0) == fingerprint_event(ev, 0)
    assert fingerprint_event(ev, 0) != fingerprint_event({**ev, "message": "otro"}, 0)


def test_ensure_event_ids_assigns_ids():
    timeline = [{"type": "epp", "time_sec": 1.0, "message": "Sin casco"}]
    out = ensure_event_ids(timeline)
    assert out[0]["event_id"]
    assert out[0]["event_id"] == ensure_event_ids(timeline)[0]["event_id"]


def test_active_timeline_excludes_dismissed():
    timeline = ensure_event_ids(
        [
            {"type": "epp", "time_sec": 1.0, "message": "a"},
            {"type": "fall", "time_sec": 2.0, "message": "b"},
        ]
    )
    eid = timeline[1]["event_id"]
    feedback = {eid: {"verdict": "dismissed"}}
    active = active_timeline(timeline, feedback)
    assert len(active) == 1
    assert active[0]["message"] == "a"
    reviewed = apply_review_state(timeline, feedback)
    assert reviewed[1]["review_status"] == "dismissed"


def test_record_dismissal_filters_future_events(tmp_path, monkeypatch):
    supp_file = tmp_path / "suppression_rules.json"
    monkeypatch.setattr("forense.app.event_feedback._SUPPRESSION_FILE", supp_file)
    ev = {"type": "fall", "rule_id": "kin_fall", "message": "Caída sospechosa"}
    record_dismissal(ev, job_id="job123")
    assert is_suppressed(ev)
    events = [
        ev,
        {"type": "epp", "rule_id": "no_helmet", "message": "Sin casco"},
    ]
    filtered = filter_suppressed_events(events)
    assert len(filtered) == 1
    assert filtered[0]["type"] == "epp"


def test_review_event_updates_job_and_report(tmp_path, monkeypatch):
    job_id = "aabbccddeeff"
    job_dir = tmp_path / job_id
    job_dir.mkdir(parents=True)
    timeline = ensure_event_ids(
        [
            {
                "type": "fall",
                "time_sec": 5.0,
                "time_label": "00:05",
                "severity": "high",
                "rule_id": "kin_fall",
                "message": "Posible caída",
            },
            {
                "type": "epp",
                "time_sec": 8.0,
                "time_label": "00:08",
                "severity": "medium",
                "message": "Sin casco",
            },
        ]
    )
    job = {
        "id": job_id,
        "title": "Caso prueba",
        "site": "Faena",
        "status": "done",
        "analysis": {"timeline": timeline, "keyframes": []},
        "template_name": "General",
    }
    monkeypatch.setattr("forense.app.jobs.JOBS_DIR", tmp_path)
    monkeypatch.setattr("forense.app.jobs._jobs", {job_id: job})
    monkeypatch.setattr("forense.app.jobs._regenerate_job_outputs", lambda _jid: None)

    fall_id = timeline[0]["event_id"]
    updated = review_event(job_id, fall_id, verdict="dismissed", note="falso positivo")
    assert updated["event_feedback"][fall_id]["verdict"] == "dismissed"
    active = active_timeline(updated["analysis"]["timeline"], updated["event_feedback"])
    assert len(active) == 1
    assert active[0]["type"] == "epp"

    report = build_report_markdown(updated)
    assert "Posible caída" not in report.split("Eventos descartados")[0]
    assert "descartados" in report.lower() or "descartado" in report.lower()


def test_review_event_api(client, tmp_path, monkeypatch):
    job_id = "112233445566"
    timeline = ensure_event_ids(
        [{"type": "proximity", "time_sec": 3.0, "time_label": "00:03", "message": "Muy cerca"}]
    )
    job = {
        "id": job_id,
        "title": "API test",
        "site": "Faena",
        "status": "done",
        "analysis": {"timeline": timeline, "keyframes": []},
        "template_name": "General",
    }
    monkeypatch.setattr("forense.app.jobs.JOBS_DIR", tmp_path)
    monkeypatch.setattr("forense.app.jobs._jobs", {job_id: job})
    monkeypatch.setattr("forense.app.jobs._regenerate_job_outputs", lambda _jid: None)
    (tmp_path / job_id).mkdir(parents=True)
    (tmp_path / job_id / "job.json").write_text(json.dumps(job), encoding="utf-8")

    _login(client)
    event_id = timeline[0]["event_id"]
    res = client.post(
        f"/api/forense/jobs/{job_id}/events/{event_id}/review",
        json={"verdict": "confirmed", "note": "visto en video"},
    )
    assert res.status_code == 200
    payload = res.json()
    assert payload["ok"] is True
    assert payload["job"]["event_feedback"][event_id]["verdict"] == "confirmed"
    assert payload["job"]["analysis"]["timeline"][0]["review_status"] == "confirmed"
