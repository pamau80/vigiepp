"""Lectura de cámaras IP / NVR / DVR vía RTSP u OpenCV."""

from __future__ import annotations

import logging
import os
import threading
import time
from typing import Optional

import cv2
import numpy as np

logger = logging.getLogger("vigiepp.rtsp")


class RTSPStream:
    """Captura frames de un stream RTSP/HTTP/archivo en un hilo separado."""

    def __init__(self, url: str, reconnect_sec: float = 3.0) -> None:
        self.url = url.strip()
        self.reconnect_sec = reconnect_sec
        self._cap: Optional[cv2.VideoCapture] = None
        self._frame: Optional[np.ndarray] = None
        self._lock = threading.Lock()
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self.last_error: str | None = None
        self.connected = False

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2.0)
        if self._cap is not None:
            self._cap.release()
            self._cap = None
        self.connected = False

    def _open(self) -> bool:
        # Preferir FFmpeg para RTSP; reduce latencia
        self._cap = cv2.VideoCapture(self.url, cv2.CAP_FFMPEG)
        self._cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        if not self._cap.isOpened():
            self.last_error = f"No se pudo abrir: {self.url}"
            self.connected = False
            return False
        self.connected = True
        self.last_error = None
        return True

    def _loop(self) -> None:
        while self._running:
            if self._cap is None or not self._cap.isOpened():
                if not self._open():
                    time.sleep(self.reconnect_sec)
                    continue

            ok, frame = self._cap.read()
            if not ok or frame is None:
                self.connected = False
                self.last_error = "Stream interrumpido — reintentando"
                logger.warning(self.last_error)
                if self._cap is not None:
                    self._cap.release()
                    self._cap = None
                time.sleep(self.reconnect_sec)
                continue

            with self._lock:
                self._frame = frame
            self.connected = True

    def read(self) -> Optional[np.ndarray]:
        with self._lock:
            if self._frame is None:
                return None
            return self._frame.copy()


# Registro simple de streams activos por sesión/demo
_streams: dict[str, RTSPStream] = {}
_streams_lock = threading.Lock()
_MAX_STREAMS = int(os.getenv("VIGIEPP_MAX_RTSP_STREAMS", "24"))


def active_stream_count() -> int:
    with _streams_lock:
        return len(_streams)


def get_or_create_stream(url: str) -> RTSPStream:
    key = url.strip()
    with _streams_lock:
        if key not in _streams:
            if len(_streams) >= _MAX_STREAMS:
                raise RuntimeError(
                    f"Límite de streams RTSP ({_MAX_STREAMS}). Detén cámaras antes de agregar más."
                )
            stream = RTSPStream(key)
            stream.start()
            _streams[key] = stream
        return _streams[key]


def stop_stream(url: str) -> None:
    key = url.strip()
    with _streams_lock:
        stream = _streams.pop(key, None)
        if stream:
            stream.stop()


def stop_all() -> None:
    with _streams_lock:
        for stream in _streams.values():
            stream.stop()
        _streams.clear()