"""Zonas de riesgo por cámara/viewport (coords normalizadas 0–1)."""

from __future__ import annotations

import json
import threading
import uuid
from datetime import UTC, datetime
from typing import Any

from .paths import data_dir

DATA_DIR = data_dir()
ZONES_FILE = DATA_DIR / "zones.json"
_lock = threading.Lock()

DEFAULT = {
    "zones": [
        {
            "id": "zona-restringida-demo",
            "name": "Zona restringida",
            "type": "restricted",
            "enabled": True,
            "x": 0.05,
            "y": 0.1,
            "w": 0.35,
            "h": 0.5,
            "color": "#e85d04",
        },
        {
            "id": "via-vehiculos-demo",
            "name": "Vía vehículos",
            "type": "vehicle_lane",
            "enabled": True,
            "x": 0.55,
            "y": 0.35,
            "w": 0.4,
            "h": 0.55,
            "color": "#d62828",
        },
    ],
    "updated_at": None,
}


PRESETS: dict[str, list[dict[str, Any]]] = {
    "faena": DEFAULT["zones"],
    "porteria": [
        {
            "id": "acceso-principal",
            "name": "Línea de acceso",
            "type": "restricted",
            "enabled": True,
            "x": 0.25,
            "y": 0.15,
            "w": 0.5,
            "h": 0.7,
            "color": "#e85d04",
        }
    ],
    "bodega": [
        {
            "id": "pasillo-montacargas",
            "name": "Pasillo montacargas",
            "type": "vehicle_lane",
            "enabled": True,
            "x": 0.35,
            "y": 0.05,
            "w": 0.3,
            "h": 0.9,
            "color": "#d62828",
        },
        {
            "id": "area-carga",
            "name": "Área de carga",
            "type": "restricted",
            "enabled": True,
            "x": 0.02,
            "y": 0.55,
            "w": 0.32,
            "h": 0.4,
            "color": "#e85d04",
        },
        {
            "id": "maquinaria-bodega",
            "name": "Zona maquinaria",
            "type": "machinery",
            "enabled": True,
            "x": 0.68,
            "y": 0.1,
            "w": 0.28,
            "h": 0.4,
            "color": "#9b2226",
        },
    ],
}


def apply_preset(name: str) -> dict[str, Any]:
    key = (name or "faena").strip().lower()
    zones = PRESETS.get(key)
    if not zones:
        raise ValueError(f"Preset desconocido: {name}. Usa: {', '.join(PRESETS)}")
    # copias nuevas con ids únicos si ya existen
    payload_zones = []
    for z in zones:
        item = dict(z)
        item["id"] = str(item.get("id") or uuid.uuid4().hex[:10])
        payload_zones.append(item)
    return save_zones(payload_zones)


def list_presets() -> list[dict[str, Any]]:
    return [
        {"id": "faena", "name": "Faena general", "zones": 2, "hint": "Restringida + vía vehículos"},
        {"id": "porteria", "name": "Portería / acceso", "zones": 1, "hint": "Línea de control frontal"},
        {"id": "bodega", "name": "Bodega / montacargas", "zones": 2, "hint": "Pasillo + área de carga"},
    ]


def _ensure() -> None:
    global DATA_DIR, ZONES_FILE
    DATA_DIR = data_dir()
    ZONES_FILE = DATA_DIR / "zones.json"
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if not ZONES_FILE.exists():
        payload = dict(DEFAULT)
        payload["updated_at"] = datetime.now(UTC).isoformat()
        ZONES_FILE.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def get_zones() -> dict[str, Any]:
    _ensure()
    with _lock:
        return json.loads(ZONES_FILE.read_text(encoding="utf-8"))


_ZONE_TYPES = ("restricted", "vehicle_lane", "machinery")


def _normalize_zone_type(raw: Any) -> str:
    t = str(raw or "restricted").strip().lower()
    return t if t in _ZONE_TYPES else "restricted"


