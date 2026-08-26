"""Configuración y envío de notificaciones (webhook + email real + registro)."""

from __future__ import annotations

import json
import os
import smtplib
import ssl
import threading
import urllib.error
import urllib.request
from datetime import datetime, timezone
from email.message import EmailMessage
from pathlib import Path
from typing import Any
from urllib.parse import quote

from . import hardware_alarm as hw_mod
from . import access_gate as gate_mod
from . import whatsapp_cloud as wa_mod
from .paths import data_dir

DATA_DIR = data_dir()
CONFIG_FILE = DATA_DIR / "notifications.json"
LOG_FILE = DATA_DIR / "notification_log.jsonl"
_lock = threading.Lock()

DEFAULT_CONFIG: dict[str, Any] = {
    "enabled": False,
    "on_non_compliant": True,
    "on_unknown_face": True,
    "on_zone_alert": True,
    "only_known_workers": True,
    "cooldown_seconds": 120,
    "access_control": {
        "enabled": False,
        "require_identity": True,
        "notify": True,
        "hardware": dict(hw_mod.DEFAULT_HARDWARE),
        "gate": dict(gate_mod.DEFAULT_GATE),
    },
    "channels": {
        "webhook": {"enabled": False, "url": ""},
        "email": {"enabled": False, "to": "", "cc": ""},
        "whatsapp_webhook": {"enabled": False, "url": ""},
        "whatsapp_cloud": {"enabled": False, "phone_number_id": "", "to": ""},
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


def refresh_paths() -> None:
    """Rebind paths tras cambio de sitio activo."""
    _ensure()


def get_config() -> dict[str, Any]:
    _ensure()
    with _lock:
        raw = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
    cfg = json.loads(json.dumps(DEFAULT_CONFIG))
    cfg.update({k: v for k, v in raw.items() if k not in ("channels", "template", "access_control")})
    if isinstance(raw.get("access_control"), dict):
        cfg.setdefault("access_control", {})
        ac_raw = raw["access_control"]
        hw_raw = ac_raw.get("hardware") if isinstance(ac_raw.get("hardware"), dict) else {}
        gate_raw = ac_raw.get("gate") if isinstance(ac_raw.get("gate"), dict) else ac_raw
        cfg["access_control"].update({k: v for k, v in ac_raw.items() if k not in ("hardware", "gate")})
        cfg["access_control"]["hardware"] = hw_mod.merge_hardware(hw_raw)
        cfg["access_control"]["gate"] = gate_mod.merge_gate(gate_raw)
    else:
        cfg.setdefault("access_control", {})
        cfg["access_control"]["hardware"] = hw_mod.merge_hardware(
            (cfg.get("access_control") or {}).get("hardware")
        )
        cfg["access_control"]["gate"] = gate_mod.merge_gate(
            (cfg.get("access_control") or {}).get("gate")
        )
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
    for key in (
        "enabled",
        "on_non_compliant",
        "on_unknown_face",
        "on_zone_alert",
        "only_known_workers",
        "cooldown_seconds",
    ):
        if key in patch:
            cfg[key] = patch[key]
    if isinstance(patch.get("access_control"), dict):
        cfg.setdefault("access_control", {})
        ac_patch = patch["access_control"]
        hw_patch = ac_patch.get("hardware") if isinstance(ac_patch.get("hardware"), dict) else None
        gate_patch = ac_patch.get("gate") if isinstance(ac_patch.get("gate"), dict) else None
        cfg["access_control"].update(
            {k: v for k, v in ac_patch.items() if k not in ("hardware", "gate")}
        )
        if hw_patch is not None:
            current_hw = hw_mod.merge_hardware(cfg["access_control"].get("hardware"))
            current_hw.update(hw_patch)
            base = str(current_hw.get("base_url") or "").strip()
            if base:
                ok_u, normalized = hw_mod.validate_base_url(base)
                if not ok_u:
                    raise ValueError(f"URL ESP32 inválida: {normalized}")
                current_hw["base_url"] = normalized
            else:
                current_hw["base_url"] = ""
            cfg["access_control"]["hardware"] = current_hw
        if gate_patch is not None:
            merged = gate_mod.merge_gate(cfg["access_control"].get("gate"))
            for k, v in gate_patch.items():
                if k in ("esp32", "modbus", "http_dual", "wiegand") and isinstance(v, dict):
                    merged[k].update(v)
                elif k in merged:
                    merged[k] = v
            cfg["access_control"]["gate"] = gate_mod.merge_gate(merged)
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
    try:
        from . import cloud_persist as cloud_mod

        cloud_mod.schedule_push()
    except Exception:  # noqa: BLE001
        pass
    return cfg


def email_transport_status() -> dict[str, Any]:
    """Qué backend de email está disponible (sin secretos)."""
    resend = bool(os.getenv("RESEND_API_KEY", "").strip() or os.getenv("VIGIEPP_RESEND_API_KEY", "").strip())
    smtp_host = os.getenv("VIGIEPP_SMTP_HOST", os.getenv("SMTP_HOST", "")).strip()
    smtp_user = os.getenv("VIGIEPP_SMTP_USER", os.getenv("SMTP_USER", "")).strip()
    smtp_pass = os.getenv("VIGIEPP_SMTP_PASS", os.getenv("SMTP_PASS", "")).strip()
    smtp_from = os.getenv("VIGIEPP_SMTP_FROM", os.getenv("SMTP_FROM", "")).strip()
    smtp_ok = bool(smtp_host and smtp_from)
    mode = "resend" if resend else ("smtp" if smtp_ok else "mailto")
    return {
        "mode": mode,
        "resend": resend,
        "smtp": smtp_ok,
        "smtp_host": smtp_host or None,
        "smtp_from": smtp_from or None,
        "smtp_user_set": bool(smtp_user),
        "smtp_pass_set": bool(smtp_pass),
        "can_send_real": resend or smtp_ok,
    }


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
    from .security_urls import validate_outbound_url

    ok_u, why = validate_outbound_url(url, allow_public=True)
    if not ok_u:
        return False, why
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


def _send_resend(to: str, cc: str, subject: str, body: str) -> tuple[bool, str]:
    key = os.getenv("RESEND_API_KEY", "").strip() or os.getenv("VIGIEPP_RESEND_API_KEY", "").strip()
    if not key:
        return False, "RESEND_API_KEY no configurada"
    frm = os.getenv("VIGIEPP_SMTP_FROM", os.getenv("SMTP_FROM", "VigiEPP <onboarding@resend.dev>")).strip()
    payload: dict[str, Any] = {
        "from": frm,
        "to": [x.strip() for x in to.split(",") if x.strip()],
        "subject": subject,
        "text": body,
    }
    if cc:
        payload["cc"] = [x.strip() for x in cc.split(",") if x.strip()]
    req = urllib.request.Request(
        "https://api.resend.com/emails",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {key}",
            "User-Agent": "VigiEPP/1.0",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=12) as resp:
            return True, f"resend HTTP {resp.status}"
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="ignore")[:180]
        return False, f"resend HTTP {exc.code}: {detail}"
    except Exception as exc:  # noqa: BLE001
        return False, str(exc)


def _send_smtp(to: str, cc: str, subject: str, body: str) -> tuple[bool, str]:
    host = os.getenv("VIGIEPP_SMTP_HOST", os.getenv("SMTP_HOST", "")).strip()
    port = int(os.getenv("VIGIEPP_SMTP_PORT", os.getenv("SMTP_PORT", "587")) or 587)
    user = os.getenv("VIGIEPP_SMTP_USER", os.getenv("SMTP_USER", "")).strip()
    password = os.getenv("VIGIEPP_SMTP_PASS", os.getenv("SMTP_PASS", "")).strip()
    frm = os.getenv("VIGIEPP_SMTP_FROM", os.getenv("SMTP_FROM", "")).strip()
    if not host or not frm:
        return False, "SMTP no configurado (VIGIEPP_SMTP_HOST / FROM)"
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = frm
    msg["To"] = to
    if cc:
        msg["Cc"] = cc
    msg.set_content(body)
    recipients = [x.strip() for x in to.split(",") if x.strip()]
    recipients += [x.strip() for x in cc.split(",") if x.strip()]
    try:
        if port == 465:
            context = ssl.create_default_context()
            with smtplib.SMTP_SSL(host, port, timeout=15, context=context) as smtp:
                if user:
                    smtp.login(user, password)
                smtp.send_message(msg, to_addrs=recipients)
        else:
            with smtplib.SMTP(host, port, timeout=15) as smtp:
                smtp.ehlo()
                try:
                    smtp.starttls(context=ssl.create_default_context())
                    smtp.ehlo()
                except smtplib.SMTPException:
                    pass
                if user:
                    smtp.login(user, password)
                smtp.send_message(msg, to_addrs=recipients)
        return True, f"smtp {host}:{port}"
    except Exception as exc:  # noqa: BLE001
        return False, str(exc)


def _append_log(entry: dict[str, Any]) -> None:
    global DATA_DIR, LOG_FILE
    DATA_DIR = data_dir()
    LOG_FILE = DATA_DIR / "notification_log.jsonl"
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with _lock:
        with LOG_FILE.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(entry, ensure_ascii=False) + "\n")


