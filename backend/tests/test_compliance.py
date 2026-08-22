"""Cumplimiento: Hardhat del modelo cuenta como casco (case-insensitive)."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.compliance import evaluate, normalize_detections  # noqa: E402


class HardhatMappingTests(unittest.TestCase):
    def test_hardhat_maps_to_casco(self) -> None:
        dets = normalize_detections(
            [{"label": "Hardhat", "confidence": 0.7, "box": [10, 10, 80, 80]}]
        )
        self.assertEqual(dets[0].category, "casco")

    def test_construction_profile_counts_hardhat_and_vest(self) -> None:
        raw = [
            {"label": "Hardhat", "confidence": 0.8, "box": [40, 10, 90, 60]},
            {"label": "Safety Vest", "confidence": 0.7, "box": [20, 50, 120, 180]},
        ]
        result = evaluate(raw, "construccion")
        self.assertTrue(result.persons)
        self.assertIn("casco", result.persons[0].present)
        self.assertIn("chaleco", result.persons[0].present)
        self.assertTrue(result.overall_compliant)
        self.assertIn("Cumplimiento OK", result.summary)


if __name__ == "__main__":
    unittest.main()
