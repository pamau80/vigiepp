"""Contexto epp vs vigil en respuestas API."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.main import _build_response  # noqa: E402


class ContextSplitTests(unittest.TestCase):
    def test_epp_context_excludes_behavior_alerts(self) -> None:
        dets = [
            {"label": "Person", "category": "persona", "confidence": 0.9, "box": [100, 100, 200, 300]},
            {"label": "Person", "category": "persona", "confidence": 0.9, "box": [130, 120, 230, 320]},
        ]
        payload = _build_response(dets, None, "general", frame_wh=(640, 480), context="epp")
        self.assertEqual(payload["context"], "epp")
        self.assertEqual(payload["behavior"]["severity"], "ok")
        self.assertEqual(payload["zones"]["alerts"], [])
        self.assertIsNone(payload.get("identity"))

    def test_vigil_context_includes_behavior(self) -> None:
        dets = [
            {"label": "Person", "category": "persona", "confidence": 0.9, "box": [100, 100, 200, 300]},
            {"label": "Person", "category": "persona", "confidence": 0.9, "box": [130, 120, 230, 320]},
        ]
        payload = _build_response(dets, None, "general", frame_wh=(640, 480), context="vigil")
        self.assertEqual(payload["context"], "vigil")
        self.assertIsNone(payload["identity"])
        self.assertIn(payload["behavior"]["severity"], ("high", "medium"))


if __name__ == "__main__":
    unittest.main()
