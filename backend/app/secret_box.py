"""Cifrado reversible para secretos en disco (credenciales NVR)."""

from __future__ import annotations

import hashlib
import logging
import os
from pathlib import Path

logger = logging.getLogger("vigiepp.secrets")

_KEY_FILE = ".secrets_key"


def _bundle_root() -> Path:
    from .paths import _bundle_data_root

    return _bundle_data_root()


def _fernet():
    try:
        from cryptography.fernet import Fernet
    except ImportError:
        return None

    env = os.getenv("VIGIEPP_SECRETS_KEY", "").strip()
    if env:
        try:
            return Fernet(env.encode("ascii"))
        except Exception:  # noqa: BLE001
            logger.warning("VIGIEPP_SECRETS_KEY inválida")

    path = _bundle_root() / _KEY_FILE
    if path.is_file():
        raw = path.read_text(encoding="utf-8").strip()
        try:
            return Fernet(raw.encode("ascii"))
        except Exception:  # noqa: BLE001
            logger.warning("Archivo .secrets_key corrupto; se regenerará")

    key = Fernet.generate_key()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(key.decode("ascii"), encoding="utf-8")
    return Fernet(key)


def encrypt_text(plain: str) -> str | None:
    if not plain:
        return None
    f = _fernet()
    if f is None:
        return None
    try:
        return f.encrypt(plain.encode("utf-8")).decode("ascii")
    except Exception:  # noqa: BLE001
        logger.exception("encrypt failed")
        return None


def decrypt_text(token: str) -> str | None:
    if not token:
        return None
    f = _fernet()
    if f is None:
        return None
    try:
        return f.decrypt(token.encode("ascii")).decode("utf-8")
    except Exception:  # noqa: BLE001
        return None


def digest_secret(plain: str) -> str:
    return hashlib.sha256((plain or "").encode("utf-8")).hexdigest()[:16]
