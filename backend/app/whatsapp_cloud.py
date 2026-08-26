"""WhatsApp Business Cloud API (Meta) — envío nativo."""

from __future__ import annotations

import json
import logging
import os
import urllib.error
import urllib.request
from typing import Any

logger = logging.getLogger("vigiepp.whatsapp")

GRAPH = "https://graph.facebook.com/v21.0"


def _token() -> str:
    return (
        os.getenv("WHATSAPP_TOKEN", "").strip()
        or os.getenv("VIGIEPP_WHATSAPP_TOKEN", "").strip()
    )


def _phone_number_id(cfg: dict[str, Any]) -> str:
    return str(cfg.get("phone_number_id") or os.getenv("WHATSAPP_PHONE_NUMBER_ID", "")).strip()


def configured(cfg: dict[str, Any] | None = None) -> bool:
    c = cfg or {}
    return bool(_token() and _phone_number_id(c))


def send_text(
    to: str,
    body: str,
    *,
    cfg: dict[str, Any] | None = None,
) -> tuple[bool, str]:
    token = _token()
    phone_id = _phone_number_id(cfg or {})
    to_digits = "".join(ch for ch in str(to or "") if ch.isdigit())
    if not token or not phone_id:
        return False, "WHATSAPP_TOKEN o phone_number_id no configurados"
    if not to_digits:
        return False, "número destino vacío"
    if len(body) > 4096:
        body = body[:4093] + "..."

    url = f"{GRAPH}/{phone_id}/messages"
    payload = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": to_digits,
        "type": "text",
        "text": {"preview_url": False, "body": body},
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
            return True, raw[:200] or f"HTTP {resp.status}"
    except urllib.error.HTTPError as exc:
        err_body = exc.read().decode("utf-8", errors="replace")[:300]
        return False, f"HTTP {exc.code}: {err_body}"
    except Exception as exc:  # noqa: BLE001
        return False, str(exc)


def send_to_recipients(
    recipients: list[str],
    subject: str,
    body: str,
    *,
    cfg: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    text = f"{subject}\n\n{body}".strip()
    out: list[dict[str, Any]] = []
    for raw in recipients:
        num = str(raw or "").strip()
        if not num:
            continue
        ok, detail = send_text(num, text, cfg=cfg)
        out.append({"to": num, "ok": ok, "detail": detail})
    return out
