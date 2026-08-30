"""Reglas de acciones inseguras configurables (P0)."""

from __future__ import annotations

import json
import threading
import time
import uuid
from datetime import UTC, datetime
from typing import Any

from .paths import data_dir
from .zones import _is_person, _overlap_ratio, zones_for_source

ACTIONS_FILE = data_dir() / "action_rules.json"
DEFAULT_SETTINGS: dict[str, Any] = {
    "meters_per_pixel": 0.045,
    "reference": "Ajustá según altura de cámara NVR (4–6 cm/px típico en patio)",
    "action_audio_enabled": True,
    "action_audio_severities": ["critical", "high"],
}
_lock = threading.Lock()
_last_trigger: dict[str, float] = {}

# Palabras clave por familia de objeto/comportamiento (YOLO base + teach custom)
KEYWORDS: dict[str, list[str]] = {
    "persona": ["person", "human", "persona"],
    "montacargas": ["forklift", "montacargas", "lift", "pallet"],
    "celular": ["cell", "phone", "celular", "telefono", "móvil", "movil"],
    "carga_suspendida": ["load", "carga", "suspend", "hook", "gancho", "suspended"],
    "grua": ["crane", "grua", "grúa"],
    "casco": ["hardhat", "helmet", "casco"],
    "vehiculo": ["truck", "camion", "camión", "vehicle", "bus", "van", "pickup", "volquete", "trailer"],
    "escalera": ["ladder", "escalera", "step ladder"],
    "humo": ["smoke", "humo", "fire", "fuego", "flame", "incendio"],
    "soldadura": ["weld", "welding", "soldadura", "torch", "antorcha"],
}

