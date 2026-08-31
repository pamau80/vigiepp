"""Tests importación externa a biblioteca Forense."""

from __future__ import annotations

from pathlib import Path

import pytest

from forense.app.knowledge import find_by_source_id, list_knowledge, reset_knowledge
from forense.app.knowledge_import import (
    import_osha,
    import_seeds,
    list_import_catalog,
    osha_row_to_entry,
)


@pytest.fixture(autouse=True)
def _isolated_knowledge(monkeypatch, tmp_path: Path):
    kn_dir = tmp_path / "knowledge"
    kn_dir.mkdir()
    monkeypatch.setattr("forense.app.knowledge.KNOWLEDGE_DIR", kn_dir)
    monkeypatch.setattr("forense.app.knowledge._INDEX_PATH", kn_dir / "index.json")
    reset_knowledge()
    yield
    reset_knowledge()


def test_osha_row_mapping():
    row = {
        "summary_nr": 509257,
        "event_desc": "Employee killed when brakes on crane fail",
        "event_keyword": "BRAKE,CRANE,CONSTRUCTION",
        "abstract_text": None,
        "fatality": "X",
    }
    entry = osha_row_to_entry(row, default_industry="portuario")
    assert entry is not None
    assert entry["source"] == "osha"
    assert entry["source_id"] == "osha:509257"
    assert entry["situation_type"] in ("unsafe_act", "collision", "proximity")
    assert "crane" in entry["title"].lower() or "Employee" in entry["title"]


def test_import_seeds():
    result = import_seeds(skip_existing=True)
    assert result["imported"] >= 20
    entries = list_knowledge()
    assert len(entries) >= 20
    port = [e for e in entries if e.get("industry") == "portuario"]
    assert any("grúa" in (e.get("title") or "").lower() or "grua" in (e.get("description") or "").lower() for e in port)
    assert find_by_source_id("seed", "seed:portuario:maniobra-imprudente-gruas")


def test_import_seeds_skip_duplicates():
    first = import_seeds(skip_existing=True)
    second = import_seeds(skip_existing=True)
    assert first["imported"] > 0
    assert second["skipped"] >= first["imported"]
    assert second["imported"] == 0


def test_import_catalog():
    catalog = list_import_catalog()
    assert any(c["id"] == "seeds" for c in catalog)
    assert any(c["id"] == "osha_crane" for c in catalog)


def test_import_osha_mocked(monkeypatch):
    def fake_fetch(**kwargs):
        return [
            {
                "summary_nr": 999001,
                "event_desc": "Crane struck worker on dock",
                "event_keyword": "CRANE,DOCK,STRUCK BY",
                "abstract_text": "Stevedore injured during lift.",
                "fatality": None,
            }
        ]

    monkeypatch.setattr("forense.app.knowledge_import.fetch_osha_labordata", fake_fetch)
    result = import_osha(keywords=["CRANE"], limit_per_keyword=5, default_industry="portuario")
    assert result["imported"] == 1
    entry = find_by_source_id("osha", "osha:999001")
    assert entry is not None
    assert entry["industry"] == "portuario"
