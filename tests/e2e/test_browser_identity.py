"""E2E browser — identificar rostro enrolado."""

from __future__ import annotations

from playwright.sync_api import Page, expect

from tests.e2e.helpers import go_identity_tab, start_fake_camera_ui, ui_login, wait_camera_ready, wait_identify_ready


def test_browser_identify_known_worker(page: Page, enrolled_worker: dict) -> None:
    ui_login(page)
    go_identity_tab(page)
    expect(page.locator("#workerList")).to_contain_text("E2E Lena Test", timeout=90000)
    start_fake_camera_ui(page)
    wait_camera_ready(page)
    chk = page.locator("#chkIdentify")
    if chk.is_visible() and not chk.is_checked():
        chk.check()
    wait_identify_ready(page)

    with page.expect_response(
        lambda r: "/api/identity/identify" in r.url and r.request.method == "POST",
        timeout=180000,
    ) as resp_info:
        page.evaluate("() => document.getElementById('btnIdentify')?.click()")
    resp = resp_info.value
    assert resp.ok, resp.text()
    payload = resp.json()
    assert payload.get("faces_detected", 0) >= 1, payload
    identified = payload.get("identified") or {}
    assert identified.get("id"), payload

    expect(page.locator("#identityName")).not_to_have_text("Sin identificar", timeout=30000)
    identity_text = page.locator("#identityName").inner_text()
    assert "E2E" in identity_text or "Lena" in identity_text
