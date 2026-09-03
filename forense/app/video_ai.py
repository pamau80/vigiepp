"""Análisis visual IA de video forense (fotogramas clave + modelo visión)."""

from __future__ import annotations

import base64
import json
import logging
import os
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from .config import JOBS_DIR
from .frame_store import read_frames

logger = logging.getLogger("vigiepp.forense.video_ai")

_VISION_PROMPT = (
    "Sos analista de prevención de riesgos en faena industrial (Chile). "
    "Describí SOLO hechos observables en esta imagen de video de incidente: "
    "personas, maquinaria, EPP visible, proximidad, actos inseguros aparentes. "
    "Usá condicional (podría, se observa). Máximo 3 oraciones. "
    "No concluyas culpa legal ni negligencia."
)


def video_ai_enabled() -> bool:
    flag = os.getenv("VIGIEPP_FORENSE_VIDEO_AI", "1").strip().lower()
    if flag in ("0", "false", "no", "off"):
        return False
    return bool(_api_key())


def _api_key() -> str:
    return (os.getenv("VIGIEPP_FORENSE_OPENAI_KEY") or os.getenv("OPENAI_API_KEY") or "").strip()


def _api_base() -> str:
    return (os.getenv("VIGIEPP_FORENSE_OPENAI_BASE") or "https://api.openai.com/v1").rstrip("/")


def _vision_model() -> str:
    return (
        os.getenv("VIGIEPP_FORENSE_VISION_MODEL")
        or os.getenv("VIGIEPP_FORENSE_LLM_MODEL")
        or "gpt-4o-mini"
    )


def _max_vision_frames() -> int:
    try:
        return max(1, min(8, int(os.getenv("VIGIEPP_FORENSE_VIDEO_AI_MAX_FRAMES", "5"))))
    except ValueError:
        return 5


def _job_dir(job_id: str) -> Path:
    return JOBS_DIR / job_id


def _keyframe_bytes(job_id: str, name: str) -> bytes | None:
    path = _job_dir(job_id) / "keyframes" / name
    if path.is_file():
        return path.read_bytes()
    return None


def select_frames_for_vision(job: dict[str, Any], job_id: str) -> list[dict[str, Any]]:
    """Elige fotogramas representativos: keyframes, alertas de proximidad y timeline."""
    max_frames = _max_vision_frames()
    picks: list[dict[str, Any]] = []
    seen_times: set[float] = set()

    def add_pick(time_sec: float, time_label: str, *, source: str, image_name: str | None = None) -> None:
        if len(picks) >= max_frames:
            return
        key = round(time_sec, 1)
        if key in seen_times:
            return
        seen_times.add(key)
        picks.append(
            {
                "time_sec": round(time_sec, 3),
                "time_label": time_label or _format_ts(time_sec),
                "source": source,
                "image_name": image_name,
            }
        )

    analysis = job.get("analysis") or {}
    for kf in analysis.get("keyframes") or []:
        if kf.get("image"):
            add_pick(
                float(kf.get("time_sec") or 0),
                str(kf.get("time_label") or ""),
                source="keyframe",
                image_name=str(kf["image"]),
            )

    timeline = analysis.get("timeline") or []
    severity_rank = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    for ev in sorted(
        timeline,
        key=lambda e: severity_rank.get(str(e.get("severity") or "medium"), 9),
    ):
        if ev.get("type") in ("knowledge_match", "knowledge_conjecture"):
            continue
        add_pick(
            float(ev.get("time_sec") or 0),
            str(ev.get("time_label") or ""),
            source="timeline",
        )

    for fr in read_frames(job_id, limit=400):
        prox = fr.get("proximity") or []
        if any(p.get("alert") for p in prox):
            add_pick(
                float(fr.get("time_sec") or 0),
                str(fr.get("time_label") or ""),
                source="proximity_alert",
            )

    if len(picks) < max_frames:
        duration = float((job.get("meta") or {}).get("duration_sec") or 0)
        if duration > 0:
            steps = min(max_frames - len(picks), 3)
            for i in range(1, steps + 1):
                t = duration * i / (steps + 1)
                add_pick(t, _format_ts(t), source="sample")

    return picks[:max_frames]


def _format_ts(sec: float) -> str:
    s = max(0, int(sec))
    h, rem = divmod(s, 3600)
    m, ss = divmod(rem, 60)
    return f"{h:02d}:{m:02d}:{ss:02d}"


