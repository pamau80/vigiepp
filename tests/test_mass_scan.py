"""Tests del módulo mass_scan (sin RTSP real)."""

from __future__ import annotations

import threading
from unittest.mock import MagicMock, patch

import numpy as np
from app.mass_scan import run_mass_scan


def _fake_build_response(detections, annotated_jpeg, profile, frame_wh=None, required=None, source_id="live"):
    return {
        "compliance": {
            "overall_compliant": True,
            "alerts": [],
            "persons": [{"missing": []}],
        },
        "actions": {"triggered": [], "alerts": []},
        "safety_score": 100,
    }


def _fake_compliance(payload):
    comp = payload.get("compliance") or {}
    missing: list[str] = []
    for p in comp.get("persons") or []:
        missing.extend(p.get("missing") or [])
    return {
        "compliant": comp.get("overall_compliant"),
        "missing": missing,
        "alerts": comp.get("alerts") or [],
        "actions": (payload.get("actions") or {}).get("triggered") or [],
    }


def test_run_mass_scan_empty_channels():
    result = run_mass_scan(
        [],
        profile="general",
        conf=0.35,
        required="",
        validate_rtsp_url=lambda u: u,
        detect_lock=threading.Lock(),
        detect_imgsz_max=640,
        build_response=_fake_build_response,
        compliance_cell_fields=_fake_compliance,
        thumb_b64=lambda f: "thumb",
    )
    assert result["ok"] is True
    assert result["cells"] == []
    assert result["summary"]["total"] == 0


def test_run_mass_scan_with_mocked_frame():
    frame = np.zeros((120, 160, 3), dtype=np.uint8)
    channels = [{"id": "c1", "name": "Cam 1", "url": "rtsp://fake/stream", "enabled": True}]
    mock_stream = MagicMock()
    mock_stream.read.return_value = frame
    mock_stream.connected = True
    mock_stream.last_error = None
    mock_det = MagicMock()
    mock_det.predict.return_value = ([], None)

    with (
        patch("app.mass_scan.get_or_create_stream", return_value=mock_stream),
        patch("app.mass_scan.PPEDetector.get", return_value=mock_det),
    ):
        result = run_mass_scan(
            channels,
            profile="general",
            conf=0.35,
            required="",
            validate_rtsp_url=lambda u: u,
            detect_lock=threading.Lock(),
            detect_imgsz_max=640,
            build_response=_fake_build_response,
            compliance_cell_fields=_fake_compliance,
            thumb_b64=lambda f: "thumb-b64",
        )

    assert result["ok"] is True
    assert len(result["cells"]) == 1
    cell = result["cells"][0]
    assert cell["ok"] is True
    assert cell["connected"] is True
    assert cell["compliant"] is True
    assert cell["thumb"] == "thumb-b64"
    mock_det.predict.assert_called_once()
