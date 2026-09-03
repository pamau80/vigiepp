"""Tests análisis visual IA de video."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

from forense.app.video_ai import (
    analyze_job_video_ai,
    nearest_video_caption,
    select_frames_for_vision,
    video_ai_enabled,
)


def test_video_ai_disabled(monkeypatch):
    monkeypatch.setenv("VIGIEPP_FORENSE_VIDEO_AI", "0")
    monkeypatch.setenv("VIGIEPP_FORENSE_OPENAI_KEY", "test")
    assert video_ai_enabled() is False


def test_select_frames_prefers_keyframes(tmp_path, monkeypatch):
    monkeypatch.setattr("forense.app.video_ai.JOBS_DIR", tmp_path)
    job_id = "job1"
    job = {
        "meta": {"duration_sec": 30},
        "analysis": {
            "keyframes": [
                {"time_sec": 5.0, "time_label": "00:00:05", "image": "kf_000.jpg"},
                {"time_sec": 12.0, "time_label": "00:00:12", "image": "kf_001.jpg"},
            ],
            "timeline": [
                {"time_sec": 20.0, "time_label": "00:00:20", "type": "proximity", "severity": "high"},
            ],
        },
    }
    picks = select_frames_for_vision(job, job_id)
    assert len(picks) >= 2
    assert picks[0]["source"] == "keyframe"


def test_analyze_job_video_ai_mocked(tmp_path, monkeypatch):
    monkeypatch.setattr("forense.app.video_ai.JOBS_DIR", tmp_path)
    monkeypatch.setenv("VIGIEPP_FORENSE_VIDEO_AI", "1")
    monkeypatch.setenv("VIGIEPP_FORENSE_OPENAI_KEY", "test-key")
    job_id = "job2"
    kf_dir = tmp_path / job_id / "keyframes"
    kf_dir.mkdir(parents=True)
    (kf_dir / "kf_000.jpg").write_bytes(b"\xff\xd8\xff fake jpeg")
    job = {
        "title": "Caso prueba",
        "site": "Faena",
        "meta": {"duration_sec": 10},
        "analysis": {
            "keyframes": [{"time_sec": 2.0, "time_label": "00:00:02", "image": "kf_000.jpg"}],
            "timeline": [],
        },
    }

    fake_resp = MagicMock()
    fake_resp.read.return_value = json.dumps(
        {"choices": [{"message": {"content": "Se observa una persona cerca de maquinaria en retroceso."}}]}
    ).encode()
    fake_resp.__enter__ = lambda s: s
    fake_resp.__exit__ = MagicMock(return_value=False)

    with patch("forense.app.video_ai.urllib.request.urlopen", return_value=fake_resp):
        result = analyze_job_video_ai(job, job_id)

    assert result["status"] in ("ok", "partial")
    assert result["frame_count"] >= 1
    assert "persona" in result["captions"][0]["caption"]
    assert result["summary"]


def test_nearest_video_caption():
    video_ai = {
        "captions": [
            {"time_sec": 5.0, "time_label": "00:00:05", "caption": "A"},
            {"time_sec": 15.0, "time_label": "00:00:15", "caption": "B"},
        ]
    }
    near = nearest_video_caption(video_ai, 5.3)
    assert near is not None
    assert near["caption"] == "A"
    assert nearest_video_caption(video_ai, 50.0) is None
