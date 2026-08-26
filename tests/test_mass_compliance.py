"""Tests helper cumplimiento masivo."""

from __future__ import annotations

from app.main import _compliance_cell_fields


def test_compliance_cell_fields():
    payload = {
        "compliance": {
            "overall_compliant": False,
            "alerts": ["falta casco"],
            "persons": [{"missing": ["casco", "chaleco"]}],
        }
    }
    fields = _compliance_cell_fields(payload)
    assert fields["compliant"] is False
    assert "casco" in fields["missing"]
    assert fields["alerts"] == ["falta casco"]
