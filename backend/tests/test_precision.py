"""Precisión: umbrales por clase, NMS y casco vs SIN casco."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.compliance import evaluate  # noqa: E402
from app.precision import refine_detections, resolve_pos_neg_conflicts  # noqa: E402


class RefineTests(unittest.TestCase):
    def test_drops_low_conf_negative(self) -> None:
        dets = [
            {
                "label": "NO-Hardhat",
                "category": "sin_casco",
                "confidence": 0.32,
                "box": [10, 10, 80, 80],
            }
        ]
        out = refine_detections(dets, 200, 200, precision="alta")
        self.assertEqual(out, [])

    def test_keeps_hardhat_in_alta(self) -> None:
        dets = [
            {
                "label": "Hardhat",
                "category": "casco",
                "confidence": 0.42,
                "box": [40, 10, 90, 55],
            }
        ]
        out = refine_detections(dets, 200, 200, precision="alta")
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0]["category"], "casco")

    def test_positive_wins_conflict(self) -> None:
        dets = [
            {
                "label": "Hardhat",
                "category": "casco",
                "confidence": 0.62,
                "box": [40, 10, 90, 50],
            },
            {
                "label": "NO-Hardhat",
                "category": "sin_casco",
                "confidence": 0.55,
                "box": [42, 12, 88, 48],
            },
        ]
        out = resolve_pos_neg_conflicts(dets)
        cats = {d["category"] for d in out}
        self.assertIn("casco", cats)
        self.assertNotIn("sin_casco", cats)


class SpatialTests(unittest.TestCase):
    def test_helmet_and_vest_on_person(self) -> None:
        raw = [
            {"label": "Person", "confidence": 0.8, "box": [20, 10, 120, 220]},
            {"label": "Hardhat", "confidence": 0.7, "box": [45, 12, 95, 55]},
            {"label": "Safety Vest", "confidence": 0.7, "box": [30, 70, 110, 160]},
        ]
        result = evaluate(raw, "construccion")
        self.assertTrue(result.overall_compliant)
        self.assertIn("casco", result.persons[0].present)
        self.assertIn("chaleco", result.persons[0].present)

    def test_helmet_far_from_person_does_not_count(self) -> None:
        raw = [
            {"label": "Person", "confidence": 0.8, "box": [10, 10, 80, 200]},
            {"label": "Hardhat", "confidence": 0.9, "box": [300, 10, 340, 50]},
            {"label": "Safety Vest", "confidence": 0.8, "box": [20, 70, 70, 140]},
        ]
        result = evaluate(raw, "construccion")
        self.assertNotIn("casco", result.persons[0].present)
        self.assertFalse(result.overall_compliant)


if __name__ == "__main__":
    unittest.main()
