"""E2E browser — operador / portería (monitoreo en vivo)."""

from __future__ import annotations

import re

from playwright.sync_api import Page, expect

from tests.e2e.helpers import E2E_OPERATOR_PIN, E2E_PIN, ui_login


def test_browser_operator_login_and_kiosk(page: Page, base_url: str) -> None:
    ui_login(page, pin=E2E_OPERATOR_PIN)

    assert page.evaluate("() => document.body.dataset.role") == "operator"
    expect(page.locator("#roleBadge")).to_have_text("Portería")
    expect(page.locator("body")).to_have_class(re.compile(r"kiosk-mode"))
    expect(page.locator("#kioskOverlay")).not_to_have_class("hidden")

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


def test_browser_operator_exit_kiosk_with_admin_pin(page: Page, base_url: str) -> None:
    ui_login(page, pin=E2E_OPERATOR_PIN)
    expect(page.locator("#kioskOverlay")).not_to_have_class("hidden")

    def on_dialog(dialog) -> None:
        if dialog.type == "prompt":
            dialog.accept(E2E_PIN)
        else:
            dialog.accept()

    page.on("dialog", on_dialog)
    page.locator("#btnKioskExit").click()

    expect(page.locator("body")).not_to_have_class(re.compile(r"kiosk-mode"))
    expect(page.locator("#kioskOverlay")).to_be_hidden()
    expect(page.locator("#roleBadge")).to_be_hidden()
    expect(page.locator('.mode-btn[data-mode="identity"]')).to_be_visible()

    me = page.request.get(f"{base_url}/api/auth/me")
    assert me.ok
    assert me.json().get("role") == "admin"
