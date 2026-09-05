"""Tests de seguridad Forense (P0 auditoría)."""

from __future__ import annotations

import time

import pytest
from fastapi.testclient import TestClient

from forense.app.jobs import keyframe_path
from forense.app.license import sign_license, verify_license
from forense.app.main import app
from forense.app.path_safety import safe_entry_id, safe_job_id, safe_keyframe_name


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


def test_keyframe_path_rejects_traversal(tmp_path, monkeypatch):
    monkeypatch.setattr("forense.app.jobs.JOBS_DIR", tmp_path)
    job_id = "40041a6c30ca"
    job_dir = tmp_path / job_id / "keyframes"
    job_dir.mkdir(parents=True)
    (job_dir / "kf_000.jpg").write_bytes(b"jpeg")
    (tmp_path / job_id / "job.json").write_text("{}", encoding="utf-8")

    assert keyframe_path(job_id, "kf_000.jpg") is not None
    assert keyframe_path(job_id, "../job.json") is None
    assert keyframe_path(job_id, "..\\job.json") is None
    assert keyframe_path(job_id, "kf_999.jpg") is None


def test_safe_job_id_and_entry_id():
    assert safe_job_id("40041a6c30ca")
    assert safe_job_id("../etc") is None
    assert safe_job_id("DROP TABLE") is None
    assert safe_entry_id("kn-abc1234567")
    assert safe_entry_id("../kn-evil") is None
    assert safe_keyframe_name("kf_001.jpg")
    assert safe_keyframe_name("../job.json") is None


def test_knowledge_thumb_rejects_traversal(client):
    _login(client)
    res = client.get("/api/forense/knowledge/../jobs/thumb.jpg")
    assert res.status_code in (404, 422)


def test_keyframe_route_rejects_traversal(client, tmp_path, monkeypatch):
    monkeypatch.setattr("forense.app.jobs.JOBS_DIR", tmp_path)
    job_id = "10daf3d0cea9"
    kf_dir = tmp_path / job_id / "keyframes"
    kf_dir.mkdir(parents=True)
    (kf_dir / "kf_000.jpg").write_bytes(b"jpeg")
    (tmp_path / job_id / "job.json").write_text('{"id":"10daf3d0cea9"}', encoding="utf-8")
    monkeypatch.setattr(
        "forense.app.jobs._jobs",
        {"10daf3d0cea9": {"id": job_id, "status": "done", "analysis": {"keyframes": []}}},
    )
    _login(client)
    ok = client.get(f"/api/forense/jobs/{job_id}/keyframes/kf_000.jpg")
    assert ok.status_code == 200
    bad = client.get(f"/api/forense/jobs/{job_id}/keyframes/../job.json")
    assert bad.status_code == 404


def test_operator_pin_rejected(client, monkeypatch):
    monkeypatch.setenv("VIGIEPP_OPERATOR_PIN", "porteria")
    res = client.post("/api/forense/auth/login", json={"pin": "porteria"})
    assert res.status_code == 403


def test_jobs_list_requires_auth(client):
    res = client.get("/api/forense/jobs")
    assert res.status_code == 401


def test_production_license_requires_signing_key(monkeypatch):
    monkeypatch.setenv("VIGIEPP_FORENSE", "1")
    monkeypatch.setenv("VIGIEPP_FORENSE_LICENSE", "faena-norte.9999999999.deadbeefdeadbeefdeadbeefde")
    monkeypatch.delenv("VIGIEPP_FORENSE_SIGNING_KEY", raising=False)
    ok, msg = verify_license()
    assert not ok
    assert "SIGNING_KEY" in msg


def test_production_license_verifies_with_explicit_key(monkeypatch):
    monkeypatch.setenv("VIGIEPP_FORENSE", "1")
    monkeypatch.setenv("VIGIEPP_FORENSE_SIGNING_KEY", "prod-verify-key")
    exp = int(time.time()) + 86400
    key = sign_license("faena-norte", exp, secret="prod-verify-key")
    monkeypatch.setenv("VIGIEPP_FORENSE_LICENSE", key)
    ok, msg = verify_license(key)
    assert ok
    assert "faena-norte" in msg


def test_invalid_job_id_returns_not_found(client):
    _login(client)
    res = client.get("/api/forense/jobs/../../etc")
    assert res.status_code in (404, 422)
