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


def test_ehs_secrets_encrypted_on_disk(tmp_path, monkeypatch):
    monkeypatch.setenv("VIGIEPP_DATA_DIR", str(tmp_path))
    from app import ehs_connectors as ehs_mod

    ehs_mod.save_config(
        {
            "connectors": {
                "webhook": {"auth_header": "Bearer secret-token"},
                "safetycloud": {"api_key": "sc-key-123"},
            }
        }
    )
    raw = (tmp_path / "ehs_connectors.json").read_text(encoding="utf-8")
    assert "secret-token" not in raw
    assert "sc-key-123" not in raw
    pub = ehs_mod.get_config()
    assert pub["connectors"]["webhook"]["auth_header_set"]
    assert pub["connectors"]["safetycloud"]["api_key_set"]
