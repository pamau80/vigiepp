"""Tests RBAC — roles admin/guardia, permisos y cuentas."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def rbac_client(tmp_path, monkeypatch):
    monkeypatch.setenv("VIGIEPP_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("VIGIEPP_AUTH", "1")
    monkeypatch.setenv("VIGIEPP_ADMIN_PIN", "rbac-admin-pin")
    monkeypatch.setenv("VIGIEPP_OPERATOR_PIN", "rbac-guard-pin")
    monkeypatch.setenv("VIGIEPP_PORTERIA_PIN", "rbac-porteria-pin")
    from app.main import app

    return TestClient(app)


def _login(client: TestClient, pin: str) -> dict[str, str]:
    r = client.post("/api/auth/login", json={"pin": pin})
    assert r.status_code == 200, r.text
    token = r.json()["token"]
    return {"X-VigiEPP-Key": token}


def test_admin_login_has_all_permissions(rbac_client):
    hdrs = _login(rbac_client, "rbac-admin-pin")
    me = rbac_client.get("/api/auth/me", headers=hdrs).json()
    assert me["role"] == "admin"
    assert "*" in me["permissions"]


def test_guard_env_pin_role(rbac_client):
    hdrs = _login(rbac_client, "rbac-guard-pin")
    me = rbac_client.get("/api/auth/me", headers=hdrs).json()
    assert me["role"] == "guard"
    assert "live.rtsp" in me["permissions"]
    assert "users.manage" not in me["permissions"]


def test_porteria_env_pin_minimal(rbac_client):
    hdrs = _login(rbac_client, "rbac-porteria-pin")
    me = rbac_client.get("/api/auth/me", headers=hdrs).json()
    assert me["role"] == "operator"
    assert "live.view" in me["permissions"]
    assert "live.rtsp" not in me["permissions"]


def test_guard_cannot_manage_users(rbac_client):
    hdrs = _login(rbac_client, "rbac-guard-pin")
    r = rbac_client.get("/api/auth/users", headers=hdrs)
    assert r.status_code == 403


def test_admin_creates_guard_account(rbac_client):
    admin = _login(rbac_client, "rbac-admin-pin")
    r = rbac_client.post(
        "/api/auth/users",
        headers=admin,
        json={
            "name": "Guardia Test",
            "pin": "4422",
            "role": "guard",
            "extra_permissions": ["teach.use"],
        },
    )
    assert r.status_code == 200, r.text
    user = r.json()["user"]
    assert user["name"] == "Guardia Test"
    assert "teach.use" in user["permissions"]

    guard_hdrs = _login(rbac_client, "4422")
    me = rbac_client.get("/api/auth/me", headers=guard_hdrs).json()
    assert me["role"] == "guard"
    assert "teach.use" in me["permissions"]

    r_te = rbac_client.get("/api/teach/classes", headers=guard_hdrs)
    assert r_te.status_code == 200


def test_guard_blocked_from_zones_write(rbac_client):
    hdrs = _login(rbac_client, "rbac-guard-pin")
    r = rbac_client.post("/api/zones", json={"name": "Z1", "points": []}, headers=hdrs)
    assert r.status_code == 403


def test_permissions_catalog_public_within_auth(rbac_client):
    admin = _login(rbac_client, "rbac-admin-pin")
    r = rbac_client.get("/api/auth/permissions", headers=admin)
    assert r.status_code == 200
    body = r.json()
    assert any(p["id"] == "live.view" for p in body["permissions"])
