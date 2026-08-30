"""E2E browser — pestaña Acciones (v62 P2)."""

from __future__ import annotations

from playwright.sync_api import Page, expect

from tests.e2e.helpers import ui_login


def test_browser_actions_tab(page: Page) -> None:
    ui_login(page)
    page.locator('.mode-btn[data-mode="actions"]').click()
    expect(page.locator("#actionsDesk")).to_be_visible()
    expect(page.locator("#actionsRuleList")).to_be_visible()
    expect(page.locator("#actionsEventList")).to_be_visible()
    expect(page.locator("#actionsAudioEnabled")).to_be_visible()

    events = page.request.get("/api/actions/events?limit=5")
    assert events.ok
    body = events.json()
    assert body.get("ok") is True
    assert "events" in body

    rules = page.request.get("/api/actions/rules")
    assert rules.ok
    payload = rules.json()
    assert isinstance(payload.get("rules"), list)
    settings = payload.get("settings") or {}
    assert "action_audio_enabled" in settings
    assert "action_audio_severities" in settings
