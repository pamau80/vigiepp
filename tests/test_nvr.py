"""Tests URLs RTSP NVR/DVR."""

from __future__ import annotations

from app.nvr import build_channel_url, dahua_rtsp, hikvision_rtsp, uniview_rtsp


def test_hikvision_rtsp_main():
    url = hikvision_rtsp("192.168.1.64", 1, username="admin", password="pass", port=554, subtype=0)
    assert url.startswith("rtsp://")
    assert "192.168.1.64" in url
    assert "Streaming" in url


def test_dahua_rtsp():
    url = dahua_rtsp("10.0.0.5", 3, username="user", password="pwd", port=554, subtype=1)
    assert "cam/realmonitor" in url
    assert "channel=3" in url


def test_uniview_rtsp():
    url = uniview_rtsp("10.0.0.8", 2, username="u", password="p", port=554, subtype=0)
    assert "unicast" in url


def test_build_channel_url_hikvision():
    url = build_channel_url(
        "hikvision",
        host="192.168.1.1",
        port=554,
        username="a",
        password="b",
        channel=1,
        subtype=0,
    )
    assert url and "rtsp://" in url
