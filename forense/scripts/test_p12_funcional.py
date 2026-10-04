#!/usr/bin/env python3
"""Prueba funcional end-to-end Forense p12 — evidencia para validación en terreno."""

from __future__ import annotations

import json
import os
import sys
import tempfile
import time
from pathlib import Path

import cv2
import httpx
import numpy as np

BASE = os.getenv("FORENSE_URL", "http://127.0.0.1:8001").rstrip("/")
PIN = os.getenv("FORENSE_PIN", "vigiepp")
ARTIFACTS = Path(os.getenv("FORENSE_TEST_ARTIFACTS", "/opt/cursor/artifacts"))
MAX_WAIT = int(os.getenv("FORENSE_DEMO_TIMEOUT", "180"))


def log(step: str, msg: str, ok: bool = True) -> None:
    mark = "OK" if ok else "FAIL"
    line = f"[{mark}] {step}: {msg}"
    print(line)
    results.append({"step": step, "ok": ok, "message": msg})


results: list[dict] = []


def make_video(path: Path, *, label: str, color: tuple[int, int, int], seconds: float = 3.0) -> None:
    w, h, fps = 640, 360, 10.0
    writer = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"mp4v"), fps, (w, h))
    if not writer.isOpened():
        raise RuntimeError(f"No VideoWriter: {path}")
    for i in range(int(seconds * fps)):
        frame = np.full((h, w, 3), 40, dtype=np.uint8)
        cv2.putText(frame, label, (12, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (220, 220, 220), 2)
        x = 80 + int(i * 4)
        cv2.rectangle(frame, (x, 180), (x + 60, 220), color, -1)
        writer.write(frame)
    writer.release()


def main() -> int:
    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    print("=== Prueba funcional Forense p12 ===\n")

    with httpx.Client(base_url=BASE, timeout=120.0) as client:
        # 1. Health + build
        h = client.get("/api/forense/health")
        if h.status_code != 200:
            log("health", f"HTTP {h.status_code}", False)
            return 1
        build = h.json().get("build")
        lic = h.json().get("license") or {}
        log("health", f"build={build}, licencia={lic.get('detail')}", build == "forense-p12")
        if build != "forense-p12":
            return 1

        # 2. Login
        login = client.post("/api/forense/auth/login", json={"pin": PIN})
        if login.status_code != 200:
            log("login", f"HTTP {login.status_code}: {login.text}", False)
            return 1
        token = login.json().get("token") or ""
        headers = {"X-VigiEPP-Key": token}
        log("login", "sesión admin obtenida")

        # 3. Preview fuente construcción
        prev = client.get("/api/forense/knowledge/sources/seeds_construccion/preview?limit=10", headers=headers)
        if prev.status_code != 200:
            log("preview", f"HTTP {prev.status_code}", False)
            return 1
        pb = prev.json()
        log(
            "preview",
            f"candidatos={pb.get('candidates')}, válidos={pb.get('valid_count')}, inválidos={pb.get('invalid_count')}",
            pb.get("valid_count", 0) >= 1,
        )

        # 4. Multi-cam job
        with tempfile.TemporaryDirectory() as tmp:
            v0 = Path(tmp) / "cam0.mp4"
            v1 = Path(tmp) / "cam1.mp4"
            make_video(v0, label="CAM0 PATIO", color=(0, 140, 255))
            make_video(v1, label="CAM1 MUELLE", color=(80, 220, 120))
            with v0.open("rb") as f0, v1.open("rb") as f1:
                job_res = client.post(
                    "/api/forense/jobs",
                    headers=headers,
                    data={
                        "title": "Test p12 — multi-cam CPHS",
                        "site": "Faena test terreno",
                        "template_id": "construccion",
                        "meters_per_pixel": "0.05",
                    },
                    files={
                        "video": ("cam0.mp4", f0, "video/mp4"),
                        "video2": ("cam1.mp4", f1, "video/mp4"),
                    },
                )
        if job_res.status_code != 200:
            log("create_job", f"HTTP {job_res.status_code}: {job_res.text}", False)
            return 1
        job_id = job_res.json()["job"]["id"]
        log("create_job", f"job_id={job_id} (2 cámaras)")

        # 5. Poll until done
        status = "queued"
        deadline = time.time() + MAX_WAIT
        while time.time() < deadline:
            j = client.get(f"/api/forense/jobs/{job_id}", headers=headers).json()["job"]
            status = j.get("status", "")
            if status == "done":
                break
            if status == "error":
                log("analysis", j.get("error") or "error desconocido", False)
                return 1
            time.sleep(2)
        else:
            log("analysis", f"timeout ({MAX_WAIT}s)", False)
            return 1
        log("analysis", f"completado · eventos={j.get('analysis', {}).get('event_count', 0)}")

        # 6. Multi-cam video endpoints
        cams = j.get("video_cameras") or []
        log("video_cameras", str(cams), len(cams) >= 2)
        for cam in cams[:2]:
            vr = client.get(f"/api/forense/jobs/{job_id}/video?cam={cam}", headers=headers)
            log(f"video_cam_{cam}", f"HTTP {vr.status_code}, {len(vr.content)} bytes", vr.status_code == 200 and len(vr.content) > 500)

        # 7. LLM status
        llm = j.get("llm_status")
        log("llm_status", llm or "—", llm in ("offline", "enriched", "failed"))

        # 8. Committee CPHS
        cm = client.get(f"/api/forense/jobs/{job_id}/committee.md", headers=headers)
        if cm.status_code != 200:
            log("committee", f"HTTP {cm.status_code}", False)
            return 1
        committee_text = cm.text
        checks = [
            ("CPHS en terreno", "CPHS en terreno" in committee_text),
            ("DS 54/69", "DS N° 54/69" in committee_text or "DS N°54" in committee_text),
            ("plan seguimiento", "Plan de seguimiento CPHS" in committee_text),
            ("construccion", "andamio" in committee_text.lower() or "construcción" in committee_text.lower() or "Obra" in committee_text),
        ]
        for name, passed in checks:
            log(f"committee_{name}", "presente" if passed else "ausente", passed)
        (ARTIFACTS / "forense_committee_p12.md").write_text(committee_text, encoding="utf-8")

        # 9. Report + bundle
        rep = client.get(f"/api/forense/jobs/{job_id}/report.md", headers=headers)
        log("report", f"HTTP {rep.status_code}, {len(rep.text)} chars", rep.status_code == 200)
        (ARTIFACTS / "forense_report_p12.md").write_text(rep.text, encoding="utf-8")

        bundle = client.get(f"/api/forense/jobs/{job_id}/case_bundle.zip", headers=headers)
        if bundle.status_code == 200:
            (ARTIFACTS / "forense_case_bundle_p12.zip").write_bytes(bundle.content)
            log("bundle", f"{len(bundle.content)} bytes guardado")
        else:
            log("bundle", f"HTTP {bundle.status_code}", False)

    passed = sum(1 for r in results if r["ok"])
    total = len(results)
    summary = {"passed": passed, "total": total, "all_ok": passed == total, "results": results}
    (ARTIFACTS / "forense_p12_funcional.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\n=== Resultado: {passed}/{total} pasos OK ===")
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
