"""Conectores EHS — exportación de incidentes a plataformas externas."""

from __future__ import annotations

import json
import logging
import threading
from datetime import datetime, timezone
from typing import Any
from urllib.request import Request, urlopen

from .paths import data_dir
from .security_urls import validate_outbound_url

logger = logging.getLogger("vigiepp.ehs")

_lock = threading.Lock()
_CONFIG_FILE = "ehs_connectors.json"

DEFAULT_CONNECTORS: dict[str, dict[str, Any]] = {
    "webhook": {
        "id": "webhook",
        "name": "Webhook genérico",
        "enabled": False,
        "url": "",
        "auth_header": "",
        "format": "vigiepp",
    },
    "safetycloud": {
        "id": "safetycloud",
        "name": "SafetyCloud / JSON EHS",
        "enabled": False,
        "url": "",
        "api_key": "",
        "site_code": "",
    },
    "sap_ewm": {
        "id": "sap_ewm",
        "name": "SAP EWM incident stub",
        "enabled": False,
        "url": "",
        "client_id": "",
        "plant": "",
    },
}


def _config_path() -> Any:
    return data_dir() / _CONFIG_FILE


def _load() -> dict[str, Any]:
    path = _config_path()
    if not path.is_file():
        return {"connectors": dict(DEFAULT_CONNECTORS), "updated_at": None}
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(raw, dict):
            merged = dict(DEFAULT_CONNECTORS)
            for k, v in (raw.get("connectors") or {}).items():
                if isinstance(v, dict):
                    base = dict(merged.get(k) or {})
                    base.update(v)
                    merged[k] = base
            return {"connectors": merged, "updated_at": raw.get("updated_at")}
    except json.JSONDecodeError:
        pass
    return {"connectors": dict(DEFAULT_CONNECTORS), "updated_at": None}


def _save(payload: dict[str, Any]) -> None:
    payload["updated_at"] = datetime.now(timezone.utc).isoformat()
    path = _config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def get_config() -> dict[str, Any]:
    with _lock:
        data = _load()
    connectors = data.get("connectors") or {}
    public = {}
    for cid, cfg in connectors.items():
        pub = {k: v for k, v in cfg.items() if k not in ("api_key", "auth_header", "client_id")}
        pub["api_key_set"] = bool(cfg.get("api_key"))
        pub["auth_header_set"] = bool(cfg.get("auth_header"))
        public[cid] = pub
    return {"connectors": public, "updated_at": data.get("updated_at")}


def save_config(patch: dict[str, Any]) -> dict[str, Any]:
    with _lock:
        data = _load()
        connectors = data.get("connectors") or dict(DEFAULT_CONNECTORS)
        for cid, upd in (patch.get("connectors") or {}).items():
            if not isinstance(upd, dict):
                continue
            base = dict(connectors.get(cid) or DEFAULT_CONNECTORS.get(cid) or {})
            base.update(upd)
            connectors[cid] = base
        data["connectors"] = connectors
        _save(data)
    return get_config()


def _format_payload(connector_id: str, incident: dict[str, Any]) -> dict[str, Any]:
    if connector_id == "safetycloud":
        return {
            "source": "VigiEPP",
            "type": "ppe_incident",
            "site": incident.get("site") or "",
            "timestamp": incident.get("ts") or datetime.now(timezone.utc).isoformat(),
            "worker": {
                "name": incident.get("worker_name"),
                "rut": incident.get("worker_rut"),
                "id": incident.get("worker_id"),
            },
            "profile": incident.get("profile"),
            "compliant": incident.get("compliant"),
            "summary": incident.get("summary"),
            "missing_ppe": incident.get("missing") or [],
            "evidence_id": incident.get("evidence_id"),
        }
    if connector_id == "sap_ewm":
        return {
            "IncidentType": "PPE_NON_COMPLIANCE",
            "Plant": incident.get("plant") or "",
            "Description": incident.get("summary") or "Incumplimiento EPP",
            "PersonnelId": incident.get("worker_rut") or "",
            "Timestamp": incident.get("ts") or datetime.now(timezone.utc).isoformat(),
        }
    return {
        "ok": True,
        "kind": "ppe_incident",
        "incident": incident,
    }


def _post_json(url: str, body: dict[str, Any], headers: dict[str, str] = None) -> tuple[bool, str]:
    ok, msg = validate_outbound_url(url)
    if not ok:
        return False, msg
    data = json.dumps(body, ensure_ascii=False).encode("utf-8")
    hdrs = {"Content-Type": "application/json", "User-Agent": "VigiEPP-EHS/1.0"}
    if headers:
        hdrs.update(headers)
    try:
        req = Request(url, data=data, method="POST", headers=hdrs)
        with urlopen(req, timeout=12) as resp:  # noqa: S310
            return True, f"HTTP {resp.status}"
    except Exception as exc:  # noqa: BLE001
        return False, str(exc)


def push_incident(incident: dict[str, Any]) -> list[dict[str, Any]]:
    """Envía incidente a conectores EHS habilitados."""
    with _lock:
        data = _load()
        connectors = data.get("connectors") or {}
    results: list[dict[str, Any]] = []
    for cid, cfg in connectors.items():
        if not cfg.get("enabled"):
            continue
        url = str(cfg.get("url") or "").strip()
        if not url:
            results.append({"connector": cid, "ok": False, "error": "URL vacía"})
            continue
        payload = _format_payload(cid, incident)
        headers: dict[str, str] = {}
        if cfg.get("auth_header"):
            headers["Authorization"] = str(cfg["auth_header"])
        if cfg.get("api_key"):
            headers["X-API-Key"] = str(cfg["api_key"])
        ok, msg = _post_json(url, payload, headers)
        results.append({"connector": cid, "ok": ok, "detail": msg})
        if not ok:
            logger.warning("EHS push %s falló: %s", cid, msg)
    return results


def test_connector(connector_id: str) -> dict[str, Any]:
    sample = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "worker_name": "Prueba EHS",
        "worker_rut": "11.111.111-1",
        "profile": "general",
        "compliant": False,
        "summary": "Prueba conector EHS VigiEPP",
        "missing": ["casco"],
        "site": "faena-test",
    }
    with _lock:
        data = _load()
        cfg = (data.get("connectors") or {}).get(connector_id)
    if not cfg:
        return {"ok": False, "error": "Conector no encontrado"}
    url = str(cfg.get("url") or "").strip()
    if not url:
        return {"ok": False, "error": "URL requerida"}
    payload = _format_payload(connector_id, sample)
    headers: dict[str, str] = {}
    if cfg.get("auth_header"):
        headers["Authorization"] = str(cfg["auth_header"])
    if cfg.get("api_key"):
        headers["X-API-Key"] = str(cfg["api_key"])
    ok, msg = _post_json(url, payload, headers)
    return {"ok": ok, "detail": msg, "connector": connector_id}
