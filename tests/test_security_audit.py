"""Auditoría de seguridad P0/P1 — auth, SSRF, OIDC, EHS secrets."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def auth_client(tmp_path, monkeypatch):
    monkeypatch.setenv("VIGIEPP_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("VIGIEPP_AUTH", "1")
    monkeypatch.setenv("VIGIEPP_ADMIN_PIN", "audit-admin-pin")
    monkeypatch.setenv("VIGIEPP_OPERATOR_PIN", "audit-op-pin")
    from app.main import app

    return TestClient(app)


def _admin_headers(client: TestClient) -> dict[str, str]:
    r = client.post("/api/auth/login", json={"pin": "audit-admin-pin"})
    assert r.status_code == 200
    token = r.json()["token"]
    return {"X-VigiEPP-Key": token}


def test_pin_not_permanent_bearer(auth_client):
    """PIN solo válido en login — no como X-VigiEPP-Key permanente."""
    r = auth_client.get("/api/zones", headers={"X-VigiEPP-Key": "audit-admin-pin"})
    assert r.status_code == 401


def test_api_key_still_works_as_bearer(auth_client, monkeypatch):
    monkeypatch.setenv("VIGIEPP_API_KEY", "static-api-key-xyz")
    from app.main import app

    c = TestClient(app)
    r = c.get("/api/zones", headers={"X-VigiEPP-Key": "static-api-key-xyz"})
    assert r.status_code == 200


def test_login_session_works(auth_client):
    hdrs = _admin_headers(auth_client)
    r2 = auth_client.get("/api/zones", headers=hdrs)
    assert r2.status_code == 200


def test_oidc_callback_public_without_auth(auth_client):
    r = auth_client.get("/api/auth/oidc/callback?code=&state=")
    assert r.status_code in (400, 401)


def test_oidc_config_public(auth_client):
    r = auth_client.get("/api/auth/oidc/config")
    assert r.status_code == 200
    body = r.json()
    assert "enabled" in body


def test_rtsp_blocks_loopback(auth_client, monkeypatch):
    monkeypatch.setenv("VIGIEPP_ALLOW_LAN", "1")
    hdrs = _admin_headers(auth_client)
    r = auth_client.post(
        "/api/cameras",
        json={"name": "Bad", "url": "rtsp://127.0.0.1/stream"},
        headers=hdrs,
    )
    assert r.status_code == 400


def test_rtsp_blocks_metadata_host(auth_client):
    hdrs = _admin_headers(auth_client)
    r = auth_client.post(
        "/api/cameras",
        json={"name": "Bad", "url": "rtsp://metadata.google.internal/v1"},
        headers=hdrs,
    )
    assert r.status_code == 400


def test_rtsp_lan_blocked_on_cloud(auth_client, monkeypatch):
    monkeypatch.setenv("RENDER", "1")
    monkeypatch.delenv("VIGIEPP_ALLOW_LAN", raising=False)
    hdrs = _admin_headers(auth_client)
    r = auth_client.post(
        "/api/cameras",
        json={"name": "LAN", "url": "rtsp://192.168.1.50/stream"},
        headers=hdrs,
    )
    assert r.status_code == 400


def test_metrics_not_public_on_cloud(auth_client, monkeypatch):
    monkeypatch.setenv("RENDER", "1")
    monkeypatch.delenv("VIGIEPP_METRICS_PUBLIC", raising=False)
    r = auth_client.get("/metrics")
    assert r.status_code == 401


def test_metrics_public_when_explicit(auth_client, monkeypatch):
    monkeypatch.setenv("RENDER", "1")
    monkeypatch.setenv("VIGIEPP_METRICS_PUBLIC", "1")
    from app.main import app

    c = TestClient(app)
    r = c.get("/metrics")
    assert r.status_code == 200


def test_default_pins_blocked_on_cloud(auth_client, monkeypatch):
    monkeypatch.setenv("RENDER", "1")
    monkeypatch.delenv("VIGIEPP_ADMIN_PIN", raising=False)
    monkeypatch.delenv("VIGIEPP_OPERATOR_PIN", raising=False)
    from app.main import app

    c = TestClient(app)
    r = c.post("/api/auth/login", json={"pin": "vigiepp"})
    assert r.status_code == 503


def test_ehs_secrets_encrypted_on_disk(tmp_path, monkeypatch):
    monkeypatch.setenv("VIGIEPP_DATA_DIR", str(tmp_path))
    from app import ehs_connectors as ehs_mod

    ehs_mod.save_config(
        {
            "connectors": {
                "webhook": {"auth_header": "Bearer secret-token"},
                "safetycloud": {"api_key": "sc-key-123"},
            }
        }
    )
    raw = (tmp_path / "ehs_connectors.json").read_text(encoding="utf-8")
    assert "secret-token" not in raw
    assert "sc-key-123" not in raw
    pub = ehs_mod.get_config()
    assert pub["connectors"]["webhook"]["auth_header_set"]
    assert pub["connectors"]["safetycloud"]["api_key_set"]


def test_security_headers_present(auth_client):
    r = auth_client.get("/api/health")
    assert r.headers.get("x-content-type-options") == "nosniff"
    assert r.headers.get("content-security-policy")
    assert r.headers.get("x-request-id")
