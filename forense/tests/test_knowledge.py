"""Tests biblioteca de aprendizaje Forense."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from forense.app.knowledge import (
    apply_knowledge_insights,
    create_knowledge,
    match_knowledge_for_job,
    reset_knowledge,
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


def test_create_and_match_knowledge():
    import cv2

    img = np.zeros((64, 64, 3), dtype=np.uint8)
    img[10:50, 10:50] = (0, 200, 0)
    ok, buf = cv2.imencode(".jpg", img)
    assert ok

    entry = create_knowledge(
        title="Near miss montacargas",
        situation_type="near_miss",
        description="Operador cruzó sin mirar",
        industry="bodega",
        event_types=["proximity", "action"],
        labels=["critical"],
        media_bytes=buf.tobytes(),
        media_filename="ref.jpg",
    )
    assert entry["id"].startswith("kn-")

    job = {
        "id": "job1",
        "title": "Near miss montacargas",
        "case_notes": "Operador cruzó sin mirar en pasillo de bodega",
        "template_id": "bodega",
        "analysis": {
            "timeline": [
                {"type": "proximity", "severity": "critical", "message": "test"},
                {"type": "action", "severity": "high", "message": "test2"},
            ],
            "keyframes": [],
        },
    }
    matches = match_knowledge_for_job(job)
    assert len(matches) >= 1
    assert matches[0]["title"] == "Near miss montacargas"

    insights = apply_knowledge_insights(job, matches)
    assert (insights["boosted_events"] + insights.get("conjectures", 0)) >= 1
    types = {e["type"] for e in job["analysis"]["timeline"]}
    assert "knowledge_match" in types or "knowledge_conjecture" in types


def test_text_only_knowledge_match():
    create_knowledge(
        title="maniobra imprudente",
        situation_type="unsafe_act",
        description="grua de bajo tonelaje sortea entre gruas de alto tonelaje con bobina",
        industry="portuario",
    )
    job = {
        "id": "job2",
        "title": "Maniobra imprudente patio portuario",
        "case_notes": "grua de bajo tonelaje sortea entre gruas con bobina en muelle",
        "template_id": "portuario",
        "site": "Muelle",
        "analysis": {"timeline": [], "keyframes": []},
        "sources": [],
    }
    matches = match_knowledge_for_job(job)
    assert len(matches) >= 1
    assert matches[0]["title"] == "maniobra imprudente"


def test_generic_port_job_rejects_crane_hallucination():
    """Título genérico + video distinto no debe forzar coincidencias de grúas."""
    create_knowledge(
        title="maniobra imprudente",
        situation_type="unsafe_act",
        description="grua de bajo tonelaje sortea entre gruas de alto tonelaje con bobina",
        industry="portuario",
        source="user",
        source_id="test-crane-user",
    )
    create_knowledge(
        title="Acto inseguro camión basura",
        situation_type="unsafe_act",
        description="conductor camión retira basura LXHW32 sin señalizar",
        industry="portuario",
        source="seed",
        source_id="test-truck-seed",
    )
    job = {
        "id": "job-garbage",
        "title": "Análisis forense",
        "site": "Faena",
        "template_id": "portuario",
        "analysis": {"timeline": [], "keyframes": []},
        "sources": [{"path": "/nonexistent/garbage.avi"}],
    }
    matches = match_knowledge_for_job(job)
    strong = [m for m in matches if not m.get("conjecture")]
    assert not any("grua" in (m.get("title") or "").lower() or "grúa" in (m.get("title") or "").lower() for m in strong)


def test_case_notes_improves_truck_match():
    create_knowledge(
        title="Acto inseguro camión retira basura",
        situation_type="unsafe_act",
        description="conductor camión recolector LXHW32 retira basura sin señalizar en patio",
        industry="portuario",
        source="seed",
        source_id="test-truck-match",
    )
    job = {
        "id": "job2",
        "title": "Near-miss patio",
        "case_notes": "ACCION INSEGURA CONDUCTOR CAMION RETIRA BASURA LXHW32",
        "template_id": "portuario",
        "analysis": {"timeline": [], "keyframes": []},
        "sources": [],
    }
    matches = match_knowledge_for_job(job)
    assert len(matches) >= 1
    assert "basura" in (matches[0].get("title") or "").lower() or "camión" in (matches[0].get("title") or "").lower()


def test_reset_knowledge():
    create_knowledge(title="Temp", situation_type="other", industry="general")
    removed = reset_knowledge()
    assert removed == 1
    assert reset_knowledge() == 0
