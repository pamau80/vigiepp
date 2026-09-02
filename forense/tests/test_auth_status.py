"""Tests auth Forense — status sin 401 ruidoso."""

from __future__ import annotations

from fastapi.testclient import TestClient


def _client(tmp_path, monkeypatch):
    monkeypatch.setenv("VIGIEPP_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("VIGIEPP_AUTH", "1")
    monkeypatch.setenv("VIGIEPP_ADMIN_PIN", "forense-admin")
    monkeypatch.setenv("VIGIEPP_FORENSE", "1")
    monkeypatch.setenv("VIGIEPP_FORENSE_LICENSE", "dev")
    from forense.app.main import app

    return TestClient(app)


def test_auth_status_without_session(tmp_path, monkeypatch):
    client = _client(tmp_path, monkeypatch)
    r = client.get("/api/forense/auth/status")
    assert r.status_code == 200
    body = r.json()
    assert body["authenticated"] is False
    assert body["can_access"] is False
    assert body.get("token") in (None, "")


def test_auth_status_returns_token_when_logged_in(tmp_path, monkeypatch):
    client = _client(tmp_path, monkeypatch)
    login = client.post("/api/forense/auth/login", json={"pin": "forense-admin"})
    assert login.status_code == 200
    token = login.json()["token"]
    r = client.get("/api/forense/auth/status")
    assert r.status_code == 200
    body = r.json()
    assert body["can_access"] is True
    assert body["token"] == token


def test_auth_logout_revokes_session(tmp_path, monkeypatch):
    client = _client(tmp_path, monkeypatch)
    login = client.post("/api/forense/auth/login", json={"pin": "forense-admin"})
    token = login.json()["token"]
    out = client.post("/api/forense/auth/logout", headers={"X-VigiEPP-Key": token})
    assert out.status_code == 200
    st = client.get("/api/forense/auth/status", headers={"X-VigiEPP-Key": token})
    assert st.json()["can_access"] is False


def test_favicon_route():
    from forense.app.main import app

    client = TestClient(app)
    r = client.get("/favicon.ico")
    assert r.status_code == 200
