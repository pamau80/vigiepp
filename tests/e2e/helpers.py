"""Helpers UI para tests E2E browser."""

from __future__ import annotations

import json
import time
import urllib.request
from pathlib import Path

import cv2
import numpy as np
from playwright.sync_api import Page

E2E_PIN = "e2e-browser-pin"
E2E_OPERATOR_PIN = "e2e-operator-pin"


def ui_login(page: Page, pin: str = E2E_PIN) -> None:
    page.goto("/", wait_until="domcontentloaded", timeout=60000)
    page.wait_for_load_state("domcontentloaded")
    page.wait_for_function(
        """
        () => {
          const gate = document.getElementById('authGate');
          const logout = document.getElementById('btnLogout');
          if (!gate) return true;
          const needsLogin = !gate.classList.contains('hidden');
          const loggedIn = logout && !logout.classList.contains('hidden');
          return needsLogin || loggedIn;
        }
        """,
        timeout=30000,
    )
    if page.locator("#authGate").is_visible():
        page.locator("#authPin").fill(pin)
        page.locator("#authSubmit").click()
    page.wait_for_function(
        "() => document.getElementById('authGate')?.classList.contains('hidden')",
        timeout=30000,
    )


def go_identity_tab(page: Page) -> None:
    page.locator('.mode-btn[data-mode="identity"]').click()
    page.wait_for_function(
        "() => document.body.classList.contains('mode-identity')",
        timeout=30000,
    )
    page.wait_for_selector("#identityControls:not(.hidden)", timeout=30000)
    page.wait_for_selector("#btnIdentify", state="visible", timeout=30000)


def _face_jpeg_variants(face_path: Path, count: int = 4) -> list[bytes]:
    img = cv2.imread(str(face_path))
    if img is None:
        raise RuntimeError(f"No se pudo leer {face_path}")
    out: list[bytes] = []
    h, w = img.shape[:2]
    cx, cy = w / 2, h / 2

    def rot(m: np.ndarray, deg: float) -> np.ndarray:
        return cv2.warpAffine(
            m,
            cv2.getRotationMatrix2D((cx, cy), deg, 1.0),
            (w, h),
        )

    ops = [
        lambda m: m,
        lambda m: cv2.flip(m, 1),
        lambda m: rot(m, 14),
        lambda m: rot(m, -11),
        lambda m: rot(m, 22),
        lambda m: cv2.convertScaleAbs(m, alpha=1.12, beta=18),
        lambda m: cv2.convertScaleAbs(rot(m, 8), alpha=0.92, beta=-8),
        lambda m: cv2.warpAffine(
            m,
            np.float32([[1, 0, 12], [0, 1, -8]]),
            (w, h),
        ),
    ]
    for i in range(count):
        variant = ops[i % len(ops)](img.copy())
        ok, buf = cv2.imencode(".jpg", variant, [int(cv2.IMWRITE_JPEG_QUALITY), 92])
        if not ok:
            raise RuntimeError("imencode falló")
        out.append(buf.tobytes())
    return out


def _face_jpeg_variant_paths(face_path: Path, tmp_dir: Path, count: int = 4) -> list[Path]:
    tmp_dir.mkdir(parents=True, exist_ok=True)
    paths: list[Path] = []
    for idx, blob in enumerate(_face_jpeg_variants(face_path, count)):
        out = tmp_dir / f"face-{idx}.jpg"
        out.write_bytes(blob)
        paths.append(out)
    return paths


def enroll_worker_via_api(base_url: str, face_path: Path, name: str, rut: str, samples: int = 4) -> dict:
    login_req = urllib.request.Request(
        f"{base_url}/api/auth/login",
        data=json.dumps({"pin": E2E_PIN}).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(login_req, timeout=15) as resp:
        token = json.loads(resp.read().decode())["token"]

    jpeg_variants = _face_jpeg_variants(face_path, samples)
    boundary = f"----vigiepp{int(time.time() * 1000)}"
    parts: list[bytes] = []
    for field, val in (("name", name), ("rut", rut), ("consent", "true")):
        parts.append(f"--{boundary}\r\n".encode())
        parts.append(f'Content-Disposition: form-data; name="{field}"\r\n\r\n'.encode())
        parts.append(f"{val}\r\n".encode())
    for idx, jpeg in enumerate(jpeg_variants):
        parts.append(f"--{boundary}\r\n".encode())
        parts.append(f'Content-Disposition: form-data; name="files"; filename="face{idx}.jpg"\r\n'.encode())
        parts.append(b"Content-Type: image/jpeg\r\n\r\n")
        parts.append(jpeg)
        parts.append(b"\r\n")
    parts.append(f"--{boundary}--\r\n".encode())
    body = b"".join(parts)

    req = urllib.request.Request(
        f"{base_url}/api/identity/enroll-photos",
        data=body,
        headers={
            "Content-Type": f"multipart/form-data; boundary={boundary}",
            "X-VigiEPP-Key": token,
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=180) as resp:
        data = json.loads(resp.read().decode())
    if not data.get("ok"):
        raise RuntimeError(data)
    worker = data.get("worker") or {}
    if not worker.get("ready") and (worker.get("face_samples") or 0) < 2:
        raise RuntimeError(f"Enrolamiento insuficiente: {data.get('message') or data}")
    return data


E2E_FACE_URL = "/__e2e__/face.jpg"


def wait_camera_ready(page: Page, timeout_ms: int = 45000) -> None:
    page.wait_for_function(
        """
        () => {
          const v = document.getElementById('liveVideo');
          return v && v.videoWidth > 0 && v.videoHeight > 0;
        }
        """,
        timeout=timeout_ms,
    )


def start_fake_camera_ui(page: Page) -> None:
    """Modo Personas intenta abrir cámara al entrar; reintento con Iniciar si hace falta."""
    page.wait_for_timeout(800)
    btn = page.locator("#btnStartCam")
    if btn.is_visible() and btn.is_enabled():
        btn.click()
        page.wait_for_timeout(400)