PRESET_RULES: list[dict[str, Any]] = [
    {
        "id": "preset-epp-faena",
        "name": "Sin EPP completo en faena",
        "enabled": True,
        "severity": "high",
        "sources": ["*"],
        "condition": {"type": "epp_non_compliant"},
        "message": "Persona sin EPP obligatorio en faena",
        "cooldown_seconds": 20,
    },
    {
        "id": "preset-caida",
        "name": "Caída detectada",
        "enabled": True,
        "severity": "critical",
        "sources": ["*"],
        "condition": {"type": "fall_detected"},
        "message": "Caída o postura de caída detectada",
        "cooldown_seconds": 15,
    },
    {
        "id": "preset-celular-zona",
        "name": "Celular en zona restringida",
        "enabled": True,
        "severity": "medium",
        "sources": ["*"],
        "condition": {
            "type": "detect_in_zone",
            "detect_keywords": KEYWORDS["celular"],
            "zone_types": ["restricted", "machinery"],
            "min_overlap": 0.15,
            "min_conf": 0.3,
        },
        "message": "Uso de celular en zona no habilitada",
        "cooldown_seconds": 30,
    },
    {
        "id": "preset-montacargas-prox",
        "name": "Persona cerca de montacargas / grúa horquilla",
        "enabled": True,
        "severity": "high",
        "sources": ["*"],
        "condition": {
            "type": "proximity",
            "subject_keywords": KEYWORDS["persona"],
            "object_keywords": KEYWORDS["montacargas"] + KEYWORDS["grua"],
            "max_distance_meters": 3.0,
            "max_distance_ratio": 0.14,
            "min_conf": 0.25,
        },
        "message": "Persona demasiado cerca de montacargas o grúa",
        "cooldown_seconds": 25,
    },
    {
        "id": "preset-carga-suspendida",
        "name": "Persona bajo área de carga suspendida",
        "enabled": True,
        "severity": "critical",
        "sources": ["*"],
        "condition": {
            "type": "proximity",
            "subject_keywords": KEYWORDS["persona"],
            "object_keywords": KEYWORDS["carga_suspendida"],
            "max_distance_meters": 2.0,
            "max_distance_ratio": 0.12,
            "min_conf": 0.25,
        },
        "message": "Persona bajo o junto a carga suspendida",
        "cooldown_seconds": 20,
    },
    {
        "id": "preset-near-miss-via",
        "name": "Near-miss: peatón en vía de vehículos",
        "enabled": True,
        "severity": "high",
        "sources": ["*"],
        "condition": {
            "type": "person_in_zone",
            "zone_types": ["vehicle_lane"],
            "min_overlap": 0.28,
        },
        "message": "Peatón en vía de vehículos / montacargas",
        "cooldown_seconds": 20,
    },
    {
        "id": "preset-zona-maquinaria",
        "name": "Proximidad a maquinaria (zona)",
        "enabled": False,
        "severity": "medium",
        "sources": ["*"],
        "condition": {
            "type": "person_in_zone",
            "zone_types": ["machinery"],
            "min_overlap": 0.28,
        },
        "message": "Persona en zona de maquinaria",
        "cooldown_seconds": 30,
    },
    # --- P3: catálogo ampliado (deshabilitados por defecto; agregar desde UI) ---
    {
        "id": "preset-zona-restringida",
        "name": "Peatón en zona restringida",
        "enabled": False,
        "severity": "high",
        "sources": ["*"],
        "condition": {"type": "person_in_zone", "zone_types": ["restricted"], "min_overlap": 0.25},
        "message": "Persona en zona restringida",
        "cooldown_seconds": 25,
    },
    {
        "id": "preset-linea-fuego-1m",
        "name": "Línea de fuego: persona a <1 m de carga suspendida",
        "enabled": False,
        "severity": "critical",
        "sources": ["*"],
        "condition": {
            "type": "proximity",
            "subject_keywords": KEYWORDS["persona"],
            "object_keywords": KEYWORDS["carga_suspendida"],
            "max_distance_meters": 1.0,
            "max_distance_ratio": 0.08,
            "min_conf": 0.25,
        },
        "message": "Línea de fuego: persona bajo o junto a carga suspendida",
        "cooldown_seconds": 15,
    },
    {
        "id": "preset-grua-linea-fuego",
        "name": "Línea de fuego: persona cerca de grúa",
        "enabled": False,
        "severity": "critical",
        "sources": ["*"],
        "condition": {
            "type": "proximity",
            "subject_keywords": KEYWORDS["persona"],
            "object_keywords": KEYWORDS["grua"],
            "max_distance_meters": 2.5,
            "max_distance_ratio": 0.12,
            "min_conf": 0.25,
        },
        "message": "Persona en línea de fuego / radio de grúa",
        "cooldown_seconds": 20,
    },
    {
        "id": "preset-volquete-prox",
        "name": "Persona cerca de camión / volquete",
        "enabled": False,
        "severity": "high",
        "sources": ["*"],
        "condition": {
            "type": "proximity",
            "subject_keywords": KEYWORDS["persona"],
            "object_keywords": KEYWORDS["vehiculo"],
            "max_distance_meters": 4.0,
            "max_distance_ratio": 0.16,
            "min_conf": 0.3,
        },
        "message": "Persona demasiado cerca de vehículo pesado",
        "cooldown_seconds": 25,
    },
    {
        "id": "preset-celular-faena",
        "name": "Celular detectado en faena",
        "enabled": False,
        "severity": "medium",
        "sources": ["*"],
        "condition": {"type": "detect_anywhere", "detect_keywords": KEYWORDS["celular"], "min_conf": 0.35},
        "message": "Uso de celular detectado en faena",
        "cooldown_seconds": 40,
    },
    {
        "id": "preset-humo-incendio",
        "name": "Humo o fuego detectado",
        "enabled": False,
        "severity": "critical",
        "sources": ["*"],
        "condition": {"type": "detect_anywhere", "detect_keywords": KEYWORDS["humo"], "min_conf": 0.4},
        "message": "Posible humo o fuego en cámara",
        "cooldown_seconds": 30,
    },
    {
        "id": "preset-soldadura-zona",
        "name": "Soldadura en zona no habilitada",
        "enabled": False,
        "severity": "high",
        "sources": ["*"],
        "condition": {
            "type": "detect_in_zone",
            "detect_keywords": KEYWORDS["soldadura"],
            "zone_types": ["restricted"],
            "min_overlap": 0.12,
            "min_conf": 0.35,
        },
        "message": "Trabajo de soldadura en zona restringida",
        "cooldown_seconds": 30,
    },
    {
        "id": "preset-vehiculo-restringido",
        "name": "Vehículo en zona restringida",
        "enabled": False,
        "severity": "high",
        "sources": ["*"],
        "condition": {
            "type": "detect_in_zone",
            "detect_keywords": KEYWORDS["vehiculo"],
            "zone_types": ["restricted"],
            "min_overlap": 0.2,
            "min_conf": 0.35,
        },
        "message": "Vehículo en zona restringida",
        "cooldown_seconds": 25,
    },
    {
        "id": "preset-escalera-insegura",
        "name": "Persona cerca de escalera portátil",
        "enabled": False,
        "severity": "medium",
        "sources": ["*"],
        "condition": {
            "type": "proximity",
            "subject_keywords": KEYWORDS["persona"],
            "object_keywords": KEYWORDS["escalera"],
            "max_distance_meters": 2.0,
            "max_distance_ratio": 0.1,
            "min_conf": 0.3,
        },
        "message": "Proximidad a escalera — revisar uso seguro",
        "cooldown_seconds": 35,
    },
    {
        "id": "preset-near-miss-camion",
        "name": "Near-miss: camión en vía de peatones",
        "enabled": False,
        "severity": "high",
        "sources": ["*"],
        "condition": {
            "type": "detect_in_zone",
            "detect_keywords": KEYWORDS["vehiculo"],
            "zone_types": ["vehicle_lane"],
            "min_overlap": 0.22,
            "min_conf": 0.35,
        },
        "message": "Vehículo pesado en vía de tránsito peatonal",
        "cooldown_seconds": 20,
    },
    {
        "id": "preset-prox-soldadura",
        "name": "Persona cerca de zona de soldadura",
        "enabled": False,
        "severity": "medium",
        "sources": ["*"],
        "condition": {
            "type": "proximity",
            "subject_keywords": KEYWORDS["persona"],
            "object_keywords": KEYWORDS["soldadura"],
            "max_distance_meters": 3.0,
            "max_distance_ratio": 0.14,
            "min_conf": 0.3,
        },
        "message": "Persona cerca de trabajo de soldadura sin delimitación",
        "cooldown_seconds": 30,
    },
    {
        "id": "preset-ergonomia-espacio-confinado",
        "name": "Persona en espacio confinado (zona restringida)",
        "enabled": False,
        "severity": "medium",
        "sources": ["*"],
        "condition": {"type": "person_in_zone", "zone_types": ["restricted"], "min_overlap": 0.45},
        "message": "Persona en espacio confinado — verificar permiso de trabajo",
        "cooldown_seconds": 40,
    },
    {
        "id": "preset-izaje-zona-maquinaria",
        "name": "Persona en zona de izaje activo",
        "enabled": False,
        "severity": "high",
        "sources": ["*"],
        "condition": {"type": "person_in_zone", "zone_types": ["machinery"], "min_overlap": 0.35},
        "message": "Persona en zona de izaje / maquinaria",
        "cooldown_seconds": 25,
    },
    {
        "id": "preset-carga-patio",
        "name": "Persona en patio de carga",
        "enabled": False,
        "severity": "medium",
        "sources": ["*"],
        "condition": {
            "type": "detect_in_zone",
            "detect_keywords": KEYWORDS["persona"],
            "zone_types": ["vehicle_lane"],
            "min_overlap": 0.3,
            "min_conf": 0.2,
        },
        "message": "Persona en patio de carga — riesgo de atropello",
        "cooldown_seconds": 25,
    },
    {
        "id": "preset-doble-riesgo-maquinaria",
        "name": "Persona + maquinaria en misma zona",
        "enabled": False,
        "severity": "high",
        "sources": ["*"],
        "condition": {
            "type": "proximity",
            "subject_keywords": KEYWORDS["persona"],
            "object_keywords": KEYWORDS["montacargas"] + KEYWORDS["vehiculo"],
            "max_distance_meters": 5.0,
            "max_distance_ratio": 0.18,
            "min_conf": 0.28,
        },
        "message": "Coexistencia persona–maquinaria en sector operativo",
        "cooldown_seconds": 30,
    },
    {
        "id": "preset-sin-casco-prox-grua",
        "name": "Proximidad a grúa (refuerzo SIF)",
        "enabled": False,
        "severity": "high",
        "sources": ["*"],
        "condition": {
            "type": "proximity",
            "subject_keywords": KEYWORDS["persona"],
            "object_keywords": KEYWORDS["grua"] + KEYWORDS["carga_suspendida"],
            "max_distance_meters": 3.5,
            "max_distance_ratio": 0.14,
            "min_conf": 0.25,
        },
        "message": "Persona en radio de izaje — verificar EPP y delimitación",
        "cooldown_seconds": 25,
    },
]


