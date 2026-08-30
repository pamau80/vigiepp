"""Tests inferencia combinada EPP + identidad."""

from __future__ import annotations


def test_combined_inference_env_off(monkeypatch):
    monkeypatch.setenv("VIGIEPP_COMBINED_INFERENCE", "0")
    monkeypatch.delenv("VIGIEPP_DATA_DIR", raising=False)
    from app.inference import combined_inference_enabled

    assert combined_inference_enabled() is False


def test_combined_inference_env_on(monkeypatch):
    monkeypatch.setenv("VIGIEPP_COMBINED_INFERENCE", "1")
    from app.inference import combined_inference_enabled

    assert combined_inference_enabled() is True


def test_combined_inference_auto_persistent(monkeypatch, tmp_path):
    monkeypatch.setenv("VIGIEPP_COMBINED_INFERENCE", "auto")
    monkeypatch.setenv("VIGIEPP_DATA_DIR", str(tmp_path))
    from app.inference import combined_inference_enabled

    assert combined_inference_enabled() is True
