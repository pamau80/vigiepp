"""Tests preview de fuentes sin importar."""

from __future__ import annotations

from forense.app.sources.sync import preview_source


def test_preview_seeds_construccion():
    result = preview_source("seeds_construccion", limit=10)
    assert result.get("ok") is True
    assert result.get("source_id") == "seeds_construccion"
    assert result.get("valid_count", 0) >= 1
    assert result.get("candidates", 0) >= 1
