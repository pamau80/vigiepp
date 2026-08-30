"""Almacén de state OIDC — memoria local o Redis (multi-worker)."""

from __future__ import annotations

import logging
import os
import time
from typing import Protocol

logger = logging.getLogger("vigiepp.oidc_state")

_STATE_TTL = 600.0
_PREFIX = "vigiepp:oidc:state:"


class StateStore(Protocol):
    def put(self, state: str, expires_at: float) -> None: ...
    def pop_if_valid(self, state: str) -> bool: ...


class MemoryStateStore:
    def __init__(self) -> None:
        self._pending: dict[str, float] = {}

    def _purge(self) -> None:
        now = time.time()
        for k, ts in list(self._pending.items()):
            if now - ts > _STATE_TTL:
                self._pending.pop(k, None)

    def put(self, state: str, expires_at: float) -> None:
        self._purge()
        self._pending[state] = expires_at

    def pop_if_valid(self, state: str) -> bool:
        if not state:
            return False
        self._purge()
        ts = self._pending.get(state)
        if ts is None:
            return False
        if time.time() - ts > _STATE_TTL:
            self._pending.pop(state, None)
            return False
        self._pending.pop(state, None)
        return True


class RedisStateStore:
    def __init__(self, url: str) -> None:
        import redis

        self._client = redis.from_url(url, decode_responses=True)
        self._ttl = int(_STATE_TTL)

    def put(self, state: str, expires_at: float) -> None:
        self._client.setex(f"{_PREFIX}{state}", self._ttl, str(expires_at))

    def pop_if_valid(self, state: str) -> bool:
        if not state:
            return False
        key = f"{_PREFIX}{state}"
        raw = self._client.get(key)
        if not raw:
            return False
        self._client.delete(key)
        try:
            ts = float(raw)
        except ValueError:
            return False
        return not time.time() - ts > _STATE_TTL


_store: StateStore | None = None


def _redis_url() -> str:
    return os.getenv("VIGIEPP_OIDC_STATE_REDIS_URL", "").strip() or os.getenv(
        "VIGIEPP_REDIS_URL", ""
    ).strip()


def get_store() -> StateStore:
    global _store
    if _store is not None:
        return _store
    url = _redis_url()
    if url:
        try:
            _store = RedisStateStore(url)
            logger.info("OIDC state: Redis (%s)", url.split("@")[-1])
            return _store
        except Exception:
            logger.exception("OIDC Redis no disponible — fallback memoria")
    _store = MemoryStateStore()
    return _store


def store_state(state: str) -> None:
    get_store().put(state, time.time())


def validate_and_consume(state: str) -> bool:
    return get_store().pop_if_valid(state)
