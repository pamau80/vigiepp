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
    assert insights["boosted_events"] >= 1
    types = {e["type"] for e in job["analysis"]["timeline"]}
    assert "knowledge_match" in types


def test_reset_knowledge():
    create_knowledge(title="Temp", situation_type="other", industry="general")
    removed = reset_knowledge()
    assert removed == 1
    assert reset_knowledge() == 0
