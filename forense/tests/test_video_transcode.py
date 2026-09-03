"""Tests transcodificación para reproducción web."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from forense.app.jobs import ensure_web_playback, has_job_video, job_source_video_path, job_video_path
from forense.app.main import app
from forense.app.video_transcode import needs_browser_transcode, transcode_for_browser, web_playback_path


def _ffmpeg_available() -> bool:
    return bool(shutil.which("ffmpeg") and shutil.which("ffprobe"))


def _make_h264_mp4(path: Path, duration_sec: float = 0.5) -> None:
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-f",
            "lavfi",
            "-i",
            "color=c=blue:s=160x120:d=" + str(duration_sec),
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-movflags",
            "+faststart",
            str(path),
        ],
        capture_output=True,
        check=True,
        timeout=60,
    )


@pytest.mark.skipif(not _ffmpeg_available(), reason="ffmpeg no instalado")
def test_needs_browser_transcode_h264_mp4(tmp_path: Path):
    mp4 = tmp_path / "cam0.mp4"
    _make_h264_mp4(mp4)
    assert needs_browser_transcode(mp4) is False


@pytest.mark.skipif(not _ffmpeg_available(), reason="ffmpeg no instalado")
def test_web_playback_transcodes_non_browser_codec(tmp_path: Path):
    src = tmp_path / "cam0.avi"
    # Generar HEVC en contenedor AVI (mismo patrón que cámaras NVR)
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-f",
            "lavfi",
            "-i",
            "color=c=red:s=160x120:d=0.4",
            "-c:v",
            "libx265",
            "-tag:v",
            "hvc1",
            str(src),
        ],
        capture_output=True,
        check=True,
        timeout=90,
    )
    assert needs_browser_transcode(src) is True
    web = web_playback_path(tmp_path, cam=0)
    assert web is not None
    assert web.name == "cam0_web.mp4"
    assert web.is_file()
    assert needs_browser_transcode(web) is False


@pytest.mark.skipif(not _ffmpeg_available(), reason="ffmpeg no instalado")
def test_job_video_path_integration(tmp_path, monkeypatch):
    monkeypatch.setattr("forense.app.jobs.JOBS_DIR", tmp_path)
    job_id = "aabbccdd0011"
    sources = tmp_path / job_id / "sources"
    sources.mkdir(parents=True)
    (tmp_path / job_id / "job.json").write_text("{}", encoding="utf-8")
    src = sources / "cam0.avi"
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-f",
            "lavfi",
            "-i",
            "color=c=green:s=160x120:d=1.0",
            "-c:v",
            "mpeg4",
            str(src),
        ],
        capture_output=True,
        check=True,
        timeout=90,
    )
    assert has_job_video(job_id)
    assert job_source_video_path(job_id) == src
    web = ensure_web_playback(job_id)
    assert web is not None
    assert web.suffix == ".mp4"
    assert job_video_path(job_id) == web


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("VIGIEPP_FORENSE", "1")
    monkeypatch.setenv("VIGIEPP_FORENSE_LICENSE", "dev")
    monkeypatch.setenv("VIGIEPP_AUTH", "1")
    monkeypatch.setenv("VIGIEPP_ADMIN_PIN", "vigiepp")
    return TestClient(app)


@pytest.mark.skipif(not _ffmpeg_available(), reason="ffmpeg no instalado")
def test_jobs_video_endpoint_serves_mp4(client: TestClient, tmp_path, monkeypatch):
    monkeypatch.setattr("forense.app.jobs.JOBS_DIR", tmp_path)
    job_id = "ccddeeff0022"
    job_dir = tmp_path / job_id
    sources = job_dir / "sources"
    sources.mkdir(parents=True)
    (job_dir / "job.json").write_text('{"id":"ccddeeff0022"}', encoding="utf-8")
    mp4 = sources / "cam0.mp4"
    _make_h264_mp4(mp4)

    client.post("/api/forense/auth/login", json={"pin": "vigiepp"})
    res = client.get(f"/api/forense/jobs/{job_id}/video")
    assert res.status_code == 200
    assert res.headers.get("content-type", "").startswith("video/mp4")
    assert len(res.content) > 1000
