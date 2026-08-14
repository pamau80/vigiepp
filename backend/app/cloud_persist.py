"""Volumen durable gratuito (fuente de verdad) vía Hugging Face Hub.

Render Free / cualquier host sin disco: /data local es solo caché.
El zip (identidad + zonas/cámaras/notif/bitácora) vive en un dataset PRIVADO de HF.

Env:
  HF_TOKEN o VIGIEPP_HF_TOKEN  — token write de https://huggingface.co/settings/tokens
  VIGIEPP_HF_REPO              — ej. tuusuario/vigiepp-data (se crea solo si falta)
  VIGIEPP_HF_FILE              — default identity-backup.zip (nombre histórico)
"""

from __future__ import annotations

import logging
import os
import tempfile
import threading
from pathlib import Path
from typing import Any

logger = logging.getLogger("vigiepp.durable")

_lock = threading.Lock()
_timer: threading.Timer | None = None
_last: dict[str, Any] = {
    "backend": "huggingface",
    "configured": False,
    "repo": None,
    "last_push_ok": None,
    "last_pull_ok": None,
    "last_error": None,
    "mode": "primary",
}


def _token() -> str:
    return (
        os.getenv("VIGIEPP_HF_TOKEN", "").strip()
        or os.getenv("HF_TOKEN", "").strip()
        or os.getenv("HUGGINGFACE_HUB_TOKEN", "").strip()
    )


def _repo_id() -> str:
    return os.getenv("VIGIEPP_HF_REPO", "").strip()


def _file_name() -> str:
    return os.getenv("VIGIEPP_HF_FILE", "identity-backup.zip").strip() or "identity-backup.zip"


def configured() -> bool:
    return bool(_token() and _repo_id())


def status() -> dict[str, Any]:
    st = dict(_last)
    st["configured"] = configured()
    st["repo"] = _repo_id() or None
    st["ephemeral_host"] = os.getenv("VIGIEPP_EPHEMERAL", "").strip().lower() in ("1", "true", "yes")
    # Compat con health anterior
    st["enabled"] = configured()
    st["path"] = _file_name()
    return st


def _api():
    from huggingface_hub import HfApi

    return HfApi(token=_token())


def ensure_repo() -> None:
    api = _api()
    repo = _repo_id()
    try:
        api.create_repo(repo_id=repo, repo_type="dataset", private=True, exist_ok=True)
    except Exception as exc:  # noqa: BLE001
        # Puede existir o faltar permiso; el upload fallará con mensaje claro
        logger.info("ensure_repo: %s", exc)


def pull_and_restore_if_empty() -> dict[str, Any]:
    """Compat: si local vacío, hidrata desde HF."""
    return hydrate(force=False)


def hydrate(force: bool = False) -> dict[str, Any]:
    """Descarga el volumen remoto y restaura identidad.

    force=False: solo si no hay workers locales.
    force=True: siempre reemplaza local con remoto (arranque durable).
    """
    if not configured():
        return {"ok": False, "skipped": True, "reason": "HF no configurado"}

    from . import backup as backup_mod
    from .paths import data_dir

    workers = data_dir() / "workers.json"
    has_local = False
    if workers.exists():
        try:
            import json

            raw = json.loads(workers.read_text(encoding="utf-8"))
            has_local = bool(raw.get("workers"))
        except Exception:  # noqa: BLE001
            has_local = False

    if has_local and not force:
        return {"ok": True, "skipped": True, "reason": "ya hay datos locales"}

    try:
        from huggingface_hub import hf_hub_download

        ensure_repo()
        path = hf_hub_download(
            repo_id=_repo_id(),
            filename=_file_name(),
            repo_type="dataset",
            token=_token(),
        )
        blob = Path(path).read_bytes()
        if len(blob) < 40:
            return {"ok": False, "error": "backup remoto vacío"}
        result = backup_mod.restore_backup_zip(blob, mode="replace")
        backup_mod.reload_identity_registry()
        _last["last_pull_ok"] = True
        _last["last_error"] = None
        logger.info("Durable HF: restaurados %s workers", result.get("workers"))
        return {"ok": True, "restored": True, **result}
    except Exception as exc:  # noqa: BLE001
        msg = str(exc)
        # Primera vez: aún no hay archivo remoto
        if "404" in msg or "Entry Not Found" in msg or "not found" in msg.lower():
            _last["last_pull_ok"] = True
            _last["last_error"] = None
            return {"ok": True, "skipped": True, "reason": "aún no hay snapshot remoto"}
        _last["last_pull_ok"] = False
        _last["last_error"] = msg
        logger.warning("Durable HF pull falló: %s", exc)
        return {"ok": False, "error": msg}


def push_now() -> dict[str, Any]:
    if not configured():
        return {"ok": False, "skipped": True, "reason": "HF no configurado"}

    from . import backup as backup_mod

    try:
        ensure_repo()
        blob = backup_mod.build_backup_zip()
        with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as tmp:
            tmp.write(blob)
            tmp_path = tmp.name
        try:
            _api().upload_file(
                path_or_fileobj=tmp_path,
                path_in_repo=_file_name(),
                repo_id=_repo_id(),
                repo_type="dataset",
                commit_message="VigiEPP site durable snapshot",
            )
        finally:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
        _last["last_push_ok"] = True
        _last["last_error"] = None
        logger.info("Durable HF: snapshot %s bytes → %s", len(blob), _repo_id())
        return {"ok": True, "bytes": len(blob)}
    except Exception as exc:  # noqa: BLE001
        _last["last_push_ok"] = False
        _last["last_error"] = str(exc)
        logger.warning("Durable HF push falló: %s", exc)
        return {"ok": False, "error": str(exc)}


def schedule_push(delay_seconds: float = 3.0) -> None:
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
