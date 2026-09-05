"""Muestreo adaptivo de frames para análisis forense rápido."""

from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np


@dataclass
class SampledFrame:
    index: int
    time_sec: float
    frame_bgr: np.ndarray
    burst: bool


def _gray_small(frame: np.ndarray, width: int = 160) -> np.ndarray:
    h, w = frame.shape[:2]
    scale = width / max(w, 1)
    small = cv2.resize(frame, (width, max(1, int(h * scale))))
    return cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)


def adaptive_sample_video(
    video_path: str,
    *,
    base_interval_sec: float = 0.5,
    motion_threshold: float = 12.0,
    burst_interval_sec: float = 0.1,
    burst_duration_sec: float = 4.0,
    max_frames: int = 4000,
) -> tuple[list[SampledFrame], dict]:
    """Extrae frames con muestreo base + ráfaga ante movimiento."""
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise ValueError(f"No se pudo abrir video: {video_path}")

    fps = float(cap.get(cv2.CAP_PROP_FPS) or 25.0)
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    duration = total / fps if fps > 0 and total > 0 else 0.0

    samples: list[SampledFrame] = []
    prev_gray: np.ndarray | None = None
    idx = 0
    last_sample_t = -1.0
    burst_until = -1.0

    while len(samples) < max_frames:
        ok, frame = cap.read()
        if not ok:
            break
        t = idx / fps
        gray = _gray_small(frame)
        motion = 0.0
        if prev_gray is not None:
            motion = float(np.mean(cv2.absdiff(gray, prev_gray)))
        prev_gray = gray

        in_burst = t < burst_until
        if motion >= motion_threshold:
            burst_until = max(burst_until, t + burst_duration_sec)

        interval = burst_interval_sec if in_burst or motion >= motion_threshold else base_interval_sec
        if last_sample_t < 0 or (t - last_sample_t) >= interval:
            samples.append(
                SampledFrame(
                    index=idx,
                    time_sec=round(t, 3),
                    frame_bgr=frame.copy(),
                    burst=in_burst or motion >= motion_threshold,
                )
            )
            last_sample_t = t
        idx += 1

    cap.release()
    meta = {
        "fps": round(fps, 3),
        "total_frames": idx,
        "duration_sec": round(duration or (idx / fps if fps else 0), 2),
        "sampled_frames": len(samples),
    }
    return samples, meta


def enrich_focus_window(
    samples: list[SampledFrame],
    video_path: str,
    *,
    focus_from_sec: float,
    focus_until_sec: float,
    interval_sec: float = 0.12,
    max_extra: int = 120,
) -> list[SampledFrame]:
    """Agrega fotogramas densos en la ventana del incidente indicada por el operador."""
    if focus_until_sec <= focus_from_sec:
        return samples
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        return samples
    fps = float(cap.get(cv2.CAP_PROP_FPS) or 25.0)
    if fps <= 0:
        cap.release()
        return samples

    existing = {round(s.time_sec, 2) for s in samples}
    extras: list[SampledFrame] = []
    t = focus_from_sec
    while t <= focus_until_sec and len(extras) < max_extra:
        cap.set(cv2.CAP_PROP_POS_FRAMES, int(t * fps))
        ok, frame = cap.read()
        if ok and frame is not None:
            key = round(t, 2)
            if key not in existing:
                extras.append(
                    SampledFrame(
                        index=int(t * fps),
                        time_sec=round(t, 3),
                        frame_bgr=frame.copy(),
                        burst=True,
                    )
                )
                existing.add(key)
        t += interval_sec
    cap.release()
    if not extras:
        return samples
    merged = sorted(samples + extras, key=lambda s: s.time_sec)
    return merged


def sample_window_frames(
    video_path: str,
    *,
    focus_from_sec: float,
    focus_until_sec: float,
    interval_sec: float = 0.25,
    max_frames: int = 80,
) -> list[SampledFrame]:
    """Extrae fotogramas densos solo en la ventana del incidente."""
    if focus_until_sec <= focus_from_sec:
        return []
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        return []
    fps = float(cap.get(cv2.CAP_PROP_FPS) or 25.0)
    if fps <= 0:
        cap.release()
        return []
    out: list[SampledFrame] = []
    t = focus_from_sec
    while t <= focus_until_sec and len(out) < max_frames:
        cap.set(cv2.CAP_PROP_POS_FRAMES, int(t * fps))
        ok, frame = cap.read()
        if ok and frame is not None:
            out.append(
                SampledFrame(
                    index=int(t * fps),
                    time_sec=round(t, 3),
                    frame_bgr=frame.copy(),
                    burst=True,
                )
            )
        t += interval_sec
    cap.release()
    return out
