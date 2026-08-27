"""Fixtures compartidas para E2E browser (Playwright)."""

from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

import pytest

from tests.e2e.helpers import E2E_PIN, enroll_worker_via_api

ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "backend"
FACE_FIXTURE = ROOT / "tests" / "fixtures" / "lena.jpg"
Y4M_FIXTURE = ROOT / "tests" / "fixtures" / "lena.y4m"
E2E_DATA = ROOT / "tests" / "e2e" / "_runtime_data"
LENA_URL = "https://raw.githubusercontent.com/opencv/opencv/4.x/samples/data/lena.jpg"


def _free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _wait_health(url: str, timeout_s: float = 90.0) -> None:
    deadline = time.time() + timeout_s
    last_err: Exception | None = None
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(f"{url}/api/health", timeout=3) as resp:
                if resp.status == 200:
                    return
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            last_err = exc
        time.sleep(0.4)
    raise RuntimeError(f"Servidor E2E no respondió en {url}: {last_err}")


@pytest.fixture(scope="session")
def face_jpeg_path() -> Path:
    FACE_FIXTURE.parent.mkdir(parents=True, exist_ok=True)
    if not FACE_FIXTURE.exists() or FACE_FIXTURE.stat().st_size < 1000:
        urllib.request.urlretrieve(LENA_URL, FACE_FIXTURE)
    assert FACE_FIXTURE.exists(), "fixture lena.jpg no disponible"
    return FACE_FIXTURE


@pytest.fixture(scope="session")
def e2e_server_url(face_jpeg_path) -> str:
    del face_jpeg_path
    data_dir = E2E_DATA
    data_dir.mkdir(parents=True, exist_ok=True)
    for p in data_dir.iterdir():
        if p.is_file():
            p.unlink(missing_ok=True)

    port = _free_port()
    env = os.environ.copy()
    env["PYTHONPATH"] = str(BACKEND)
    env["VIGIEPP_DATA_DIR"] = str(data_dir)
    env["VIGIEPP_AUTH"] = "1"
    env["VIGIEPP_ADMIN_PIN"] = E2E_PIN
    env["VIGIEPP_OPERATOR_PIN"] = "e2e-operator-pin"
    env["VIGIEPP_COMBINED_INFERENCE"] = "0"

    venv_python = ROOT / ".venv" / "bin" / "python"
    python = str(venv_python if venv_python.exists() else sys.executable)
    proc = subprocess.Popen(
        [
            python,
            "-m",
            "uvicorn",
            "app.main:app",
            "--host",
            "127.0.0.1",
            "--port",
            str(port),
        ],
        cwd=str(BACKEND),
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
    )
    base = f"http://127.0.0.1:{port}"
    try:
        _wait_health(base)
        deadline = time.time() + 180
        while time.time() < deadline:
            with urllib.request.urlopen(f"{base}/api/health", timeout=5) as resp:
                payload = json.loads(resp.read().decode())
            if payload.get("identity_ready"):
                break
            time.sleep(1)
        else:
            raise RuntimeError("identity_ready no alcanzado en servidor E2E")
        yield base
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=15)
        except subprocess.TimeoutExpired:
            proc.kill()


@pytest.fixture(scope="session")
def base_url(e2e_server_url: str) -> str:
    return e2e_server_url


@pytest.fixture(scope="session")
def face_video_path(face_jpeg_path: Path) -> Path:
    """Video Y4M para cámara fake de Chromium (--use-file-for-fake-video-capture)."""
    if Y4M_FIXTURE.exists() and Y4M_FIXTURE.stat().st_mtime >= face_jpeg_path.stat().st_mtime:
        return Y4M_FIXTURE
    Y4M_FIXTURE.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-loop",
            "1",
            "-i",
            str(face_jpeg_path),
            "-t",
            "12",
            "-vf",
            "scale=640:480",
            "-pix_fmt",
            "yuv420p",
            "-f",
            "yuv4mpegpipe",
            str(Y4M_FIXTURE),
        ],
        check=True,
        capture_output=True,
    )
    return Y4M_FIXTURE


@pytest.fixture(scope="session")
def browser_type_launch_args(face_video_path: Path):
    return {
        "headless": True,
        "args": [
            "--use-fake-device-for-media-stream",
            "--use-fake-ui-for-media-stream",
            f"--use-file-for-fake-video-capture={face_video_path}",
        ],
    }


@pytest.fixture(scope="session")
def face_photo_paths(face_jpeg_path: Path, tmp_path_factory) -> list[Path]:
    tmp = tmp_path_factory.mktemp("e2e-faces")
    from tests.e2e.helpers import _face_jpeg_variant_paths

    return _face_jpeg_variant_paths(face_jpeg_path, tmp, count=4)


@pytest.fixture(scope="session")
def enrolled_worker(e2e_server_url: str, face_jpeg_path: Path) -> dict:
    name = "E2E Lena Test"
    rut = "11.111.111-1"
    result = enroll_worker_via_api(e2e_server_url, face_jpeg_path, name, rut, samples=8)
    assert result.get("ok"), result
    return {"name": name, "rut": rut, "api": result}