def recent_log(limit: int = 30) -> list[dict[str, Any]]:
    global LOG_FILE
    LOG_FILE = data_dir() / "notification_log.jsonl"
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


_last_sent_keys: dict[str, float] = {}


def _cooldown_key(kind: str, payload: dict[str, Any]) -> str:
    who = payload.get("worker_id") or payload.get("rut") or payload.get("name") or "anon"
    miss = ",".join(sorted(str(x) for x in (payload.get("missing") or [])[:4])) or "-"
    zone = str(payload.get("zone") or payload.get("summary") or "")[:80]
    return f"{kind}|{who}|{miss}|{zone}"


def send_notification(
    payload: dict[str, Any],
    *,
    force: bool = False,
    kind: str = "alert",
) -> dict[str, Any]:
    cfg = get_config()
    if not force and not cfg.get("enabled"):
        return {"ok": False, "skipped": True, "reason": "notificaciones desactivadas"}

    now = datetime.now(timezone.utc).timestamp()
    cooldown = float(cfg.get("cooldown_seconds") or 0)
    key = _cooldown_key(kind, payload)
    if not force and cooldown > 0:
        last = _last_sent_keys.get(key, 0.0)
        if (now - last) < cooldown:
            return {"ok": False, "skipped": True, "reason": "cooldown", "key": key}

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

    wa_cloud = channels.get("whatsapp_cloud") or {}
    if wa_cloud.get("enabled") and wa_cloud.get("to"):
        recipients = [x.strip() for x in str(wa_cloud.get("to") or "").replace(";", ",").split(",") if x.strip()]
        wa_results = wa_mod.send_to_recipients(recipients, subject, body, cfg=wa_cloud)
        for wr in wa_results:
            results.append(
                {
                    "channel": "whatsapp_cloud",
                    "ok": wr.get("ok"),
                    "detail": wr.get("detail"),
                    "to": wr.get("to"),
                }
            )

    email = channels.get("email") or {}
    mailto = None
    transport = email_transport_status()
    if email.get("enabled") and email.get("to"):
        to = str(email.get("to") or "")
        cc = str(email.get("cc") or "")
        if transport["mode"] == "resend":
            ok, detail = _send_resend(to, cc, subject, body)
            results.append({"channel": "email", "ok": ok, "detail": detail, "transport": "resend"})
        elif transport["mode"] == "smtp":
            ok, detail = _send_smtp(to, cc, subject, body)
            results.append({"channel": "email", "ok": ok, "detail": detail, "transport": "smtp"})
        else:
            mailto = f"mailto:{to}?subject={quote(subject)}&body={quote(body)}"
            results.append(
                {
                    "channel": "email",
                    "ok": True,
                    "detail": "mailto_only — configurá SMTP o RESEND_API_KEY para envío real",
                    "mailto": mailto,
                    "transport": "mailto",
                }
            )

    if not results:
        results.append({"channel": "none", "ok": False, "detail": "sin canales activos"})

    any_ok = any(r.get("ok") for r in results)
    if any_ok:
        _last_sent_keys[key] = now
        # limpia claves viejas
        if len(_last_sent_keys) > 500:
            cutoff = now - max(cooldown, 120) * 3
            for k, ts in list(_last_sent_keys.items()):
                if ts < cutoff:
                    _last_sent_keys.pop(k, None)

    entry = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "kind": kind,
        "ok": any_ok,
        "subject": subject,
        "body": body,
        "payload": payload,
        "results": results,
        "mailto": mailto,
        "cooldown_key": key,
    }
    _append_log(entry)
    return {
        "ok": any_ok,
        "subject": subject,
        "body": body,
        "results": results,
        "mailto": mailto,
        "email_transport": transport,
    }


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
    cfg = get_config()
    access = cfg.get("access_control") or {}
    hw = access.get("hardware") or {}
    if hw.get("enabled"):
        hw_mod.trigger_unknown(hw)
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
        force=True,
        kind="unknown_face",
    )