def save_zones(zones: list[dict[str, Any]]) -> dict[str, Any]:
    cleaned: list[dict[str, Any]] = []
    for z in zones:
        cleaned.append(
            {
                "id": str(z.get("id") or uuid.uuid4().hex[:10]),
                "name": str(z.get("name") or "Zona")[:60],
                "type": _normalize_zone_type(z.get("type")),
                "enabled": bool(z.get("enabled", True)),
                "x": float(max(0, min(0.95, z.get("x", 0)))),
                "y": float(max(0, min(0.95, z.get("y", 0)))),
                "w": float(max(0.05, min(1.0, z.get("w", 0.2)))),
                "h": float(max(0.05, min(1.0, z.get("h", 0.2)))),
                "color": str(z.get("color") or "#e85d04")[:20],
            }
        )
    payload = {"zones": cleaned, "updated_at": datetime.now(UTC).isoformat()}
    with _lock:
        ZONES_FILE.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    try:
        from . import cloud_persist as cloud_mod

        cloud_mod.schedule_push()
    except Exception:  # noqa: BLE001
        pass
    return payload


def _overlap_ratio(box: list[float], zone: dict[str, Any], fw: int, fh: int) -> float:
    """IoU-ish: fracción del área de la persona dentro de la zona."""
    x1, y1, x2, y2 = box
    zx1 = zone["x"] * fw
    zy1 = zone["y"] * fh
    zx2 = (zone["x"] + zone["w"]) * fw
    zy2 = (zone["y"] + zone["h"]) * fh
    ix1, iy1 = max(x1, zx1), max(y1, zy1)
    ix2, iy2 = min(x2, zx2), min(y2, zy2)
    inter = max(0, ix2 - ix1) * max(0, iy2 - iy1)
    area = max(1.0, (x2 - x1) * (y2 - y1))
    return inter / area


def _is_person(det: dict[str, Any]) -> bool:
    lab = str(det.get("label") or "").lower()
    les = str(det.get("label_es") or "").lower()
    return "person" in lab or "persona" in les or "human" in lab


def evaluate_zones(
    detections: list[dict[str, Any]],
    frame_w: int,
    frame_h: int,
) -> dict[str, Any]:
    """Evalúa personas dentro de zonas habilitadas."""
    data = get_zones()
    zones = [z for z in data.get("zones") or [] if z.get("enabled")]
    alerts: list[str] = []
    hits: list[dict[str, Any]] = []
    if not zones or frame_w <= 0 or frame_h <= 0:
        return {"alerts": alerts, "hits": hits, "zones": data.get("zones") or []}

    persons = [d for d in detections if _is_person(d) and d.get("box")]
    # Si no hay clase persona, usar cajas grandes como proxy de cuerpo
    if not persons:
        persons = [
            d
            for d in detections
            if d.get("box")
            and (d["box"][2] - d["box"][0]) * (d["box"][3] - d["box"][1]) > (frame_w * frame_h * 0.04)
        ]

    for z in zones:
        for d in persons:
            ratio = _overlap_ratio(d["box"], z, frame_w, frame_h)
            if ratio < 0.28:
                continue
            hit = {
                "zone_id": z["id"],
                "zone_name": z["name"],
                "zone_type": z["type"],
                "overlap": round(ratio, 3),
                "box": d["box"],
            }
            hits.append(hit)
            if z["type"] == "vehicle_lane":
                alerts.append(f"Near-miss: peatón en vía «{z['name']}»")
            elif z["type"] == "machinery":
                alerts.append(f"Proximidad: persona junto a maquinaria «{z['name']}»")
            else:
                alerts.append(f"Zona restringida: persona en «{z['name']}»")

    # Near-miss extra: dos personas muy cercanas dentro de vía de vehículos
    vehicle_zones = [z for z in zones if z["type"] == "vehicle_lane"]
    if len(persons) >= 2 and vehicle_zones:
        for z in vehicle_zones:
            inside = [d for d in persons if _overlap_ratio(d["box"], z, frame_w, frame_h) >= 0.2]
            if len(inside) >= 2:
                alerts.append(f"Near-miss: múltiples personas en vía «{z['name']}»")
                break

    # unique alerts
    seen = set()
    uniq = []
    for a in alerts:
        if a not in seen:
            seen.add(a)
            uniq.append(a)
    return {"alerts": uniq, "hits": hits, "zones": data.get("zones") or []}
