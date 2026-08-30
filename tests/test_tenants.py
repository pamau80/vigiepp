"""Tests multi-sitio / faenas."""

from __future__ import annotations

import pytest


@pytest.fixture()
def isolated_data(tmp_path, monkeypatch):
    monkeypatch.setenv("VIGIEPP_DATA_DIR", str(tmp_path))
    return tmp_path


def test_create_and_activate_site(isolated_data):
    from app import tenants as tenants_mod

    sites_before = tenants_mod.list_sites()
    assert any(s["id"] == "default" for s in sites_before)

    site = tenants_mod.create_site("Faena Norte")
    assert site["name"] == "Faena Norte"
    assert site["id"]

    active = tenants_mod.set_active_site(site["id"])
    assert active["id"] == site["id"]
    assert tenants_mod.get_active_site_id() == site["id"]

    data_dir = tenants_mod.site_data_dir(site["id"])
    assert data_dir.exists()
    assert (data_dir / "faces").exists()
