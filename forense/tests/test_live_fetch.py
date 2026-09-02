"""Tests conectores live HTML."""

from __future__ import annotations

from forense.app.sources.live_fetch import extract_records_from_html, fetch_live_records


SAMPLE_HTML = """
<html><body>
<h2>Accidentabilidad en faenas mineras</h2>
<p>Los atropellos por equipos de acarreo en retroceso representan un porcentaje relevante de fatalidades en minería a rajo abierto.</p>
<li>Caída de roca en frentes sin inspección geomecánica previa constituye riesgo crítico en operaciones subterráneas y a cielo abierto.</li>
</body></html>
"""


def test_extract_records_from_html():
    records = extract_records_from_html(
        SAMPLE_HTML,
        source="sernageomin",
        industry="mineria",
        url="https://www.sernageomin.cl/test",
        limit=5,
    )
    assert len(records) >= 2
    assert records[0]["industry"] == "mineria"
    assert records[0]["source"] == "sernageomin"


def test_fetch_live_unknown_source():
    out = fetch_live_records("no_existe")
    assert out["ok"] is False
    assert out["records"] == []
