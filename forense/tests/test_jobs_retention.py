"""Tests retención de trabajos y listado de cámaras."""

from __future__ import annotations

from pathlib import Path

import forense.app.jobs as jobs_mod


def test_list_video_cameras(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(jobs_mod, "JOBS_DIR", tmp_path / "jobs")
    job_id = "camtest01"
    src_dir = jobs_mod._job_dir(job_id) / "sources"
    src_dir.mkdir(parents=True)
    (src_dir / "cam0.mp4").write_bytes(b"fake")
    (src_dir / "cam1.mp4").write_bytes(b"fake")
    assert jobs_mod.list_video_cameras(job_id) == [0, 1]
