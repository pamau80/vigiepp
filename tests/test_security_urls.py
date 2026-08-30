"""Tests anti-SSRF."""

from __future__ import annotations

from app.security_urls import (
    edge_outbound_allowed,
    validate_lan_http_host,
    validate_outbound_url,
)


def test_validate_outbound_public_ok():
    ok, _ = validate_outbound_url("https://hooks.slack.com/services/xxx", allow_public=True)
    assert ok


def test_validate_lan_blocked_on_render(monkeypatch):
    monkeypatch.setenv("RENDER", "1")
    monkeypatch.delenv("VIGIEPP_ALLOW_LAN", raising=False)
    monkeypatch.delenv("VIGIEPP_DATA_DIR", raising=False)
    ok, msg = validate_lan_http_host("192.168.1.10")
    assert not ok
    assert "LAN" in msg or "edge" in msg.lower()


def test_edge_with_persistent_data(monkeypatch, tmp_path):
    monkeypatch.setenv("VIGIEPP_DATA_DIR", str(tmp_path))
    monkeypatch.delenv("RENDER", raising=False)
    assert edge_outbound_allowed()