def _default_payload() -> dict[str, Any]:
    return {
        "rules": [dict(r) for r in PRESET_RULES],
        "settings": dict(DEFAULT_SETTINGS),
        "updated_at": None,
    }


def get_settings() -> dict[str, Any]:
    data = get_rules()
    settings = dict(DEFAULT_SETTINGS)
    settings.update(data.get("settings") or {})
    settings["meters_per_pixel"] = max(0.01, min(0.5, float(settings.get("meters_per_pixel") or 0.045)))
    settings["action_audio_enabled"] = bool(settings.get("action_audio_enabled", True))
    sev = settings.get("action_audio_severities")
    if not isinstance(sev, list):
        sev = list(DEFAULT_SETTINGS["action_audio_severities"])
    settings["action_audio_severities"] = [s for s in sev if s in ("critical", "high", "medium", "low")]
    if not settings["action_audio_severities"]:
        settings["action_audio_severities"] = ["critical", "high"]
    return settings


def save_settings(settings: dict[str, Any]) -> dict[str, Any]:
    data = get_rules()
    merged = dict(DEFAULT_SETTINGS)
    merged.update(data.get("settings") or {})
    merged.update(settings or {})
    merged["meters_per_pixel"] = max(0.01, min(0.5, float(merged.get("meters_per_pixel") or 0.045)))
    merged["action_audio_enabled"] = bool(merged.get("action_audio_enabled", True))
    sev = merged.get("action_audio_severities")
    if not isinstance(sev, list):
        sev = list(DEFAULT_SETTINGS["action_audio_severities"])
    merged["action_audio_severities"] = [s for s in sev if s in ("critical", "high", "medium", "low")]
    if not merged["action_audio_severities"]:
        merged["action_audio_severities"] = ["critical", "high"]
    payload = {"rules": data.get("rules") or [], "settings": merged, "updated_at": datetime.now(UTC).isoformat()}
    with _lock:
        ACTIONS_FILE.parent.mkdir(parents=True, exist_ok=True)
        ACTIONS_FILE.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return payload


