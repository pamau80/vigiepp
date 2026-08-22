"""Ojo vigilia: monitoreo continuo de cámaras estáticas sin depender del navegador."""

from __future__ import annotations

import logging
import os
import threading
import time
from collections import deque
from datetime import datetime, timezone
from typing import Any

from .behavior import evaluate_behavior
from .compliance import evaluate
from .detector import PPEDetector, encode_jpeg
from .precision import normalize_precision
from .stream_rtsp import get_or_create_stream, stop_stream

logger = logging.getLogger("vigiepp.vigil")

_MAX_EVENTS = 300


class VigilMonitor:
    _instance: VigilMonitor | None = None
    _inst_lock = threading.Lock()

    def __init__(self) -> None:
        self._running = False
        self._thread: threading.Thread | None = None
        self._lock = threading.Lock()
        self._events: deque[dict[str, Any]] = deque(maxlen=_MAX_EVENTS)
        self._camera_state: dict[str, dict[str, Any]] = {}
        self._profile = os.getenv("VIGIEPP_VIGIL_PROFILE", "general")
        self._interval = float(os.getenv("VIGIEPP_VIGIL_INTERVAL", "2.5"))
        self._precision = normalize_precision(os.getenv("VIGIEPP_PRECISION", "alta"))
        self._identify_every = max(1, int(os.getenv("VIGIEPP_VIGIL_IDENTIFY_EVERY", "4")))
        self._tick = 0
        self._started_at: str | None = None

    @classmethod
    def get(cls) -> VigilMonitor:
        with cls._inst_lock:
            if cls._instance is None:
                cls._instance = cls()
            return cls._instance

    def start(self, profile: str | None = None) -> dict[str, Any]:
        if profile:
            self._profile = profile
        if self._running:
            return self.status()
        self._running = True
        self._started_at = datetime.now(timezone.utc).isoformat()
        self._thread = threading.Thread(target=self._loop, name="vigil-monitor", daemon=True)
        self._thread.start()
        logger.info("Ojo vigilia iniciado (intervalo %.1fs, perfil %s)", self._interval, self._profile)
        return self.status()

    def stop(self) -> dict[str, Any]:
        self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=3.0)
        self._thread = None
        self._started_at = None
        logger.info("Ojo vigilia detenido")
        return self.status()

    def status(self) -> dict[str, Any]:
        with self._lock:
            return {
                "running": self._running,
                "started_at": self._started_at,
                "profile": self._profile,
                "interval_sec": self._interval,
                "precision": self._precision,
                "cameras": dict(self._camera_state),
                "event_count": len(self._events),
                "recent_events": list(self._events)[-15:],
            }

    def events(self, limit: int = 50) -> list[dict[str, Any]]:
        lim = max(1, min(limit, _MAX_EVENTS))
        with self._lock:
            return list(self._events)[-lim:]

    def _emit(self, event: dict[str, Any]) -> None:
        with self._lock:
            self._events.append(event)

    def _loop(self) -> None:
        from . import cameras as cameras_mod
        from . import zones as zones_mod

        while self._running:
            self._tick += 1
            cams = [c for c in cameras_mod.list_cameras() if c.get("enabled", True)]
            if not cams:
                time.sleep(self._interval)
                continue

            for cam in cams:
                if not self._running:
                    break
                cam_id = str(cam.get("id") or "")
                url = str(cam.get("url") or "")
                name = str(cam.get("name") or cam_id)
                if not url:
                    continue
                try:
                    stream = get_or_create_stream(url)
                    frame = stream.read()
                    if frame is None:
                        with self._lock:
                            self._camera_state[cam_id] = {
                                "name": name,
                                "ok": False,
                                "error": stream.last_error or "Sin frame",
                                "updated_at": datetime.now(timezone.utc).isoformat(),
                            }
                        continue

                    det = PPEDetector.get()
                    detections, annotated = det.predict(
                        frame,
                        conf=0.35,
                        precision=self._precision,
                        enhance=True,
                    )
                    fh, fw = frame.shape[:2]
                    zone_eval = zones_mod.evaluate_zones(detections, fw, fh, camera_id=cam_id)
                    # Cumplimiento interno solo para merodeo (no alertas EPP en ojo vigilia)
                    compliance = evaluate(detections, self._profile)
                    persons = [
                        {
                            "person_id": p.person_id,
                            "compliant": p.compliant,
                            "missing": p.missing,
                            "present": p.present,
                        }
                        for p in compliance.persons
                    ]
                    behavior = evaluate_behavior(
                        detections,
                        zone_hits=zone_eval.get("hits"),
                        persons=persons,
                        frame_w=fw,
                        frame_h=fh,
                    )

                    all_alerts: list[str] = []
                    for a in zone_eval.get("alerts") or []:
                        if a not in all_alerts:
                            all_alerts.append(a)
                    for a in behavior.get("alerts") or []:
                        if a not in all_alerts:
                            all_alerts.append(a)

                    identity_summary = None

                    snapshot_b64: str | None = None
                    if all_alerts and annotated is not None:
                        try:
                            import base64

                            jpg = encode_jpeg(annotated if annotated is not None else frame)
                            snapshot_b64 = base64.b64encode(jpg).decode("ascii")
                        except Exception:  # noqa: BLE001
                            snapshot_b64 = None

                    state = {
                        "name": name,
                        "ok": True,
                        "connected": stream.connected,
                        "persons": len(compliance.persons),
                        "compliant": not all_alerts,
                        "alerts": all_alerts,
                        "behavior_severity": behavior.get("severity"),
                        "updated_at": datetime.now(timezone.utc).isoformat(),
                    }
                    with self._lock:
                        self._camera_state[cam_id] = state

                    if all_alerts:
                        self._emit(
                            {
                                "ts": state["updated_at"],
                                "camera_id": cam_id,
                                "camera_name": name,
                                "alerts": all_alerts,
                                "behavior": behavior.get("events") or [],
                                "severity": behavior.get("severity") or "medium",
                                "snapshot_b64": snapshot_b64,
                            }
                        )
                except Exception as exc:  # noqa: BLE001
                    logger.exception("Vigil error en cámara %s", cam_id)
                    with self._lock:
                        self._camera_state[cam_id] = {
                            "name": name,
                            "ok": False,
                            "error": str(exc)[:200],
                            "updated_at": datetime.now(timezone.utc).isoformat(),
                        }

            time.sleep(self._interval)

    def stop_camera_streams(self) -> None:
        from . import cameras as cameras_mod

        for cam in cameras_mod.list_cameras():
            url = str(cam.get("url") or "")
            if url:
                stop_stream(url)


def auto_start_if_configured() -> None:
    if os.getenv("VIGIEPP_VIGIL_AUTO", "").strip().lower() in ("1", "true", "yes", "on"):
        VigilMonitor.get().start()
