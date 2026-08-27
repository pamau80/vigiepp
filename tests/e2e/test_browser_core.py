"""E2E browser — login, navegación y build."""

from __future__ import annotations

from pathlib import Path

from playwright.sync_api import Page, expect

from tests.e2e.helpers import go_identity_tab, ui_login


def test_browser_login_and_build(page: Page, base_url: str) -> None:
    ui_login(page)
    expect(page.locator("#btnLogout")).to_be_visible()

    health = page.request.get(f"{base_url}/api/health")
    assert health.ok
    build = health.json().get("build", "")
    assert build.startswith("v")


def test_browser_navigate_personas_tab(page: Page) -> None:
    ui_login(page)
    page.locator('.mode-btn[data-mode="identity"]').click()
    expect(page.locator("#workerName")).to_be_visible()
    expect(page.locator("#btnEnroll")).to_be_visible()
    expect(page.locator("#btnIdentify")).to_be_visible()
    expect(page.locator("#chkBiometricConsent")).to_be_visible()


def test_browser_enroll_photos_in_ui(page: Page, face_photo_paths: list[Path]) -> None:
    ui_login(page)
    go_identity_tab(page)

    page.locator("#workerName").fill("E2E UI Enroll")
    page.locator("#workerRut").fill("22.222.222-2")
    page.locator("#chkBiometricConsent").check()
    with page.expect_response(
        lambda r: "/api/identity/enroll-photos" in r.url and r.request.method == "POST",
        timeout=180000,
    ) as resp_info:
        page.locator("#faceTrainPhotos").set_input_files([str(p) for p in face_photo_paths])
    resp = resp_info.value
    assert resp.ok, resp.text()
    payload = resp.json()
    assert payload.get("ok"), payload
    expect(page.locator("#workerList")).to_contain_text("E2E UI Enroll", timeout=30000)
