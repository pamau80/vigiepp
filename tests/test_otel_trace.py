"""OpenTelemetry span helper."""

from __future__ import annotations


def test_otel_disabled_by_default():
    from app.otel_trace import enabled, otlp_mode

    assert enabled() is False
    assert otlp_mode() == "off"


def test_otel_log_mode(monkeypatch):
    monkeypatch.setenv("VIGIEPP_OTEL", "1")
    from app import otel_trace

    otel_trace._tracer = None
    otel_trace._otlp_mode = "off"
    assert otel_trace.enabled()
    assert otel_trace.otlp_mode() in ("log-only", "otlp-grpc", "otlp-http", "sdk-local", "off")
