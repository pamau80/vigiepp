"""Tests conectores EHS."""

from __future__ import annotations

from app import ehs_connectors as ehs_mod


def test_ehs_config_defaults(tmp_path, monkeypatch):
    monkeypatch.setenv("VIGIEPP_DATA_DIR", str(tmp_path))
    cfg = ehs_mod.get_config()
    assert "webhook" in cfg["connectors"]
    assert "safetycloud" in cfg["connectors"]


def test_ehs_save_connector(tmp_path, monkeypatch):
    monkeypatch.setenv("VIGIEPP_DATA_DIR", str(tmp_path))
    ehs_mod.save_config(
        {
            "connectors": {
                "webhook": {"enabled": True, "url": "https://example.com/hook"},
            }
        }
    )
    cfg = ehs_mod.get_config()
    assert cfg["connectors"]["webhook"]["enabled"] is True
