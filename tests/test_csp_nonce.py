"""Tests CSP nonce v65."""

from __future__ import annotations

from fastapi.testclient import TestClient


def test_csp_nonce_in_headers(tmp_path, monkeypatch):
    monkeypatch.setenv("VIGIEPP_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("VIGIEPP_AUTH", "0")
    from app.main import app

    client = TestClient(app)
    r = client.get("/api/health")
    csp = r.headers.get("content-security-policy", "")
    assert "nonce-" in csp
    assert "'unsafe-inline'" not in csp.split("script-src")[1].split(";")[0]


def test_index_html_injects_script_nonce(tmp_path, monkeypatch):
    monkeypatch.setenv("VIGIEPP_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("VIGIEPP_AUTH", "0")
    from app.main import app

    client = TestClient(app)
    r = client.get("/")
    assert r.status_code == 200
    assert 'nonce="' in r.text
    assert '<script nonce="' in r.text
    csp = r.headers.get("content-security-policy", "")
    nonce = r.text.split('nonce="')[1].split('"')[0]
    assert f"'nonce-{nonce}'" in csp
