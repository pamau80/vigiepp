"""Tests almacén OIDC state (memoria / Redis)."""

from __future__ import annotations

import time

from app.oidc_state import MemoryStateStore, store_state, validate_and_consume


def test_oidc_state_memory_roundtrip():
    store = MemoryStateStore()
    store.put("state-abc", time.time())
    assert store.pop_if_valid("state-abc") is True
    assert store.pop_if_valid("state-abc") is False


def test_oidc_state_module_helpers():
    store_state("helper-state")
    assert validate_and_consume("helper-state") is True
    assert validate_and_consume("helper-state") is False
