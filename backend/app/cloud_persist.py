"""Respaldo durable de identidad (personas + caras) fuera del disco efímero de Render Free.

Config (env):
  VIGIEPP_CLOUD_TOKEN  — GitHub PAT con Contents: Read/Write
  VIGIEPP_CLOUD_REPO   — owner/repo privado (ej. pamau80/vigiepp-data)
  VIGIEPP_CLOUD_PATH   — ruta del zip (default: vigiepp-identity-backup.zip)

Al arrancar: si el volumen local no tiene workers, restaura desde GitHub.
Tras cada guardado de identidad: sube el zip (debounce).
"""

from __future__ import annotations

import base64
import json
import logging
import os
import threading
import time
import urllib.error
import urllib.request
from typing import Any

logger = logging.getLogger("vigiepp.cloud_persist")

_lock = threading.Lock()
_timer: threading.Timer | None = None
_last_status: dict[str, Any] = {
    "enabled": False,
    "configured": False,
    "last_push_ok": None,
    "last_pull_ok": None,
    "last_error": None,
    "repo": None,
    "path": None,
}


def configured() -> bool:
    return bool(os.getenv("VIGIEPP_CLOUD_TOKEN", "").strip() and os.getenv("VIGIEPP_CLOUD_REPO", "").strip())


def status() -> dict[str, Any]:
    st = dict(_last_status)
    st["configured"] = configured()
    st["enabled"] = configured()
    st["repo"] = os.getenv("VIGIEPP_CLOUD_REPO", "").strip() or None
    st["path"] = os.getenv("VIGIEPP_CLOUD_PATH", "vigiepp-identity-backup.zip").strip()
    st["ephemeral_host"] = os.getenv("VIGIEPP_EPHEMERAL", "").strip() in ("1", "true", "yes")
    return st


def _api(method: str, url: str, body: dict | None = None) -> dict[str, Any]:
    token = os.getenv("VIGIEPP_CLOUD_TOKEN", "").strip()
    data = None
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "VigiEPP-CloudPersist",
    }
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as exc:
        err_body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"GitHub HTTP {exc.code}: {err_body[:300]}") from exc


def _content_url() -> str:
    repo = os.getenv("VIGIEPP_CLOUD_REPO", "").strip()
    path = os.getenv("VIGIEPP_CLOUD_PATH", "vigiepp-identity-backup.zip").strip().lstrip("/")
    return f"https://api.github.com/repos/{repo}/contents/{path}"


def pull_and_restore_if_empty() -> dict[str, Any]:
    """Si no hay workers locales, restaura backup remoto (arranque tras sleep Free)."""
    if not configured():
        return {"ok": False, "skipped": True, "reason": "cloud no configurado"}

    from . import backup as backup_mod
    from .paths import data_dir

    workers = data_dir() / "workers.json"
    has_local = False
    if workers.exists():
        try:
            raw = json.loads(workers.read_text(encoding="utf-8"))
            has_local = bool(raw.get("workers"))
        except Exception:  # noqa: BLE001
            has_local = False
    if has_local:
        return {"ok": True, "skipped": True, "reason": "ya hay datos locales"}

    try:
        meta = _api("GET", _content_url())
        download = meta.get("download_url")
        if not download:
            content_b64 = meta.get("content")
            if not content_b64:
                _last_status["last_pull_ok"] = False
                _last_status["last_error"] = "backup remoto vacío"
                return {"ok": False, "error": "sin backup remoto"}
            blob = base64.b64decode("".join(content_b64.split()))
        else:
            req = urllib.request.Request(
                download,
                headers={"User-Agent": "VigiEPP-CloudPersist", "Accept": "application/octet-stream"},
            )
            with urllib.request.urlopen(req, timeout=60) as resp:
                blob = resp.read()

        result = backup_mod.restore_backup_zip(blob, mode="replace")
        backup_mod.reload_identity_registry()
        _last_status["last_pull_ok"] = True
        _last_status["last_error"] = None
        logger.info("Cloud persist: restaurados %s workers desde GitHub", result.get("workers"))
        return {"ok": True, "restored": True, **result}
    except Exception as exc:  # noqa: BLE001
        _last_status["last_pull_ok"] = False
        _last_status["last_error"] = str(exc)
        logger.warning("Cloud persist pull falló: %s", exc)
        return {"ok": False, "error": str(exc)}


def push_now() -> dict[str, Any]:
    if not configured():
        return {"ok": False, "skipped": True, "reason": "cloud no configurado"}

    from . import backup as backup_mod

    try:
        blob = backup_mod.build_backup_zip()
        content_b64 = base64.b64encode(blob).decode("ascii")
        sha = None
        try:
            meta = _api("GET", _content_url())
            sha = meta.get("sha")
        except Exception:  # noqa: BLE001
            sha = None

        body: dict[str, Any] = {
            "message": "VigiEPP identity backup (auto)",
            "content": content_b64,
        }
        if sha:
            body["sha"] = sha
        _api("PUT", _content_url(), body)
        _last_status["last_push_ok"] = True
        _last_status["last_error"] = None
        logger.info("Cloud persist: backup subido (%s bytes)", len(blob))
        return {"ok": True, "bytes": len(blob)}
    except Exception as exc:  # noqa: BLE001
        _last_status["last_push_ok"] = False
        _last_status["last_error"] = str(exc)
        logger.warning("Cloud persist push falló: %s", exc)
        return {"ok": False, "error": str(exc)}


def schedule_push(delay_seconds: float = 4.0) -> None:
    """Debounce: varios enrolamientos → un solo push."""
    if not configured():
        return
    global _timer
    with _lock:
        if _timer is not None:
            _timer.cancel()

        def _run() -> None:
            push_now()

        _timer = threading.Timer(delay_seconds, _run)
        _timer.daemon = True
        _timer.start()
