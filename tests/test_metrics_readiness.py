"""Tests métricas readiness HA v67."""

from __future__ import annotations

from fastapi.testclient import TestClient


def test_prometheus_includes_readiness_gauges(tmp_path, monkeypatch):
    monkeypatch.setenv("VIGIEPP_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("VIGIEPP_AUTH", "0")
    monkeypatch.setenv("VIGIEPP_METRICS_PUBLIC", "1")
    from app.main import app

    client = TestClient(app)
    r = client.get("/metrics")
    assert r.status_code == 200
    text = r.text
    assert "vigiepp_identity_ready" in text
    assert "vigiepp_epp_ready" in text
    assert "vigiepp_data_persistent" in text
    assert "vigiepp_edge_ready" in text


def test_hsts_on_edge_default(tmp_path, monkeypatch):
    monkeypatch.setenv("VIGIEPP_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("VIGIEPP_AUTH", "0")
    monkeypatch.setenv("VIGIEPP_EDGE", "1")
    monkeypatch.delenv("VIGIEPP_HSTS", raising=False)
    from app.main import app

    client = TestClient(app)
    r = client.get("/api/health")
    assert r.headers.get("strict-transport-security")