def _proximity_max_ratio(cond: dict[str, Any], frame_w: int, frame_h: int, settings: dict[str, Any]) -> float:
    if cond.get("max_distance_meters") is not None:
        mpp = float(settings.get("meters_per_pixel") or 0.045)
        diag = (frame_w**2 + frame_h**2) ** 0.5
        max_px = float(cond["max_distance_meters"]) / max(mpp, 1e-6)
        return max_px / max(1.0, diag)
    return float(cond.get("max_distance_ratio") or 0.14)


def get_rules() -> dict[str, Any]:
    with _lock:
        if not ACTIONS_FILE.exists():
            return _default_payload()
        try:
            data = json.loads(ACTIONS_FILE.read_text(encoding="utf-8"))
            if not isinstance(data.get("rules"), list):
                return _default_payload()
            return data
        except (json.JSONDecodeError, OSError):
            return _default_payload()


def save_rules(rules: list[dict[str, Any]]) -> dict[str, Any]:
    cleaned = []
    for r in rules:
        if not isinstance(r, dict) or not r.get("id"):
            continue
        cleaned.append(r)
    existing = get_rules()
    payload = {
        "rules": cleaned,
        "settings": existing.get("settings") or dict(DEFAULT_SETTINGS),
        "updated_at": datetime.now(UTC).isoformat(),
    }
    with _lock:
        ACTIONS_FILE.parent.mkdir(parents=True, exist_ok=True)
        ACTIONS_FILE.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    try:
        from . import cloud_persist as cloud_mod

        cloud_mod.schedule_push()
    except Exception:  # noqa: BLE001
        pass
    return payload


def list_presets() -> list[dict[str, Any]]:
    return [{"id": p["id"], "name": p["name"], "severity": p["severity"]} for p in PRESET_RULES]


def _label_text(det: dict[str, Any]) -> str:
    return f"{det.get('label') or ''} {det.get('label_es') or ''}".lower()


def _matches_keywords(det: dict[str, Any], keywords: list[str], min_conf: float = 0.0) -> bool:
    if float(det.get("confidence") or 0) < min_conf:
        return False
    lab = _label_text(det)
    return any(k.lower() in lab for k in keywords)


def _persons(detections: list[dict[str, Any]], frame_w: int, frame_h: int) -> list[dict[str, Any]]:
    persons = [d for d in detections if _is_person(d) and d.get("box")]
    if not persons:
        persons = [
            d
            for d in detections
            if d.get("box")
            and (d["box"][2] - d["box"][0]) * (d["box"][3] - d["box"][1]) > (frame_w * frame_h * 0.04)
        ]
    return persons


