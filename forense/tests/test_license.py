"""Tests licencia Forense."""

from __future__ import annotations

import os

import pytest

from forense.app.license import license_enabled, verify_license


def test_license_dev(monkeypatch):
    monkeypatch.setenv("VIGIEPP_FORENSE", "1")
    monkeypatch.setenv("VIGIEPP_FORENSE_LICENSE", "dev")
    ok, msg = verify_license()
    assert ok
    assert "desarrollo" in msg


def test_license_missing(monkeypatch):
    monkeypatch.setenv("VIGIEPP_FORENSE", "1")
    monkeypatch.delenv("VIGIEPP_FORENSE_LICENSE", raising=False)
    ok, _ = verify_license()
    assert not ok


def test_license_disabled(monkeypatch):
    monkeypatch.setenv("VIGIEPP_FORENSE", "0")
    assert not license_enabled()
