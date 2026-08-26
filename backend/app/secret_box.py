"""Cifrado reversible para secretos en disco (credenciales NVR)."""

from __future__ import annotations

import base64
import hashlib
import logging
import os
from pathlib import Path

logger = logging.getLogger("vigiepp.secrets")

_KEY_FILE = ".secrets_key"


def _bundle_root() -> Path:
    from .paths import _bundle_data_root

    return _bundle_data_root()


def _load_key() -> bytes | None:
    env = os.getenv("VIGIEPP_SECRETS_KEY", "").strip()
    if env:
        try:
            return base64.urlsafe_b64decode(env + "=" * (-len(env) % 4))
        except Exception:  # noqa: BLE001
            logger.warning("VIGIEPP_SECRETS_KEY inválida")
    path = _bundle_root() / _KEY_FILE
    if path.is_file():
        try:
            return base64.urlsafe_b64decode(path.read_text().strip())
        except Exception:  # noqa: BLE001
            pass
    try:
        from cryptography.fernet import Fernet

        key = Fernet.generate_key()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(key.decode(), encoding="utf-8")
        return key
    except ImportError:
        return None


def encrypt_text(plain: str) -> str | None:
    if not plain:
        return None
    try:
        from cryptography.fernet import Fernet

        key = _load_key()
        if not key:
            return None
        f = Fernet(key)
        return f.encrypt(plain.encode("utf-8")).decode("ascii")
    except Exception:  # noqa: BLE001
        logger.exception("encrypt failed")
        return None


def decrypt_text(token: str) -> str | None:
    if not token:
        return None
    try:
        from cryptography.fernet import Fernet

        key = _load_key()
        if not key:
            return None
        f = Fernet(key)
        return f.decrypt(token.encode("ascii")).decode("utf-8")
    except Exception:  # noqa: BLE001
        return None


def digest_secret(plain: str) -> str:
    return hashlib.sha256((plain or "").encode("utf-8")).hexdigest()[:16]
