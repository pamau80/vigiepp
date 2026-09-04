"""Tests formatos de video admitidos."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from forense.app.main import app
from forense.app.video_formats import (
    is_supported_video_filename,
    resolve_source_path,
    video_extension,
)


@pytest.mark.parametrize(
    "name",
    [
        "grabacion.avi",
        "camara.MP4",
        "nvr_export.mkv",
        "clip.mov",
        "dahua.dav",
        "stream.ts",
        "patrol.wmv",
        "video.h264",
    ],
)
def test_supported_extensions(name: str):
    assert is_supported_video_filename(name)
    assert video_extension(name) is not None


@pytest.mark.parametrize("name", ["malware.exe", "foto.jpg", "informe.pdf", "video.xyz"])
def test_rejects_unsupported(name: str):
    assert not is_supported_video_filename(name)


def test_resolve_source_path_finds_avi(tmp_path: Path):
    sources = tmp_path / "sources"
    sources.mkdir()
    avi = sources / "cam0.avi"
    avi.write_bytes(b"fake")
    assert resolve_source_path(sources, 0) == avi


def test_resolve_source_path_checks_all_extensions(tmp_path: Path):
    sources = tmp_path / "sources"
    sources.mkdir()
    for ext in (".dav", ".mts", ".3gp"):
        p = sources / f"cam1{ext}"
        p.write_bytes(b"x")
        assert resolve_source_path(sources, 1) == p
        p.unlink()


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("VIGIEPP_FORENSE", "1")
    monkeypatch.setenv("VIGIEPP_FORENSE_LICENSE", "dev")
    monkeypatch.setenv("VIGIEPP_AUTH", "1")
    monkeypatch.setenv("VIGIEPP_ADMIN_PIN", "vigiepp")
    return TestClient(app)


def _tiny_avi(path: Path) -> None:
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-f",
            "lavfi",
            "-i",
            "color=c=blue:s=160x120:d=0.3",
            "-c:v",
            "mpeg4",
            str(path),
        ],
        capture_output=True,
        check=True,
        timeout=60,
    )


@pytest.mark.skipif(
    not __import__("shutil").which("ffmpeg"),
    reason="ffmpeg no instalado",
)
def test_jobs_create_accepts_avi(client: TestClient, tmp_path, monkeypatch):
    monkeypatch.setattr("forense.app.jobs.JOBS_DIR", tmp_path)
    avi = tmp_path / "test.avi"
    _tiny_avi(avi)
    client.post("/api/forense/auth/login", json={"pin": "vigiepp"})
    with avi.open("rb") as f:
        res = client.post(
            "/api/forense/jobs",
            data={"title": "Caso AVI", "site": "Faena"},
            files={"video": ("export_nvr.avi", f, "video/x-msvideo")},
        )
    assert res.status_code == 200, res.text
    job_id = res.json()["job"]["id"]
    stored = tmp_path / job_id / "sources" / "cam0.avi"
    assert stored.is_file()
    assert stored.stat().st_size > 1000


def test_jobs_create_rejects_exe(client: TestClient):
    client.post("/api/forense/auth/login", json={"pin": "vigiepp"})
    res = client.post(
        "/api/forense/jobs",
        data={"title": "Mal", "site": "Faena"},
        files={"video": ("virus.exe", b"x" * 2000, "application/octet-stream")},
    )
    assert res.status_code == 400
    assert "formato no soportado" in res.json()["detail"].lower()
