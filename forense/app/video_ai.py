"""Interpretación visual con modelo de visión (OpenAI-compatible)."""

from __future__ import annotations

import base64
import json
import logging
import os
import urllib.error
import urllib.request
from typing import Any

logger = logging.getLogger("vigiepp.forense.video_ai")

_MAX_FRAMES = 6


def _api_config() -> tuple[str, str, str] | None:
    key = (os.getenv("VIGIEPP_FORENSE_OPENAI_KEY") or os.getenv("OPENAI_API_KEY") or "").strip()
    if not key:
        return None
    base = (os.getenv("VIGIEPP_FORENSE_OPENAI_BASE") or "https://api.openai.com/v1").rstrip("/")
    model = os.getenv("VIGIEPP_FORENSE_VISION_MODEL", os.getenv("VIGIEPP_FORENSE_LLM_MODEL", "gpt-4o-mini"))
    return key, base, model


def _format_ts(sec: float) -> str:
    s = int(sec)
    h, rem = divmod(s, 3600)
    m, s = divmod(rem, 60)
    return f"{h:02d}:{m:02d}:{s:02d}"


def _pick_frames(job: dict[str, Any]) -> list[dict[str, Any]]:
    from .jobs import extract_frame_jpeg, keyframe_path

    job_id = job["id"]
    analysis = job.get("analysis") or {}
    keyframes = list(analysis.get("keyframes") or [])
    focus_from = job.get("focus_from_sec")
    focus_until = job.get("focus_until_sec")
    has_focus = (
        focus_from is not None
        and focus_until is not None
        and float(focus_until) > float(focus_from)
    )

    def in_focus(kf: dict) -> bool:
        if not has_focus:
            return True
        t = float(kf.get("time_sec") or 0)
        return float(focus_from) <= t <= float(focus_until)

    ordered = [kf for kf in keyframes if in_focus(kf)]
    if len(ordered) < 2 and has_focus:
        ordered = keyframes
    if not ordered:
        ordered = keyframes

    picked: list[dict[str, Any]] = []
    step = max(1, len(ordered) // _MAX_FRAMES) if ordered else 1
    for i, kf in enumerate(ordered):
        if i % step != 0 and i != len(ordered) - 1:
            continue
        name = kf.get("image")
        if not name:
            continue
        path = keyframe_path(job_id, name)
        if not path or not path.is_file():
            continue
        picked.append(
            {
                "time_sec": kf.get("time_sec"),
                "time_label": kf.get("time_label"),
                "jpeg": path.read_bytes(),
            }
        )
        if len(picked) >= _MAX_FRAMES:
            break

    # Pocos keyframes: muestrear el video completo para no perder contexto
    if len(picked) < 4:
        from .jobs import extract_frame_jpeg

        duration = float((job.get("meta") or {}).get("duration_sec") or 0)
        if duration > 5:
            n = min(_MAX_FRAMES, 6)
            step_t = duration / max(n - 1, 1)
            for i in range(n):
                t = i * step_t
                jpeg = extract_frame_jpeg(job_id, t)
                if not jpeg:
                    continue
                picked.append(
                    {
                        "time_sec": round(t, 3),
                        "time_label": _format_ts(t),
                        "jpeg": jpeg,
                    }
                )

    # Sin capturas con eventos: extraer directo del video en la ventana de enfoque
    if len(picked) < 3 and has_focus:
        span = float(focus_until) - float(focus_from)
        n = min(_MAX_FRAMES, max(3, int(span / 4) + 1))
        step_t = span / max(n - 1, 1)
        for i in range(n):
            t = float(focus_from) + i * step_t
            jpeg = extract_frame_jpeg(job_id, t)
            if not jpeg:
                continue
            picked.append(
                {
                    "time_sec": round(t, 3),
                    "time_label": _format_ts(t),
                    "jpeg": jpeg,
                }
            )
        # dedupe by time
        seen: set[float] = set()
        deduped: list[dict[str, Any]] = []
        for fr in picked:
            key = round(float(fr.get("time_sec") or 0), 1)
            if key in seen:
                continue
            seen.add(key)
            deduped.append(fr)
        picked = deduped[:_MAX_FRAMES]

    return picked


def analyze_job_with_vision(job: dict[str, Any]) -> dict[str, Any] | None:
    """Envía fotogramas clave a modelo de visión; prioriza ventana de enfoque."""
    cfg = _api_config()
    if not cfg:
        return None
    api_key, base, model = cfg
    frames = _pick_frames(job)
    if not frames:
        return None

    focus_desc = (job.get("focus_description") or job.get("case_notes") or "").strip()
    title = job.get("title") or "Incidente"
    site = job.get("site") or "Faena"
    template = job.get("template_name") or job.get("template_id") or ""
    focus_from = job.get("focus_from_sec")
    focus_until = job.get("focus_until_sec")
    window_txt = ""
    if focus_from is not None and focus_until is not None:
        window_txt = f"Ventana prioritaria del incidente: {focus_from}s — {focus_until}s."

    expert_checklist = (
        "Analizá el incidente de forma integral (cualquier industria): "
        "EPP (casco, chaleco reflectante, lentes, guantes), proximidad persona–maquinaria, "
        "velocidad y maniobras, zonas restringidas, carga suspendida o línea de fuego, "
        "caídas o atrapamientos, actos inseguros, y solo si es visible: fuego, humo o respuesta de emergencia. "
        "Si algo no se ve, indicá «no observable»."
    )

    content: list[dict[str, Any]] = [
        {
            "type": "text",
            "text": (
                "Sos analista senior en prevención de riesgos industriales (Chile). "
                "Mirá estas capturas de un video de seguridad en faena. "
                f"Caso: «{title}» · sitio: {site} · plantilla: {template}. "
                f"{window_txt} "
                f"{expert_checklist} "
                f"Enfoque del operador: {focus_desc or 'no especificado'}. "
                "Respondé en JSON con claves: "
                "resumen (2-4 oraciones), "
                "epp_y_ropa (cumplimiento EPP visible), "
                "maquinaria_proximidad (equipos, distancias, maniobras), "
                "conducta_y_caidas (posturas, caídas, actos inseguros), "
                "zonas_y_carga (zonas, carga suspendida, línea de fuego), "
                "energia_fuego_humo (solo si visible; si no, «no observable»), "
                "respuesta_emergencia (solo si visible; si no, «no observable»), "
                "secuencia (lista de {hora, observacion}), "
                "riesgos (lista), posibles_falsos_positivos (alertas del detector que NO ves), "
                "recomendaciones (lista). "
                "Solo describe lo visible; usa condicional; no afirmes culpa legal."
            ),
        }
    ]
    for fr in frames:
        b64 = base64.standard_b64encode(fr["jpeg"]).decode("ascii")
        content.append(
            {
                "type": "image_url",
                "image_url": {"url": f"data:image/jpeg;base64,{b64}", "detail": "low"},
            }
        )
        content.append({"type": "text", "text": f"Captura en {fr.get('time_label') or fr.get('time_sec')}."})

    payload = {
        "model": model,
        "messages": [{"role": "user", "content": content}],
        "temperature": 0.2,
        "max_tokens": 1200,
    }
    req = urllib.request.Request(
        f"{base}/chat/completions",
        data=json.dumps(payload).encode(),
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=90) as resp:
            data = json.loads(resp.read().decode())
        raw = (data["choices"][0]["message"]["content"] or "").strip()
    except (urllib.error.URLError, KeyError, json.JSONDecodeError, TimeoutError) as exc:
        logger.warning("Vision API falló: %s", exc)
        return None

    parsed: dict[str, Any] | None = None
    try:
        start = raw.find("{")
        end = raw.rfind("}")
        if start >= 0 and end > start:
            parsed = json.loads(raw[start : end + 1])
    except json.JSONDecodeError:
        parsed = None

    return {
        "model": model,
        "frames_used": len(frames),
        "frames_meta": [{"time_sec": f.get("time_sec"), "time_label": f.get("time_label")} for f in frames],
        "focus_window": {"from_sec": focus_from, "until_sec": focus_until},
        "raw": raw,
        "parsed": parsed,
    }


def format_video_ai_markdown(video_ai: dict[str, Any] | None) -> str:
    if not video_ai:
        return "_Interpretación visual no disponible (configure `VIGIEPP_FORENSE_OPENAI_KEY`)._\n"
    parsed = video_ai.get("parsed") or {}
    if parsed:
        lines = []
        if parsed.get("resumen"):
            lines.append(str(parsed["resumen"]))
        for label, key in (
            ("EPP y ropa", "epp_y_ropa"),
            ("Maquinaria y proximidad", "maquinaria_proximidad"),
            ("Conducta y caídas", "conducta_y_caidas"),
            ("Zonas y carga", "zonas_y_carga"),
            ("Fuego o humo", "energia_fuego_humo"),
            ("Respuesta emergencia", "respuesta_emergencia"),
            # compatibilidad esquema anterior
            ("Fuego (legacy)", "fuego_contenedor"),
            ("Humo (legacy)", "humo"),
            ("EPP reflectante (legacy)", "epp_chaleco_reflectante"),
            ("Emergencia (legacy)", "brigada_incendios"),
        ):
            val = parsed.get(key)
            if not val or str(val).strip().lower() in {"no observable", "no visible", "ninguno", "n/a"}:
                continue
            lines.append(f"\n**{label}:** {val}")
        seq = parsed.get("secuencia") or []
        if seq:
            lines.append("\n**Secuencia observada:**\n")
            for item in seq[:12]:
                if isinstance(item, dict):
                    lines.append(f"- **{item.get('hora', '—')}:** {item.get('observacion', '')}")
                else:
                    lines.append(f"- {item}")
        risks = parsed.get("riesgos") or []
        if risks:
            lines.append("\n**Riesgos visibles:**\n")
            for r in risks[:8]:
                lines.append(f"- {r}")
        fp = parsed.get("posibles_falsos_positivos") or []
        if fp:
            lines.append("\n**Posibles falsos positivos del detector automático:**\n")
            for f in fp[:8]:
                lines.append(f"- {f}")
        rec = parsed.get("recomendaciones") or []
        if rec:
            lines.append("\n**Recomendaciones:**\n")
            for r in rec[:6]:
                lines.append(f"- {r}")
        return "\n".join(lines) + "\n"
    return (video_ai.get("raw") or "").strip() + "\n"
