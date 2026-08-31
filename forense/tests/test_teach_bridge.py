"""Tests estado Teach desde Forense."""

from __future__ import annotations

from forense.app.teach_bridge import teach_status


def test_teach_status_shape():
    data = teach_status()
    assert "total_samples" in data
    assert "teach_classes" in data
    assert isinstance(data["teach_classes"], list)
