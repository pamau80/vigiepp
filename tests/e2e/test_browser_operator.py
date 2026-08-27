"""E2E browser — operador / portería (monitoreo en vivo)."""

from __future__ import annotations

import re

from playwright.sync_api import Page, expect

from tests.e2e.helpers import E2E_OPERATOR_PIN, ui_login


def test_browser_operator_login_and_kiosk(page: Page, base_url: str) -> None:
    ui_login(page, pin=E2E_OPERATOR_PIN)

    assert page.evaluate("() => document.body.dataset.role") == "operator"
    expect(page.locator("#roleBadge")).to_have_text("Portería")
    expect(page.locator("body")).to_have_class(re.compile(r"kiosk-mode"))
    expect(page.locator("#kioskOverlay")).not_to_have_class("hidden")

    # Modo portería oculta la nav — solo vista kiosk + monitoreo
    nav_display = page.evaluate(
        "() => window.getComputedStyle(document.querySelector('.mode-nav')).display"
    )
    assert nav_display == "none"

    me = page.request.get(f"{base_url}/api/auth/me")
    assert me.ok
    assert me.json().get("role") == "operator"

    blocked = page.request.get(f"{base_url}/api/identity/workers")
    assert blocked.status == 403

    allowed = page.request.post(f"{base_url}/api/detect")
    assert allowed.status != 403
