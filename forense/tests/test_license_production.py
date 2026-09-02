"""Tests licencia Forense producción."""

from __future__ import annotations

import time

from forense.app.license import parse_license_key, sign_license, verify_license


def test_sign_and_verify_license(monkeypatch):
    monkeypatch.setenv("VIGIEPP_FORENSE", "1")
    monkeypatch.setenv("VIGIEPP_FORENSE_SIGNING_KEY", "test-signing-key")
    exp = int(time.time()) + 86400 * 30
    key = sign_license("faena-demo", exp, secret="test-signing-key")
    ok, msg = verify_license(key)
    assert ok
    assert "faena-demo" in msg
    parsed = parse_license_key(key)
    assert parsed["site_id"] == "faena-demo"
    assert parsed["expires_unix"] == exp


def test_expired_license_rejected(monkeypatch):
    import hashlib
    import hmac

    monkeypatch.setenv("VIGIEPP_FORENSE", "1")
    monkeypatch.setenv("VIGIEPP_FORENSE_SIGNING_KEY", "test-signing-key")
    exp = int(time.time()) - 60
    payload = f"faena-vieja.{exp}"
    sig = hmac.new(b"test-signing-key", payload.encode(), hashlib.sha256).hexdigest()[:32]
    key = f"{payload}.{sig}"
    ok, msg = verify_license(key)
    assert not ok
    assert "expirada" in msg.lower()
