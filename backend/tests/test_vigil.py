"""Zonas por cámara y análisis de conducta."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app import zones as zones_mod  # noqa: E402
from app.behavior import evaluate_behavior  # noqa: E402


class ZonesPerCameraTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmpdir = tempfile.TemporaryDirectory()
        zones_mod.DATA_DIR = Path(self._tmpdir.name)
        zones_mod.ZONES_FILE = zones_mod.DATA_DIR / "zones.json"
        zones_mod._ensure()

    def tearDown(self) -> None:
        self._tmpdir.cleanup()

    def test_save_and_load_per_camera(self) -> None:
        cam = "cam123"
        zones_mod.save_zones(
            [{"name": "Acceso", "type": "restricted", "enabled": True, "x": 0.1, "y": 0.1, "w": 0.3, "h": 0.3}],
            camera_id=cam,
        )
        data = zones_mod.get_zones(cam)
        self.assertEqual(data["camera_id"], cam)
        self.assertEqual(data["source"], "camera")
        self.assertEqual(len(data["zones"]), 1)
        self.assertEqual(data["zones"][0]["name"], "Acceso")

    def test_camera_falls_back_to_global(self) -> None:
        zones_mod.save_zones(
            [{"name": "Global", "type": "restricted", "enabled": True, "x": 0, "y": 0, "w": 0.2, "h": 0.2}],
        )
        data = zones_mod.get_zones("sin-zonas-propias")
        self.assertEqual(data["source"], "global_fallback")
        self.assertEqual(data["zones"][0]["name"], "Global")

    def test_legacy_migration(self) -> None:
        legacy = {"zones": [{"name": "Legacy", "type": "restricted", "enabled": True, "x": 0, "y": 0, "w": 0.5, "h": 0.5}]}
        zones_mod.ZONES_FILE.write_text(json.dumps(legacy), encoding="utf-8")
        data = zones_mod.get_zones()
        self.assertEqual(data["zones"][0]["name"], "Legacy")


class BehaviorTests(unittest.TestCase):
    def test_fall_alert(self) -> None:
        dets = [{"label": "Fall-Detected", "category": "caida", "confidence": 0.8, "box": [0, 0, 50, 50]}]
        out = evaluate_behavior(dets, frame_w=640, frame_h=480)
        self.assertEqual(out["severity"], "critical")
        self.assertTrue(any("Caída" in a for a in out["alerts"]))

    def test_fight_overlap(self) -> None:
        dets = [
            {"label": "Person", "category": "persona", "box": [100, 100, 200, 300]},
            {"label": "Person", "category": "persona", "box": [130, 120, 230, 320]},
        ]
        out = evaluate_behavior(dets, frame_w=640, frame_h=480)
        self.assertIn(out["severity"], ("high", "medium"))
        types = {e["type"] for e in out["events"]}
        self.assertTrue(types & {"pelea_probable", "proximidad_agresiva"})


if __name__ == "__main__":
    unittest.main()
