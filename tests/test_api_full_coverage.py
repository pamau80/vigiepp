"""Cobertura API completa — todos los endpoints registrados."""

from __future__ import annotations

import io
import zipfile

import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("VIGIEPP_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("VIGIEPP_AUTH", "0")
    from app.main import app

    return TestClient(app)


def test_build_v62(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    body = r.json()
    assert body["build"] == "v62"
    assert "epp_custom" in body
    assert body["epp_custom"] is False
    assert "otel" in body


def test_all_get_endpoints(client):
    gets = [
        "/api/health",
        "/api/auth/status",
        "/api/profiles",
        "/api/ppe/catalog",
        "/api/zones",
        "/api/zones/presets",
        "/api/scans/recent",
        "/api/reports/stats",
        "/api/reports/print",
        "/api/reports/summary.txt",
        "/api/notifications/config",
        "/api/notifications/log",
        "/api/cameras",
        "/api/nvr/vendors",
        "/api/nvr/devices",
        "/api/watchlist",
        "/api/audit",
        "/api/identity/workers",
        "/api/identity/consent.csv",
        "/api/teach/guide",
        "/api/teach/classes",
        "/api/teach/stats",
        "/api/actions/rules",
        "/api/actions/settings",
        "/api/actions/sources",
        "/api/actions/presets",
        "/api/actions/events",
        "/api/sites",
        "/api/privacy/config",
        "/api/ehs/config",
        "/api/ehs/incidents",
        "/metrics",
        "/",
    ]
    for path in gets:
        r = client.get(path)
        assert r.status_code in (200, 202), f"GET {path} -> {r.status_code}"


def test_auth_flow(client, monkeypatch):
    monkeypatch.setenv("VIGIEPP_AUTH", "1")
    monkeypatch.setenv("VIGIEPP_ADMIN_PIN", "testadmin")
    from app.main import app

    c = TestClient(app)
    r = c.post("/api/auth/login", json={"pin": "testadmin"})
    assert r.status_code == 200
    assert r.json().get("ok")
    r2 = c.get("/api/auth/me")
    assert r2.status_code == 200


def test_zones_save(client):
    r = client.post("/api/zones", json={"zones": []})
    assert r.status_code == 200


def test_zones_preset(client):
    r = client.get("/api/zones/presets")
    presets = r.json().get("presets") or []
    if presets:
        pid = presets[0]["id"]
        r2 = client.post(f"/api/zones/presets/{pid}")
        assert r2.status_code == 200


def test_reports_exports(client):
    r = client.get("/api/reports/export.csv")
    assert r.status_code == 200
    assert "text/csv" in r.headers.get("content-type", "")
    r2 = client.get("/api/reports/print.html")
    assert r2.status_code == 200


def test_notifications_config_roundtrip(client):
    r = client.post("/api/notifications/config", json={"enabled": True})
    assert r.status_code == 200
    r2 = client.get("/api/notifications/config")
    assert r2.status_code == 200


def test_notifications_test_send(client):
    r = client.post("/api/notifications/test")
    assert r.status_code == 200
    r2 = client.post(
        "/api/notifications/send",
        json={"name": "T", "summary": "test", "profile": "general"},
    )
    assert r2.status_code == 200


def test_cameras_crud(client):
    r = client.post(
        "/api/cameras",
        json={"name": "TestCam", "url": "rtsp://192.168.1.50/stream"},
    )
    assert r.status_code == 200
    cam = r.json()["camera"]
    r2 = client.get("/api/cameras")
    assert any(c["id"] == cam["id"] for c in r2.json()["cameras"])
    r3 = client.delete(f"/api/cameras/{cam['id']}")
    assert r3.status_code == 200


def test_watchlist_crud(client):
    r = client.post(
        "/api/watchlist",
        json={"name": "W1", "url": "rtsp://10.0.0.1/ch1", "enabled": False},
    )
    assert r.status_code == 200
    ch = r.json()["channel"]
    r2 = client.delete(f"/api/watchlist/{ch['id']}")
    assert r2.status_code == 200


def test_mass_scan(client):
    r = client.post("/api/surveillance/mass/scan")
    assert r.status_code == 200
    assert r.json().get("ok")


def test_nvr_vendors_probe(client, monkeypatch):
    monkeypatch.setenv("VIGIEPP_ALLOW_LAN", "1")
    r = client.post(
        "/api/nvr/probe",
        json={"vendor": "dahua", "host": "192.168.1.1", "channel_count": 2},
    )
    assert r.status_code == 200


def test_sites_roundtrip(client):
    r = client.post("/api/sites", json={"name": "Test Site API"})
    assert r.status_code == 200
    site_id = r.json()["site"]["id"]
    r2 = client.post("/api/sites/active", json={"site_id": site_id})
    assert r2.status_code == 200
    r3 = client.post("/api/sites/active", json={"site_id": "default"})
    assert r3.status_code == 200


def test_privacy_retention(client):
    r = client.post("/api/privacy/retention/run")
    assert r.status_code == 200


def test_ehs_config_push(client):
    r = client.post("/api/ehs/config", json={"connectors": {"webhook": {"enabled": False}}})
    assert r.status_code == 200
    r2 = client.post(
        "/api/ehs/push",
        json={"summary": "Test incident", "compliant": False, "missing": ["casco"]},
    )
    assert r2.status_code == 200
    body = r2.json()
    assert body.get("ok")
    assert body.get("incident", {}).get("status") == "open"
    r3 = client.get("/api/ehs/incidents")
    assert r3.status_code == 200
    assert r3.json().get("count", 0) >= 1


def test_audit_export(client):
    r = client.get("/api/audit/export.csv")
    assert r.status_code == 200


def test_identity_backup_zip(client):
    r = client.get("/api/identity/backup")
    assert r.status_code == 200
    buf = io.BytesIO(r.content)
    with zipfile.ZipFile(buf) as zf:
        assert len(zf.namelist()) >= 0


def test_rtsp_start_stop(client, monkeypatch):
    monkeypatch.setenv("VIGIEPP_RTSP_ALLOW", "*")
    url = "rtsp://192.168.1.50/test"
    r = client.post("/api/rtsp/start", json={"url": url})
    assert r.status_code in (200, 503)
    r2 = client.post("/api/rtsp/stop", json={"url": url})
    assert r2.status_code == 200


def test_security_headers(client):
    r = client.get("/api/health")
    assert r.headers.get("x-content-type-options") == "nosniff"
    assert r.headers.get("x-frame-options") == "DENY"