def _load_frame_jpeg(job_id: str, pick: dict[str, Any]) -> bytes | None:
    name = pick.get("image_name")
    if name:
        data = _keyframe_bytes(job_id, str(name))
        if data:
            return data
    from .jobs import extract_frame_jpeg

    return extract_frame_jpeg(job_id, float(pick.get("time_sec") or 0))


def _call_vision_api(jpeg_bytes: bytes, *, context: dict[str, Any]) -> str | None:
    api_key = _api_key()
    if not api_key:
        return None
    model = _vision_model()
    b64 = base64.standard_b64encode(jpeg_bytes).decode("ascii")
    case_bits = []
    if context.get("title"):
        case_bits.append(f"Caso: {context['title']}")
    if context.get("site"):
        case_bits.append(f"Faena: {context['site']}")
    if context.get("time_label"):
        case_bits.append(f"Instante: {context['time_label']}")
    prompt = _VISION_PROMPT
    if case_bits:
        prompt += "\n\n" + " · ".join(case_bits)

    payload = {
        "model": model,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/jpeg;base64,{b64}"},
                    },
                ],
            }
        ],
        "temperature": 0.2,
        "max_tokens": 220,
    }
    req = urllib.request.Request(
        f"{_api_base()}/chat/completions",
        data=json.dumps(payload).encode(),
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=90) as resp:
            data = json.loads(resp.read().decode())
        return str(data["choices"][0]["message"]["content"]).strip()
    except (urllib.error.URLError, KeyError, json.JSONDecodeError, IndexError) as exc:
        logger.warning("Vision API falló: %s", exc)
        return None


def analyze_job_video_ai(job: dict[str, Any], job_id: str) -> dict[str, Any]:
    """Describe fotogramas clave del video con modelo de visión (OpenAI-compatible)."""
    if not video_ai_enabled():
        return {
            "status": "skipped",
            "reason": "Análisis visual IA desactivado (VIGIEPP_FORENSE_VIDEO_AI=0)",
            "model": None,
            "frame_count": 0,
            "captions": [],
            "summary": "",
        }
    if not _api_key():
        return {
            "status": "skipped",
            "reason": "Sin API key — configurá VIGIEPP_FORENSE_OPENAI_KEY u OPENAI_API_KEY",
            "model": None,
            "frame_count": 0,
            "captions": [],
            "summary": "",
        }

    picks = select_frames_for_vision(job, job_id)
    if not picks:
        return {
            "status": "skipped",
            "reason": "Sin fotogramas seleccionables para análisis visual",
            "model": _vision_model(),
            "frame_count": 0,
            "captions": [],
            "summary": "",
        }

    context_base = {
        "title": job.get("title"),
        "site": job.get("site"),
        "template": job.get("template_name"),
    }
    captions: list[dict[str, Any]] = []
    errors = 0
    for pick in picks:
        jpeg = _load_frame_jpeg(job_id, pick)
        if not jpeg:
            errors += 1
            continue
        caption = _call_vision_api(
            jpeg,
            context={**context_base, "time_label": pick.get("time_label")},
        )
        if caption:
            captions.append(
                {
                    "time_sec": pick["time_sec"],
                    "time_label": pick["time_label"],
                    "caption": caption,
                    "source": pick.get("source"),
                }
            )
        else:
            errors += 1

    if not captions:
        return {
            "status": "error",
            "reason": "No se pudo obtener descripción visual (API o fotogramas)",
            "model": _vision_model(),
            "frame_count": len(picks),
            "captions": [],
            "summary": "",
        }

    summary = _build_visual_summary(captions)
    status = "ok" if errors == 0 else "partial"
    return {
        "status": status,
        "reason": "" if status == "ok" else f"{errors} fotograma(s) sin respuesta",
        "model": _vision_model(),
        "frame_count": len(captions),
        "captions": captions,
        "summary": summary,
    }


def _build_visual_summary(captions: list[dict[str, Any]]) -> str:
    if not captions:
        return ""
    if len(captions) == 1:
        return captions[0]["caption"]
    lines = [f"- {c['time_label']}: {c['caption']}" for c in captions[:5]]
    return "Observaciones visuales por instante:\n" + "\n".join(lines)


def nearest_video_caption(
    video_ai: dict[str, Any] | None,
    time_sec: float,
    *,
    tolerance: float = 2.0,
) -> dict[str, Any] | None:
    captions = (video_ai or {}).get("captions") or []
    if not captions:
        return None
    best = None
    best_dt = 1e9
    for cap in captions:
        dt = abs(float(cap.get("time_sec") or 0) - time_sec)
        if dt < best_dt:
            best_dt = dt
            best = cap
    return best if best_dt <= tolerance else None
