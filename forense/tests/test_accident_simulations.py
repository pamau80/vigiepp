"""Valida fixtures de simulaciones de accidente."""

from __future__ import annotations

import json
from pathlib import Path

import cv2

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "accident_simulations"
MANIFEST = FIXTURES / "manifest.json"


def test_accident_simulation_manifest():
    data = json.loads(MANIFEST.read_text(encoding="utf-8"))
    scenes = data.get("scenes") or []
    assert len(scenes) >= 7
    ids = {s["id"] for s in scenes}
    assert "sim_atropello" in ids
    assert "sim_caida_altura" in ids
    assert "sim_maniobra_temeraria" in ids


def test_accident_simulation_images_readable():
    scenes = json.loads(MANIFEST.read_text(encoding="utf-8"))["scenes"]
    for scene in scenes:
        img_path = FIXTURES / scene["file"]
        assert img_path.is_file(), scene["file"]
        img = cv2.imread(str(img_path))
        assert img is not None
        assert img.shape[0] >= 400
        assert img.shape[1] >= 640
