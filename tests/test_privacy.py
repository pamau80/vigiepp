"""Tests privacidad y retención."""

from __future__ import annotations

import pytest


@pytest.fixture()
def privacy_data(tmp_path, monkeypatch):
    monkeypatch.setenv("VIGIEPP_DATA_DIR", str(tmp_path))
    return tmp_path


def test_privacy_save_and_qr_only(privacy_data):
    from app.privacy import get_config, qr_only_enabled, save_config

    cfg = save_config({"qr_only_mode": True, "retention_days": 30})
    assert cfg["qr_only_mode"] is True
    assert cfg["retention_days"] == 30
    assert qr_only_enabled()


def test_retention_purge(privacy_data):
    from datetime import datetime, timedelta, timezone

    from app.evidence import evidence_dir, save_evidence_jpeg
    from app.privacy import apply_retention

    old = datetime.now(timezone.utc) - timedelta(days=120)
    path = evidence_dir() / "ev-old.jpg"
    path.write_bytes(b"fake")
    path.touch()
    import os

    os.utime(path, (old.timestamp(), old.timestamp()))
    result = apply_retention(90)
    assert result["evidence_removed"] >= 1