def maybe_notify_zones(
    identity: dict[str, Any] | None,
    zone_alerts: list[str],
    profile: str,
) -> None:
    cfg = get_config()
    if not zone_alerts:
        return
    access = cfg.get("access_control") or {}
    hw = access.get("hardware") or {}
    if hw.get("enabled"):
        hw_mod.trigger_zone(hw)
    if not cfg.get("enabled") or not cfg.get("on_zone_alert"):
        return
    summary = zone_alerts[0]
    send_notification(
        {
            "name": (identity or {}).get("name"),
            "rut": (identity or {}).get("rut"),
            "worker_id": (identity or {}).get("id"),
            "profile": profile,
            "summary": summary,
            "missing": ["zona"],
            "zone": summary,
            "ts": datetime.now(timezone.utc).isoformat(),
            "compliant": False,
        },
        force=True,
        kind="zone_alert",
    )


def maybe_access_gate(
    identity: dict[str, Any] | None,
    compliance: dict[str, Any],
    profile: str,
) -> dict[str, Any] | None:
    cfg = get_config()
    access = cfg.get("access_control") or {}
    gate_cfg = access.get("gate") or access
    gate_result = gate_mod.sync_from_scan(
        identity,
        compliance,
        gate=gate_cfg,
        access_enabled=bool(access.get("enabled")),
        require_identity=bool(access.get("require_identity", True)),
    )

    if not access.get("enabled") and gate_result is None:
        return None

    known = bool((identity or {}).get("known") and (identity or {}).get("id"))
    ok_epp = bool(compliance.get("overall_compliant"))
    allow = known and ok_epp
    if access.get("require_identity", True) and not known:
        allow = False

    if not access.get("enabled"):
        if gate_result is None:
            return None
        return {
            "allow": ok_epp,
            "action": gate_result.get("gate_action") or gate_result.get("action"),
            "name": (identity or {}).get("name"),
            "rut": (identity or {}).get("rut"),
            "worker_id": (identity or {}).get("id"),
            "profile": profile,
            "summary": "Control de acceso sincronizado",
            "missing": [],
            "ts": datetime.now(timezone.utc).isoformat(),
            "compliant": ok_epp,
            "gate": gate_result,
        }

    payload = {
        "allow": allow,
        "action": "open" if allow else "deny",
        "name": (identity or {}).get("name"),
        "rut": (identity or {}).get("rut"),
        "worker_id": (identity or {}).get("id"),
        "profile": profile,
        "summary": "Acceso permitido" if allow else "Acceso denegado (identidad o EPP)",
        "missing": (
            []
            if allow
            else (["identidad"] if not known else [
                m
                for p in (compliance.get("persons") or [])
                for m in (p.get("missing") or [])
            ])
        ),
        "ts": datetime.now(timezone.utc).isoformat(),
        "compliant": ok_epp,
        "gate": gate_result,
    }
    if cfg.get("enabled") and access.get("notify", True):
        send_notification(payload, force=True, kind="access_allow" if allow else "access_deny")
    return payload


def test_hardware(action: str = "alarma") -> dict[str, Any]:
    cfg = get_config()
    access = cfg.get("access_control") or {}
    gate_cfg = gate_mod.merge_gate(access.get("gate") or access)
    act = "allow" if str(action).lower().strip() in ("ok", "verde", "allow", "open") else "deny"
    return gate_mod.test_driver(gate_cfg, act)  # type: ignore[arg-type]
