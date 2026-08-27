"""Trazas opcionales (OpenTelemetry-ready) — spans locales en logs."""

from __future__ import annotations

import logging
import os
import time
from contextlib import contextmanager
from typing import Any, Iterator

logger = logging.getLogger("vigiepp.trace")

_enabled = os.getenv("VIGIEPP_OTEL", "").strip().lower() in ("1", "true", "yes", "on")


def enabled() -> bool:
    return _enabled


@contextmanager
def span(name: str, **attrs: Any) -> Iterator[None]:
    if not _enabled:
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
