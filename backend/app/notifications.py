"""Configuración y envío de notificaciones (webhook + registro local)."""

from __future__ import annotations

import json
import threading
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .paths import data_dir

DATA_DIR = data_dir()
CONFIG_FILE = DATA_DIR / "notifications.json"
LOG_FILE = DATA_DIR / "notification_log.jsonl"
_lock = threading.Lock()

DEFAULT_CONFIG: dict[str, Any] = {
    "enabled": False,
    "on_non_compliant": True,
    "on_unknown_face": True,
    "only_known_workers": True,
    "cooldown_seconds": 120,
    "access_control": {
        "enabled": False,
        "require_identity": True,
        "notify": True,
    },
    "channels": {
        "webhook": {"enabled": False, "url": ""},
        "email": {"enabled": False, "to": "", "cc": ""},
        "whatsapp_webhook": {"enabled": False, "url": ""},
    },
    "template": {
        "subject": "Alerta VigiEPP — incumplimiento EPP",
        "body": "Trabajador: {name}\nRUT: {rut}\nPerfil: {profile}\nDetalle: {summary}\nFaltantes: {missing}\nFecha: {ts}",
    },
    "recipients_extra": [],
}


def _ensure() -> None:
    global DATA_DIR, CONFIG_FILE, LOG_FILE
    DATA_DIR = data_dir()
    CONFIG_FILE = DATA_DIR / "notifications.json"
    LOG_FILE = DATA_DIR / "notification_log.jsonl"
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if not CONFIG_FILE.exists():
        CONFIG_FILE.write_text(
            json.dumps(DEFAULT_CONFIG, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )


def get_config() -> dict[str, Any]:
    _ensure()
    with _lock:
        raw = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
    # merge defaults
    cfg = json.loads(json.dumps(DEFAULT_CONFIG))
    cfg.update({k: v for k, v in raw.items() if k not in ("channels", "template", "access_control")})
    if isinstance(raw.get("access_control"), dict):
        cfg.setdefault("access_control", {})
        cfg["access_control"].update(raw["access_control"])
    if isinstance(raw.get("channels"), dict):
        for k, v in raw["channels"].items():
            cfg["channels"].setdefault(k, {})
            if isinstance(v, dict):
                cfg["channels"][k].update(v)
    if isinstance(raw.get("template"), dict):
        cfg["template"].update(raw["template"])
    if isinstance(raw.get("recipients_extra"), list):
        cfg["recipients_extra"] = raw["recipients_extra"]
    return cfg


def save_config(patch: dict[str, Any]) -> dict[str, Any]:
    cfg = get_config()
    for key in ("enabled", "on_non_compliant", "on_unknown_face", "only_known_workers", "cooldown_seconds"):
        if key in patch:
            cfg[key] = patch[key]
    if isinstance(patch.get("access_control"), dict):
        cfg.setdefault("access_control", {})
        cfg["access_control"].update(patch["access_control"])
    if isinstance(patch.get("channels"), dict):
        for name, ch in patch["channels"].items():
            cfg["channels"].setdefault(name, {})
            if isinstance(ch, dict):
                cfg["channels"][name].update(ch)
    if isinstance(patch.get("template"), dict):
        cfg["template"].update(patch["template"])
    if isinstance(patch.get("recipients_extra"), list):
        cfg["recipients_extra"] = patch["recipients_extra"]
    with _lock:
        CONFIG_FILE.write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")
    return cfg


def _format_message(cfg: dict[str, Any], payload: dict[str, Any]) -> tuple[str, str]:
    tpl = cfg.get("template") or {}
    ctx = {
        "name": payload.get("name") or "Desconocido",
        "rut": payload.get("rut") or "—",
        "profile": payload.get("profile") or "—",
        "summary": payload.get("summary") or "—",
        "missing": ", ".join(payload.get("missing") or []) or "—",
        "ts": payload.get("ts") or datetime.now(timezone.utc).isoformat(),
    }
    subject = str(tpl.get("subject") or "Alerta VigiEPP").format(**ctx)
    body = str(tpl.get("body") or "{summary}").format(**ctx)
    return subject, body


def _post_json(url: str, data: dict[str, Any], timeout: float = 8.0) -> tuple[bool, str]:
    if not url or not url.startswith(("http://", "https://")):
        return False, "URL inválida"
    req = urllib.request.Request(
        url,
        data=json.dumps(data).encode("utf-8"),
        headers={"Content-Type": "application/json", "User-Agent": "VigiEPP/1.0"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return True, f"HTTP {resp.status}"
    except urllib.error.HTTPError as exc:
        return False, f"HTTP {exc.code}"
    except Exception as exc:  # noqa: BLE001
        return False, str(exc)


def _append_log(entry: dict[str, Any]) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with _lock:
        with LOG_FILE.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(entry, ensure_ascii=False) + "\n")


def recent_log(limit: int = 30) -> list[dict[str, Any]]:
    if not LOG_FILE.exists():
        return []
    with _lock:
        lines = LOG_FILE.read_text(encoding="utf-8").strip().splitlines()
    out: list[dict[str, Any]] = []
    for line in reversed(lines):
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            continue
        if len(out) >= limit:
            break
    return out


_last_sent_at: float = 0.0


def send_notification(
    payload: dict[str, Any],
    *,
    force: bool = False,
    kind: str = "alert",
) -> dict[str, Any]:
    global _last_sent_at
    cfg = get_config()
    if not force and not cfg.get("enabled"):
        return {"ok": False, "skipped": True, "reason": "notificaciones desactivadas"}

    now = datetime.now(timezone.utc).timestamp()
    cooldown = float(cfg.get("cooldown_seconds") or 0)
    if not force and cooldown > 0 and (now - _last_sent_at) < cooldown:
        return {"ok": False, "skipped": True, "reason": "cooldown"}

    if cfg.get("only_known_workers") and not payload.get("worker_id") and not force:
        return {"ok": False, "skipped": True, "reason": "solo trabajadores conocidos"}

    subject, body = _format_message(cfg, payload)
    channels = cfg.get("channels") or {}
    results: list[dict[str, Any]] = []

    wh = channels.get("webhook") or {}
    if wh.get("enabled") and wh.get("url"):
        ok, detail = _post_json(
            str(wh["url"]),
            {
                "text": f"{subject}\n{body}",
                "content": f"{subject}\n{body}",
                "source": "VigiEPP",
                "kind": kind,
                "payload": payload,
            },
        )
        results.append({"channel": "webhook", "ok": ok, "detail": detail})

    wa = channels.get("whatsapp_webhook") or {}
    if wa.get("enabled") and wa.get("url"):
        ok, detail = _post_json(
            str(wa["url"]),
            {"message": body, "subject": subject, "source": "VigiEPP", "payload": payload},
        )
        results.append({"channel": "whatsapp_webhook", "ok": ok, "detail": detail})

    email = channels.get("email") or {}
    mailto = None
    if email.get("enabled") and email.get("to"):
        # No SMTP obligatorio: dejamos mailto listo + registro
        from urllib.parse import quote

        mailto = f"mailto:{email['to']}?subject={quote(subject)}&body={quote(body)}"
        results.append({"channel": "email", "ok": True, "detail": "mailto_ready", "mailto": mailto})

    if not results:
        results.append({"channel": "none", "ok": False, "detail": "sin canales activos"})

    any_ok = any(r.get("ok") for r in results)
    if any_ok:
        _last_sent_at = now

    entry = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "kind": kind,
        "ok": any_ok,
        "subject": subject,
        "body": body,
        "payload": payload,
        "results": results,
        "mailto": mailto,
    }
    _append_log(entry)
    return {"ok": any_ok, "subject": subject, "body": body, "results": results, "mailto": mailto}


def maybe_notify_scan(identity: dict[str, Any] | None, compliance: dict[str, Any], profile: str) -> None:
    cfg = get_config()
    if not cfg.get("enabled") or not cfg.get("on_non_compliant"):
        return
    if compliance.get("overall_compliant"):
        return
    persons = compliance.get("persons") or []
    missing: list[str] = []
    for p in persons:
        missing.extend(p.get("missing") or [])
    send_notification(
        {
            "name": (identity or {}).get("name"),
            "rut": (identity or {}).get("rut"),
            "worker_id": (identity or {}).get("id"),
            "profile": profile,
            "summary": compliance.get("summary"),
            "missing": missing,
            "ts": datetime.now(timezone.utc).isoformat(),
            "compliant": False,
        },
        force=False,
        kind="non_compliant",
    )


def maybe_notify_unknown(identity: dict[str, Any] | None, profile: str) -> None:
    """Alerta cuando hay rostro pero no está enrolado (o inactivo)."""
    cfg = get_config()
    if not cfg.get("enabled") or not cfg.get("on_unknown_face"):
        return
    send_notification(
        {
            "name": (identity or {}).get("name") or "Desconocido",
            "rut": (identity or {}).get("rut") or "—",
            "worker_id": None,
            "profile": profile,
            "summary": "Rostro detectado sin identidad enrolada / activa",
            "missing": ["identidad"],
            "ts": datetime.now(timezone.utc).isoformat(),
            "compliant": False,
            "faces_detected": (identity or {}).get("faces_detected"),
            "score": (identity or {}).get("score"),
        },
        force=True,  # no exigir worker_id
        kind="unknown_face",
    )


def maybe_access_gate(
    identity: dict[str, Any] | None,
    compliance: dict[str, Any],
    profile: str,
) -> dict[str, Any] | None:
    """
    Señal para torniquete / relé: allow solo si identidad conocida + EPP OK.
    Usa canal webhook con kind access_allow / access_deny si access_control.enabled.
    """
    cfg = get_config()
    access = cfg.get("access_control") or {}
    if not access.get("enabled"):
        return None
    known = bool((identity or {}).get("known") and (identity or {}).get("id"))
    ok_epp = bool(compliance.get("overall_compliant"))
    allow = known and ok_epp
    if access.get("require_identity", True) and not known:
        allow = False
    payload = {
        "allow": allow,
        "action": "open" if allow else "deny",
        "name": (identity or {}).get("name"),
        "rut": (identity or {}).get("rut"),
        "worker_id": (identity or {}).get("id"),
        "profile": profile,
        "summary": "Acceso permitido" if allow else "Acceso denegado (identidad o EPP)",
        "missing": [] if allow else (["identidad"] if not known else []),
        "ts": datetime.now(timezone.utc).isoformat(),
        "compliant": ok_epp,
    }
    # Enviar solo si hay cambio o force via cooldown del send_notification
    if cfg.get("enabled") and access.get("notify", True):
        send_notification(payload, force=True, kind="access_allow" if allow else "access_deny")
    return payload

