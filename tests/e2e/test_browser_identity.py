"""E2E browser — identificar rostro enrolado."""

from __future__ import annotations

from playwright.sync_api import Page, expect

from tests.e2e.helpers import go_identity_tab, inject_fake_camera, ui_login


def test_browser_identify_known_worker(page: Page, face_jpeg_path, enrolled_worker: dict) -> None:
    inject_fake_camera(page, face_jpeg_path)
    ui_login(page)
    go_identity_tab(page)
    expect(page.locator("#workerList")).to_contain_text("E2E Lena Test", timeout=90000)

    page.locator("#btnIdentify").click(timeout=60000)
    expect(page.locator("#identityName")).not_to_have_text("Sin identificar", timeout=120000)
    identity_text = page.locator("#identityName").inner_text()
    assert "E2E" in identity_text or "Lena" in identity_text
