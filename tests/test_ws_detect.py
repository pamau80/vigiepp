"""Tests WebSocket /ws/detect."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def ws_client(tmp_path, monkeypatch):
    monkeypatch.setenv("VIGIEPP_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("VIGIEPP_AUTH", "0")
    from app.main import app

    return TestClient(app)


def test_ws_detect_config_message(ws_client):
    with ws_client.websocket_connect("/ws/detect") as ws:
        ws.send_text('{"profile":"portuario","conf":0.4}')
        msg = ws.receive_json()
        assert msg.get("ok") is True
        assert msg.get("type") == "config"
        assert msg.get("profile") == "portuario"


def test_ws_detect_rejects_pin_bearer(tmp_path, monkeypatch):
    monkeypatch.setenv("VIGIEPP_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("VIGIEPP_AUTH", "1")
    monkeypatch.setenv("VIGIEPP_ADMIN_PIN", "ws-audit-pin")
    from app.main import app

    client = TestClient(app)
    with pytest.raises(Exception):  # noqa: B017 — Starlette cierra con 4401
        with client.websocket_connect(
            "/ws/detect",
            headers={"X-VigiEPP-Key": "ws-audit-pin"},
        ) as ws:
            ws.send_text('{"profile":"general"}')


def test_ws_detect_accepts_session_token(tmp_path, monkeypatch):
    monkeypatch.setenv("VIGIEPP_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("VIGIEPP_AUTH", "1")
    monkeypatch.setenv("VIGIEPP_ADMIN_PIN", "ws-session-pin")
    from app.main import app

    client = TestClient(app)
    login = client.post("/api/auth/login", json={"pin": "ws-session-pin"})
    token = login.json()["token"]
    with client.websocket_connect("/ws/detect", headers={"X-VigiEPP-Key": token}) as ws:
        ws.send_text('{"profile":"general","conf":0.35}')
        msg = ws.receive_json()
        assert msg.get("ok") is True
