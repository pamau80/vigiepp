"""Operador edge — rutas permitidas vs admin-only (sin SaaS)."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def edge_client(tmp_path, monkeypatch):
    monkeypatch.setenv("VIGIEPP_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("VIGIEPP_AUTH", "1")
    monkeypatch.setenv("VIGIEPP_ADMIN_PIN", "edge-admin")
    monkeypatch.setenv("VIGIEPP_OPERATOR_PIN", "edge-operator")
    from app.main import app

    return TestClient(app)


def _hdrs(client: TestClient, pin: str) -> dict[str, str]:
    r = client.post("/api/auth/login", json={"pin": pin})
    assert r.status_code == 200
    return {"X-VigiEPP-Key": r.json()["token"]}


def test_operator_can_read_zones(edge_client):
    r = edge_client.get("/api/zones", headers=_hdrs(edge_client, "edge-operator"))
    assert r.status_code == 200


def test_operator_cannot_write_zones(edge_client):
    r = edge_client.post(
        "/api/zones",
        json={"name": "Z", "points": []},
        headers=_hdrs(edge_client, "edge-operator"),
    )
    assert r.status_code == 403


def test_operator_cannot_list_workers(edge_client):
    r = edge_client.get("/api/identity/workers", headers=_hdrs(edge_client, "edge-operator"))
    assert r.status_code == 403


def test_operator_cannot_write_actions_settings(edge_client):
    r = edge_client.post(
        "/api/actions/settings",
        json={"settings": {"action_audio_enabled": True}},
        headers=_hdrs(edge_client, "edge-operator"),
    )
    assert r.status_code == 403


def test_operator_can_read_actions_and_ehs_incidents(edge_client):
    op = _hdrs(edge_client, "edge-operator")
    assert edge_client.get("/api/actions/rules", headers=op).status_code == 200
    assert edge_client.get("/api/ehs/incidents", headers=op).status_code == 200


def test_operator_cannot_write_ehs_config(edge_client):
    r = edge_client.post(
        "/api/ehs/config",
        json={"connectors": {}},
        headers=_hdrs(edge_client, "edge-operator"),
    )
    assert r.status_code == 403


def test_operator_me_includes_rbac(edge_client):
    r = edge_client.get("/api/auth/me", headers=_hdrs(edge_client, "edge-operator"))
    assert r.status_code == 200
    body = r.json()
    assert body["role"] == "operator"
    assert body["rbac"]["admin"] is False
    assert body["rbac"]["granular"] is True


def test_admin_full_access(edge_client):
    admin = _hdrs(edge_client, "edge-admin")
    assert edge_client.get("/api/identity/workers", headers=admin).status_code == 200
    assert edge_client.get("/api/audit", headers=admin).status_code == 200
