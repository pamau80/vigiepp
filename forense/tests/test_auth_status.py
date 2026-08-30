"""Tests auth Forense — status sin 401 ruidoso."""

from __future__ import annotations

from fastapi.testclient import TestClient


def test_auth_status_without_session(tmp_path, monkeypatch):
    monkeypatch.setenv("VIGIEPP_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("VIGIEPP_AUTH", "1")
    monkeypatch.setenv("VIGIEPP_ADMIN_PIN", "forense-admin")
    monkeypatch.setenv("VIGIEPP_FORENSE", "1")
    monkeypatch.setenv("VIGIEPP_FORENSE_LICENSE", "dev")
    from forense.app.main import app

    client = TestClient(app)
    r = client.get("/api/forense/auth/status")
    assert r.status_code == 200
    body = r.json()
    assert body["authenticated"] is False
    assert body["can_access"] is False


def test_favicon_route():
    from forense.app.main import app

    client = TestClient(app)
    r = client.get("/favicon.ico")
    assert r.status_code == 200
