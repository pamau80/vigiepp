"""Tests almacén incremental de frames."""

from __future__ import annotations

from forense.app.frame_store import append_frame, clear_frames, count_frames, nearest_frame, read_frames


def _job_id() -> str:
    return "test-frame-store"


def test_frame_store_roundtrip(tmp_path, monkeypatch):
    monkeypatch.setattr("forense.app.frame_store.JOBS_DIR", tmp_path)
    jid = _job_id()
    clear_frames(jid)
    assert count_frames(jid) == 0

    rec1 = {"time_sec": 1.0, "time_label": "00:00:01", "counts": {"persons": 1, "vehicles": 0}}
    rec2 = {"time_sec": 2.5, "time_label": "00:00:02", "counts": {"persons": 2, "vehicles": 1}}
    append_frame(jid, rec1)
    append_frame(jid, rec2)
    assert count_frames(jid) == 2

    all_frames = read_frames(jid)
    assert len(all_frames) == 2
    assert all_frames[0]["time_sec"] == 1.0

    subset = read_frames(jid, from_sec=1.5, until_sec=3.0)
    assert len(subset) == 1
    assert subset[0]["time_sec"] == 2.5

    near = nearest_frame(jid, 2.4)
    assert near is not None
    assert near["time_sec"] == 2.5

    clear_frames(jid)
    assert count_frames(jid) == 0
