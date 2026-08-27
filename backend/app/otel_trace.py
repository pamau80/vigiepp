"""Trazas opcionales — logs locales o export OTLP (OpenTelemetry)."""

from __future__ import annotations

import logging
import os
import time
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

logger = logging.getLogger("vigiepp.trace")

_otel_service = os.getenv("VIGIEPP_OTEL_SERVICE", "vigiepp").strip() or "vigiepp"

_tracer: Any = None
_otlp_mode: str = "off"


def _otel_env_enabled() -> bool:
    return os.getenv("VIGIEPP_OTEL", "").strip().lower() in ("1", "true", "yes", "on")


def _otlp_endpoint() -> str:
    return os.getenv("VIGIEPP_OTEL_ENDPOINT", "").strip()


def _init_otel() -> None:
    global _tracer, _otlp_mode
    if _tracer is not None:
        return
    endpoint = _otlp_endpoint()
    if not _otel_env_enabled() and not endpoint:
        return
    try:
        from opentelemetry import trace
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor

        resource = Resource.create({"service.name": _otel_service})
        provider = TracerProvider(resource=resource)

        if _otlp_endpoint():
            try:
                from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter

                exporter = OTLPSpanExporter(endpoint=endpoint, insecure=True)
                provider.add_span_processor(BatchSpanProcessor(exporter))
                _otlp_mode = "otlp-grpc"
            except ImportError:
                from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter

                exporter = OTLPSpanExporter(endpoint=endpoint)
                provider.add_span_processor(BatchSpanProcessor(exporter))
                _otlp_mode = "otlp-http"

        trace.set_tracer_provider(provider)
        _tracer = trace.get_tracer("vigiepp")
        if _otlp_mode == "off" and not endpoint:
            _otlp_mode = "sdk-local"
        logger.info("OpenTelemetry activo · modo=%s endpoint=%s", _otlp_mode, endpoint or "local")
    except ImportError:
        _otlp_mode = "log-only"
        logger.warning("OpenTelemetry SDK no instalado; spans solo en logs (VIGIEPP_OTEL=1)")


def enabled() -> bool:
    return _otel_env_enabled() or bool(_otlp_endpoint())


def otlp_mode() -> str:
    _init_otel()
    return _otlp_mode


@contextmanager
def span(name: str, **attrs: Any) -> Iterator[None]:
    _init_otel()
    if _tracer is not None:
        with _tracer.start_as_current_span(name, attributes={k: str(v) for k, v in attrs.items()}):
            yield
        return
    if not _otel_env_enabled():
        yield
        return
    start = time.perf_counter()
    try:
        yield
        ms = (time.perf_counter() - start) * 1000.0
        logger.info("span %s ok %.1fms %s", name, ms, attrs)
    except Exception:
        ms = (time.perf_counter() - start) * 1000.0
        logger.warning("span %s error %.1fms %s", name, ms, attrs)
        raise
