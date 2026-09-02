"""Tests bloque excelencia edge."""

from __future__ import annotations

from app.excellence import edge_excellence_summary


def test_excellence_summary():
    data = edge_excellence_summary(identity_ready=True, epp_ready=True)
    assert data["tier"] == "edge_sovereign"
    assert data["capabilities"]["actions_presets"] >= 22
    assert data["capabilities"]["ehs_workflow"] is True
    assert data["edge_score"] >= 9.0
    assert len(data["differentiators"]) >= 5
