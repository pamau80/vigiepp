"""Evaluación clínica del instante forense (ojo clínico)."""

from __future__ import annotations

from typing import Any


def _track_kind_map(frame_rec: dict[str, Any]) -> dict[int, str]:
    out: dict[int, str] = {}
    for tr in frame_rec.get("tracks") or []:
        tid = tr.get("track_id")
        if tid is not None:
            out[int(tid)] = str(tr.get("kind") or "other")
    return out


def _events_near(
    timeline: list[dict[str, Any]] | None,
    time_sec: float,
    *,
    tolerance: float = 1.5,
) -> list[dict[str, Any]]:
    if not timeline:
        return []
    out: list[dict[str, Any]] = []
    for ev in timeline:
        t = float(ev.get("time_sec") or 0)
        if abs(t - time_sec) <= tolerance:
            out.append(ev)
    return out


def evaluate_instant_audit(
    frame_rec: dict[str, Any] | None,
    *,
    timeline: list[dict[str, Any]] | None = None,
    knowledge_matches: list[dict[str, Any]] | None = None,
    video_caption: dict[str, Any] | None = None,
    time_sec: float | None = None,
    min_distance_m: float = 2.0,
    max_machinery_kmh: float = 15.0,
    max_person_kmh: float = 8.0,
    time_tolerance: float = 1.5,
) -> dict[str, Any]:
    """Resume el estado clínico de un fotograma para UI de auditoría."""
    if not frame_rec:
        return {
            "level": "idle",
            "status_label": "Sin datos",
            "headline": "Esperando análisis del video…",
            "glance_metric": "",
            "sections": [],
            "events_near": [],
        }

    t = float(time_sec if time_sec is not None else frame_rec.get("time_sec") or 0)
    counts = frame_rec.get("counts") or {}
    persons = int(counts.get("persons") or 0)
    vehicles = int(counts.get("vehicles") or 0)
    prox = list(frame_rec.get("proximity") or [])
    speeds = list(frame_rec.get("speeds") or [])
    kind_by_track = _track_kind_map(frame_rec)
    events_near = _events_near(timeline, t, tolerance=time_tolerance)

    level = "ok"
    issues: list[str] = []

    prox_alert = next((p for p in prox if p.get("alert")), None)
    if prox_alert:
        level = "alert"
        issues.append(
            f"Proximidad crítica {prox_alert.get('distance_m')} m "
            f"(persona #{prox_alert.get('person_track')} – máq. #{prox_alert.get('machinery_track')})"
        )
    elif prox:
        closest = prox[0]
        dist = float(closest.get("distance_m") or 99)
        if dist <= min_distance_m * 1.5:
            level = "warn"
            issues.append(f"Distancia persona–maquinaria: {dist} m (umbral {min_distance_m} m)")

    speed_lines: list[str] = []
    for sp in speeds:
        tid = int(sp.get("track_id") or 0)
        kmh = float(sp.get("speed_kmh") or 0)
        kind = kind_by_track.get(tid, "other")
        speed_lines.append(f"#{tid} {kmh} km/h ({kind})")
        limit = max_machinery_kmh if kind == "machinery" else max_person_kmh if kind == "person" else None
        if limit is not None and kmh > limit:
            if level != "alert":
                level = "warn"
            issues.append(f"Exceso velocidad #{tid}: {kmh} km/h (límite {limit})")

    kn_events = [e for e in events_near if e.get("type") in ("knowledge_match", "knowledge_conjecture")]
    if kn_events and level == "ok":
        level = "warn"

    if issues:
        headline = issues[0]
    elif persons or vehicles:
        headline = f"Escena estable — {persons} persona(s), {vehicles} máquina(s)"
    else:
        headline = "Sin personas ni maquinaria detectadas en este instante"

    glance_parts = [frame_rec.get("time_label") or ""]
    if prox:
        glance_parts.append(f"dist. {prox[0].get('distance_m')} m")
    elif persons or vehicles:
        glance_parts.append(f"{persons}👤 · {vehicles}🚛")
    glance_metric = " · ".join(p for p in glance_parts if p)

    det_items = []
    for det in frame_rec.get("detections") or []:
        conf = int(round(float(det.get("confidence") or 0) * 100))
        det_items.append(
            {
                "label": det.get("label") or det.get("kind") or "objeto",
                "value": f"{conf}%",
            }
        )

    sections: list[dict[str, Any]] = [
        {
            "title": "Detecciones",
            "items": det_items or [{"label": "—", "value": "Sin detecciones"}],
        },
        {
            "title": "Cinemática",
            "items": (
                [{"label": line.split()[0], "value": " ".join(line.split()[1:])} for line in speed_lines]
                if speed_lines
                else [{"label": "—", "value": "Sin velocidad medible"}]
            ),
        },
        {
            "title": "Proximidad persona–maquinaria",
            "items": (
                [
                    {
                        "label": f"#{p.get('person_track')} ↔ #{p.get('machinery_track')}",
                        "value": f"{p.get('distance_m')} m",
                        "severity": "alert" if p.get("alert") else None,
                    }
                    for p in prox[:4]
                ]
                if prox
                else [{"label": "—", "value": "Sin pares persona–máquina"}]
            ),
        },
    ]

    if events_near:
        sections.append(
            {
                "title": "Eventos en este instante",
                "items": [
                    {
                        "label": ev.get("type", "evento").replace("_", " "),
                        "value": ev.get("message") or "—",
                        "severity": ev.get("severity"),
                    }
                    for ev in events_near[:6]
                ],
            }
        )

    kn_items: list[dict[str, Any]] = []
    for ev in kn_events[:3]:
        kn_items.append(
            {
                "label": ev.get("type", "").replace("_", " "),
                "value": ev.get("message") or "—",
                "severity": "warn" if ev.get("type") == "knowledge_conjecture" else "ok",
            }
        )
    for m in (knowledge_matches or [])[:2]:
        tag = "Conjetura" if m.get("conjecture") else "Coincidencia"
        kn_items.append(
            {
                "label": tag,
                "value": f"{m.get('title')} ({m.get('confidence_pct')}%)",
                "severity": "warn" if m.get("conjecture") else "ok",
            }
        )
    if kn_items:
        sections.append({"title": "Biblioteca de aprendizaje", "items": kn_items})

    if video_caption and (video_caption.get("caption") or "").strip():
        sections.insert(
            0,
            {
                "title": "IA visual — este instante",
                "items": [
                    {
                        "label": video_caption.get("time_label") or "video",
                        "value": video_caption.get("caption"),
                        "severity": None,
                    }
                ],
            },
        )

    status_map = {
        "alert": "Riesgo alto",
        "warn": "Atención",
        "ok": "Estable",
        "idle": "Sin datos",
    }
    return {
        "level": level,
        "status_label": status_map.get(level, "—"),
        "headline": headline,
        "glance_metric": glance_metric,
        "sections": sections,
        "events_near": events_near,
    }


def clinical_progress_message(raw: str, *, progress: int | None = None) -> str:
    """Traduce mensajes técnicos de progreso a copy clínico es-CL."""
    text = (raw or "").strip()
    if not text:
        return "Preparando auditoría forense…"
    low = text.lower()
    if text == "En cola":
        return "En cola — preparando revisión forense del video"
    if text == "Preparando fuentes de video":
        return "Preparando fuentes de video para auditoría"
    if text.startswith("Consultando biblioteca"):
        return "Contrastando escena con biblioteca de incidentes"
    if text.startswith("Analizando video con IA visual"):
        return "La IA revisa fotogramas clave del video"
    if text.startswith("Generando informes"):
        return "Redactando informe clínico del caso"
    if text == "Completado":
        return "Auditoría completa — informe listo para revisión"
    if text == "Error":
        return "La auditoría no pudo completarse"
    if "calculando cinemática" in low or "mapa de calor" in low:
        return "Cuantificando velocidades y zonas de tránsito"
    if "frame " in low and "/" in text:
        return text.replace("frame ", "fotograma ").replace("Cám.", "cámara")
    if progress is not None and progress < 15:
        return f"Iniciando lectura del video — {text}"
    return text
