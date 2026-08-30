"""Tests workflow incidentes EHS."""

from __future__ import annotations

import pytest

from app import ehs_incidents as inc_mod


@pytest.fixture(autouse=True)
def isolated_incidents(tmp_path, monkeypatch):
    monkeypatch.setenv("VIGIEPP_DATA_DIR", str(tmp_path))
    yield


def test_create_and_list_incidents():
    inc = inc_mod.create_incident({"summary": "Sin casco", "worker_name": "Juan"}, source="manual")
    assert inc["status"] == "open"
    items = inc_mod.list_incidents()
    assert len(items) == 1
    assert items[0]["summary"] == "Sin casco"


def test_update_incident_status_flow():
    inc = inc_mod.create_incident({"summary": "Near miss"})
    updated = inc_mod.update_incident_status(inc["id"], "closed", note="Revisado en terreno")
    assert updated["status"] == "closed"
    assert updated["closed_at"]
    verified = inc_mod.update_incident_status(inc["id"], "verified")
    assert verified["status"] == "verified"
    assert verified["verified_at"]


def test_list_filter_by_status():
    a = inc_mod.create_incident({"summary": "A"})
    b = inc_mod.create_incident({"summary": "B"})
    inc_mod.update_incident_status(b["id"], "closed")
    open_items = inc_mod.list_incidents(status="open")
    assert any(i["id"] == a["id"] for i in open_items)
    assert not any(i["id"] == b["id"] for i in open_items)


def test_invalid_status_raises():
    inc = inc_mod.create_incident({"summary": "X"})
    with pytest.raises(ValueError):
        inc_mod.update_incident_status(inc["id"], "invalid")
