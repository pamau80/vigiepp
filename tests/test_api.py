"""Tests API HTTP."""

from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("VIGIEPP_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("VIGIEPP_AUTH", "0")
    from app.main import app

    return TestClient(app)


def test_health_build(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "ok"
    assert "default_pins" not in data
    assert "privacy" in data


def test_privacy_config_roundtrip(client):
    r = client.post("/api/privacy/config", json={"qr_only_mode": True, "retention_days": 45})
    assert r.status_code == 200
    cfg = r.json()["config"]
    assert cfg["qr_only_mode"] is True
    assert cfg["retention_days"] == 45


def test_metrics_endpoint(client):
    r = client.get("/metrics")
    assert r.status_code == 200
    assert "vigiepp_uptime_seconds" in r.text


def test_oidc_state_validation():
    import time

    from app.oidc import _pending, validate_state

    _pending["unit-test-state"] = time.time()
    assert validate_state("unit-test-state")
    assert not validate_state("invalid-state")
