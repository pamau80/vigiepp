"""Tests conectores de fuentes de conocimiento Forense."""

from __future__ import annotations

from forense.app.sources.registry import SYNC_SOURCES, get_source, list_sources_catalog
from forense.app.sources.schema import normalize_record, validate_record
from forense.app.sources.sync import sync_source
from forense.app.sources.url_ingest import _host_allowed
from forense.app.sources.validate import validate_records


def test_sources_catalog_has_industries():
    cat = list_sources_catalog()
    assert len(cat["sources"]) >= 10
    assert "mineria" in cat["industries"]
    assert "portuario" in cat["industries"]
    assert "parking" in cat["industries"]
    assert "osha.gov" in cat["url_allowlist"]


def test_get_source_emcip():
    src = get_source("emcip_port")
    assert src is not None
    assert src["connector"] == "curated_json"


def test_sync_curated_sernageomin():
    result = sync_source("sernageomin_chile", limit=3, skip_existing=True)
    assert result.get("ok") is True
    assert result.get("imported", 0) >= 0


def test_sync_seeds_parking_pack():
    result = sync_source("seeds_parking", skip_existing=True)
    assert result.get("ok") is True
    assert result.get("imported", 0) >= 0


def test_validate_records_detects_short_description():
    out = validate_records(
        [{"title": "Test", "description": "corto", "industry": "mineria"}],
        check_duplicates=False,
    )
    assert out["invalid_count"] >= 1


def test_normalize_record_industry():
    rec = normalize_record({"title": "Caída en rampa de parking con vehículo retrocediendo", "description": "x" * 30, "industry": "parking"})
    assert rec["industry"] == "parking"


def test_url_allowlist():
    assert _host_allowed("https://www.osha.gov/pls/oshaweb/owadisp.show_document")
    assert _host_allowed("https://www.sernageomin.cl/accidentabilidad-minera/")
    assert not _host_allowed("https://evil.example.com/fake-osha")


def test_validate_record_ok():
    rec = normalize_record(
        {
            "title": "Proximidad montacargas",
            "description": "Descripción suficientemente larga para validación de biblioteca forense.",
            "industry": "bodega",
            "situation_type": "proximity",
        }
    )
    assert validate_record(rec) == []
