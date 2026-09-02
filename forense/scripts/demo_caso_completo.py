#!/usr/bin/env python3
"""Demo end-to-end Forense: biblioteca → análisis → informe.

Uso (con Forense en :8001):
  PYTHONPATH=backend:forense python forense/scripts/demo_caso_completo.py

Variables:
  FORENSE_URL   (default http://127.0.0.1:8001)
  FORENSE_PIN   (default vigiepp)
"""

from __future__ import annotations

import os
import sys
import tempfile
import time
from pathlib import Path

import cv2
import httpx
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
BASE = os.getenv("FORENSE_URL", "http://127.0.0.1:8001").rstrip("/")
PIN = os.getenv("FORENSE_PIN", "vigiepp")
POLL_SEC = 2
MAX_WAIT_SEC = int(os.getenv("FORENSE_DEMO_TIMEOUT", "180"))


def _fail(msg: str) -> None:
    print(f"[demo] ERROR: {msg}", file=sys.stderr)
    sys.exit(1)


def make_demo_video(path: Path, seconds: float = 4.0, fps: float = 10.0) -> None:
    """Video sintético estilo patio: rectángulo (vehículo) + persona."""
    w, h = 640, 360
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(str(path), fourcc, fps, (w, h))
    if not writer.isOpened():
        _fail("No se pudo crear video demo (OpenCV VideoWriter)")
    frames = int(seconds * fps)
    for i in range(frames):
        frame = np.full((h, w, 3), 48, dtype=np.uint8)
        # Líneas de patio
        cv2.line(frame, (0, h // 2), (w, h // 2), (70, 70, 70), 2)
        cv2.putText(frame, "DEMO PATIO CCTV", (12, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (200, 200, 200), 2)
        # Vehículo retrocediendo
        vx = w - 80 - int(i * 3.5)
        cv2.rectangle(frame, (vx, h // 2 + 20), (vx + 70, h // 2 + 55), (0, 140, 255), -1)
        # Peatón
        px = 120 + int(i * 1.2)
        cv2.circle(frame, (px, h // 2 + 70), 12, (80, 220, 120), -1)
        writer.write(frame)
    writer.release()
    if path.stat().st_size < 1000:
        _fail("Video demo demasiado pequeño")


def run_demo() -> None:
    print("=== VigiEPP Forense — demo caso completo ===")
    print(f"URL: {BASE}")

    with httpx.Client(base_url=BASE, timeout=120.0) as client:
        health = client.get("/api/forense/health")
        if health.status_code != 200:
            _fail(f"Health falló ({health.status_code})")
        build = health.json().get("build", "?")
        print(f"[1/6] Health OK · build {build}")

        login = client.post("/api/forense/auth/login", json={"pin": PIN})
        if login.status_code != 200:
            _fail(f"Login falló ({login.status_code}): {login.text}")
        token = login.json().get("token") or ""
        headers = {"X-VigiEPP-Key": token} if token else {}

        sync = client.post(
            "/api/forense/knowledge/sources/sync",
            headers=headers,
            json={"source_id": "seeds_parking", "skip_existing": True},
        )
        if sync.status_code != 200:
            _fail(f"Sync biblioteca falló ({sync.status_code}): {sync.text}")
        sync_body = sync.json()
        print(
            f"[2/6] Biblioteca parking: {sync_body.get('imported', 0)} nuevas, "
            f"{sync_body.get('skipped', 0)} existentes"
        )

        with tempfile.TemporaryDirectory() as tmp:
            video_path = Path(tmp) / "demo_patio_retroceso.mp4"
            make_demo_video(video_path)
            print(f"[3/6] Video demo generado ({video_path.stat().st_size // 1024} KB)")

            with video_path.open("rb") as vf:
                job_res = client.post(
                    "/api/forense/jobs",
                    headers=headers,
                    data={
                        "title": "Demo — retroceso en patio sin guía",
                        "site": "Faena demo",
                        "case_notes": "Vehículo retrocede hacia zona peatonal. Caso sintético para validación edge.",
                        "template_id": "transporte",
                        "meters_per_pixel": "0.05",
                        "max_machinery_kmh": "12",
                        "max_person_kmh": "6",
                        "min_distance_m": "2",
                    },
                    files={"video": ("demo_patio_retroceso.mp4", vf, "video/mp4")},
                )
        if job_res.status_code != 200:
            _fail(f"Crear trabajo falló ({job_res.status_code}): {job_res.text}")
        job_id = job_res.json()["job"]["id"]
        print(f"[4/6] Trabajo creado: {job_id}")

        deadline = time.time() + MAX_WAIT_SEC
        status = "queued"
        while time.time() < deadline:
            j = client.get(f"/api/forense/jobs/{job_id}", headers=headers)
            if j.status_code != 200:
                _fail(f"Consultar trabajo falló ({j.status_code})")
            body = j.json().get("job") or j.json()
            status = body.get("status", "")
            progress = body.get("progress", 0)
            msg = body.get("progress_message") or ""
            print(f"      … {status} {progress}% {msg}", end="\r")
            if status == "done":
                print()
                break
            if status == "error":
                _fail(body.get("error") or "Análisis falló")
            time.sleep(POLL_SEC)
        else:
            _fail(f"Timeout tras {MAX_WAIT_SEC}s (estado: {status})")

        report = client.get(f"/api/forense/jobs/{job_id}/report.md", headers=headers)
        if report.status_code != 200:
            _fail(f"Informe MD falló ({report.status_code})")
        md = report.text
        lines = [ln for ln in md.splitlines() if ln.strip()][:8]
        print("[5/6] Informe Markdown generado:")
        for ln in lines:
            print(f"      {ln[:90]}")

        final = client.get(f"/api/forense/jobs/{job_id}", headers=headers).json()
        job = final.get("job") or final
        events = (job.get("analysis") or {}).get("event_count", 0)
        has_pdf = job.get("has_pdf", False)
        frames = job.get("frames_analyzed", 0)
        kn = job.get("knowledge") or {}
        matches = len(kn.get("matches") or [])

        print("[6/6] Resultado demo")
        print(f"      Eventos detectados: {events}")
        print(f"      Fotogramas analizados: {frames}")
        print(f"      Coincidencias biblioteca: {matches}")
        print(f"      PDF disponible: {'sí' if has_pdf else 'no'}")
        print(f"      Ver en UI: {BASE}/  → trabajo {job_id}")
        print("=== Demo completada ===")


if __name__ == "__main__":
    run_demo()
