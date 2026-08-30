"""Tests RBAC granular v65."""

from __future__ import annotations

from app.rbac import is_admin_only, operator_allowed, rbac_summary


def test_operator_allowed_porteria():
    assert operator_allowed("POST", "/api/detect")
    assert operator_allowed("POST", "/api/identity/identify")
    assert operator_allowed("POST", "/api/rtsp/start")
    assert operator_allowed("GET", "/api/zones")
    assert operator_allowed("GET", "/api/actions/rules")
    assert operator_allowed("GET", "/api/ehs/incidents")
    assert operator_allowed("POST", "/api/ehs/push")


def test_operator_denied_admin_sections():
    assert not operator_allowed("GET", "/api/identity/workers")
    assert not operator_allowed("GET", "/api/cameras")
    assert not operator_allowed("GET", "/api/nvr/devices")
    assert not operator_allowed("GET", "/api/ehs/config")
    assert not operator_allowed("POST", "/api/actions/settings")
    assert not operator_allowed("POST", "/api/ehs/config")
    assert not operator_allowed("PATCH", "/api/ehs/incidents/abc")
    assert not operator_allowed("POST", "/api/zones")


def test_is_admin_only_compat():
    assert is_admin_only("POST", "/api/cameras")
    assert not is_admin_only("POST", "/api/detect")


def test_rbac_summary():
    data = rbac_summary()
    assert data["granular"] is True
    assert "operator" in data["roles"]