def _source_matches(rule: dict[str, Any], source_id: str) -> bool:
    sources = rule.get("sources") or ["*"]
    if "*" in sources:
        return True
    sid = source_id or "live"
    for s in sources:
        if s == sid:
            return True
        if s.endswith("*") and sid.startswith(s[:-1]):
            return True
    return False


def _cooldown_ok(rule_id: str, source_id: str, cooldown: int) -> bool:
    if cooldown <= 0:
        return True
    key = f"{rule_id}|{source_id or 'live'}"
    now = time.time()
    prev = _last_trigger.get(key, 0)
    if now - prev < cooldown:
        return False
    _last_trigger[key] = now
    return True


def _trigger(rule: dict[str, Any], source_id: str, extra: dict[str, Any] | None = None) -> dict[str, Any]:
    return {
        "rule_id": rule["id"],
        "name": rule.get("name") or rule["id"],
        "severity": rule.get("severity") or "medium",
        "message": rule.get("message") or rule.get("name") or "Acción insegura",
        "source": source_id or "live",
        **(extra or {}),
    }


def evaluate_actions(
    detections: list[dict[str, Any]],
    frame_w: int,
    frame_h: int,
    *,
    source_id: str = "live",
    compliance: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Evalúa reglas habilitadas para la fuente dada."""
    data = get_rules()
    rules = [r for r in data.get("rules") or [] if r.get("enabled")]
    settings = get_settings()
    zones = zones_for_source(source_id)
    triggered: list[dict[str, Any]] = []
    alerts: list[str] = []

    if frame_w <= 0 or frame_h <= 0:
        return {"triggered": [], "alerts": [], "rules_count": len(rules)}

    persons = _persons(detections, frame_w, frame_h)
    compliance = compliance or {}

    for rule in rules:
        if not _source_matches(rule, source_id):
            continue
        cond = rule.get("condition") or {}
        ctype = cond.get("type") or ""
        cooldown = int(rule.get("cooldown_seconds") or 20)
        hit = False
        extra: dict[str, Any] = {}

        if ctype == "epp_non_compliant":
            persons_c = compliance.get("persons") or []
            if persons_c and not compliance.get("overall_compliant"):
                hit = True
                miss = []
                for p in persons_c:
                    miss.extend(p.get("missing") or [])
                extra["missing"] = miss[:6]

        elif ctype == "fall_detected":
            for p in compliance.get("persons") or []:
                if "caida" in [str(v).lower() for v in (p.get("violations") or [])]:
                    hit = True
                    break
            if not hit:
                for d in detections:
                    if "fall" in _label_text(d) or "caída" in _label_text(d) or "caida" in _label_text(d):
                        hit = True
                        break

        elif ctype == "person_in_zone":
            ztypes = set(cond.get("zone_types") or [])
            min_ov = float(cond.get("min_overlap") or 0.28)
            for z in zones:
                if ztypes and z.get("type") not in ztypes:
                    continue
                for d in persons:
                    if _overlap_ratio(d["box"], z, frame_w, frame_h) >= min_ov:
                        hit = True
                        extra["zone_id"] = z["id"]
                        extra["zone_name"] = z["name"]
                        break
                if hit:
                    break

        elif ctype == "detect_in_zone":
            kws = cond.get("detect_keywords") or []
            ztypes = set(cond.get("zone_types") or [])
            min_ov = float(cond.get("min_overlap") or 0.15)
            min_conf = float(cond.get("min_conf") or 0.3)
            targets = [d for d in detections if _matches_keywords(d, kws, min_conf) and d.get("box")]
            for z in zones:
                if ztypes and z.get("type") not in ztypes:
                    continue
                for d in targets:
                    if _overlap_ratio(d["box"], z, frame_w, frame_h) >= min_ov:
                        hit = True
                        extra["zone_name"] = z["name"]
                        extra["detect_label"] = d.get("label_es") or d.get("label")
                        break
                if hit:
                    break

        elif ctype == "proximity":
            subj_kw = cond.get("subject_keywords") or KEYWORDS["persona"]
            obj_kw = cond.get("object_keywords") or []
            max_ratio = _proximity_max_ratio(cond, frame_w, frame_h, settings)
            min_conf = float(cond.get("min_conf") or 0.25)
            diag = (frame_w**2 + frame_h**2) ** 0.5
            subs = persons if persons else [d for d in detections if _matches_keywords(d, subj_kw, 0) and d.get("box")]
            objs = [d for d in detections if _matches_keywords(d, obj_kw, min_conf) and d.get("box")]
            for s in subs:
                sx = (s["box"][0] + s["box"][2]) / 2
                sy = (s["box"][1] + s["box"][3]) / 2
                for o in objs:
                    if s is o:
                        continue
                    ox = (o["box"][0] + o["box"][2]) / 2
                    oy = (o["box"][1] + o["box"][3]) / 2
                    dist = ((sx - ox) ** 2 + (sy - oy) ** 2) ** 0.5
                    if dist / max(1.0, diag) <= max_ratio:
                        hit = True
                        extra["object_label"] = o.get("label_es") or o.get("label")
                        extra["distance_ratio"] = round(dist / diag, 3)
                        break
                if hit:
                    break

        elif ctype == "detect_anywhere":
            kws = cond.get("detect_keywords") or []
            min_conf = float(cond.get("min_conf") or 0.3)
            for d in detections:
                if _matches_keywords(d, kws, min_conf) and d.get("box"):
                    hit = True
                    extra["detect_label"] = d.get("label_es") or d.get("label")
                    break

        if hit and _cooldown_ok(str(rule["id"]), source_id, cooldown):
            tr = _trigger(rule, source_id, extra)
            triggered.append(tr)
            msg = tr["message"]
            if msg not in alerts:
                alerts.append(msg)

    return {"triggered": triggered, "alerts": alerts, "rules_count": len(rules)}


def log_action_event(triggered: dict[str, Any]) -> None:
    """Append a JSONL event (best-effort)."""
    path = data_dir() / "action_events.jsonl"
    line = {**triggered, "ts": datetime.now(UTC).isoformat()}
    try:
        with path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(line, ensure_ascii=False) + "\n")
    except OSError:
        pass


def list_action_events(
    *,
    limit: int = 100,
    severity: str | None = None,
    source_id: str | None = None,
) -> list[dict[str, Any]]:
    """Últimos eventos de acciones inseguras (más recientes primero)."""
    path = data_dir() / "action_events.jsonl"
    if not path.is_file():
        return []
    limit = max(1, min(500, int(limit)))
    lines: list[str] = []
    try:
        with path.open(encoding="utf-8") as fh:
            for line in fh:
                if line.strip():
                    lines.append(line)
    except OSError:
        return []
    events: list[dict[str, Any]] = []
    for raw in reversed(lines):
        try:
            ev = json.loads(raw)
        except json.JSONDecodeError:
            continue
        if severity and (ev.get("severity") or "") != severity:
            continue
        if source_id and (ev.get("source") or "") != source_id:
            continue
        events.append(ev)
        if len(events) >= limit:
            break
    return events


def should_play_action_audio(severity: str) -> bool:
    settings = get_settings()
    if not settings.get("action_audio_enabled", True):
        return False
    allowed = settings.get("action_audio_severities") or ["critical", "high"]
    return (severity or "medium") in allowed


def add_rule_from_preset(preset_id: str) -> dict[str, Any]:
    preset = next((p for p in PRESET_RULES if p["id"] == preset_id), None)
    if not preset:
        raise ValueError(f"Preset desconocido: {preset_id}")
    data = get_rules()
    rules = list(data.get("rules") or [])
    if any(r.get("id") == preset_id for r in rules):
        return {"ok": True, "message": "La regla ya existe", "rules": rules}
    rules.append(dict(preset))
    save_rules(rules)
    return {"ok": True, "message": f"Regla añadida: {preset['name']}", "rules": rules}


def create_custom_rule(name: str, condition_type: str, **kwargs: Any) -> dict[str, Any]:
    rid = f"rule-{uuid.uuid4().hex[:10]}"
    rule = {
        "id": rid,
        "name": name.strip() or "Regla personalizada",
        "enabled": True,
        "severity": kwargs.get("severity") or "medium",
        "sources": kwargs.get("sources") or ["*"],
        "condition": kwargs.get("condition") or {"type": condition_type},
        "message": kwargs.get("message") or name,
        "cooldown_seconds": int(kwargs.get("cooldown_seconds") or 25),
    }
    data = get_rules()
    rules = list(data.get("rules") or [])
    rules.append(rule)
    save_rules(rules)
    return {"ok": True, "rule": rule, "rules": rules}
