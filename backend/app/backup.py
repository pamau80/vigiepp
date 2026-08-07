"""Backup / restore de personas + embeddings faciales."""

from __future__ import annotations

import io
import json
import logging
import shutil
import tempfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .paths import data_dir

logger = logging.getLogger("vigiepp.backup")

MANIFEST = "vigiepp-backup.json"


def _workers_file() -> Path:
    return data_dir() / "workers.json"


def _faces_dir() -> Path:
    return data_dir() / "faces"


def build_backup_zip() -> bytes:
    """Empaqueta workers.json + carpeta faces/ en un zip en memoria."""
    buf = io.BytesIO()
    workers = _workers_file()
    faces = _faces_dir()
    manifest = {
        "product": "VigiEPP",
        "kind": "identity-backup",
        "version": 1,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(MANIFEST, json.dumps(manifest, ensure_ascii=False, indent=2))
        if workers.exists():
            zf.write(workers, arcname="workers.json")
        else:
            zf.writestr("workers.json", json.dumps({"workers": [], "updated_at": None}, indent=2))
        if faces.exists():
            for path in faces.rglob("*"):
                if path.is_file():
                    zf.write(path, arcname=str(Path("faces") / path.relative_to(faces)).replace("\\", "/"))
    return buf.getvalue()


def restore_backup_zip(data: bytes, *, mode: str = "merge") -> dict[str, Any]:
    """
    Restaura backup.
    mode=merge: agrega/actualiza workers por id (no borra los que no vienen).
    mode=replace: reemplaza workers.json y faces/ completos.
    """
    if mode not in ("merge", "replace"):
        raise ValueError("mode debe ser merge o replace")

    with tempfile.TemporaryDirectory(prefix="vigiepp-restore-") as tmp:
        tmp_path = Path(tmp)
        with zipfile.ZipFile(io.BytesIO(data), "r") as zf:
            # Evitar path traversal
            for info in zf.infolist():
                name = info.filename.replace("\\", "/")
                if name.startswith("/") or ".." in name.split("/"):
                    raise ValueError(f"Ruta inválida en zip: {info.filename}")
            zf.extractall(tmp_path)

        workers_src = tmp_path / "workers.json"
        if not workers_src.exists():
            raise ValueError("El zip no contiene workers.json")

        raw = json.loads(workers_src.read_text(encoding="utf-8"))
        incoming = raw.get("workers") if isinstance(raw, dict) else raw
        if not isinstance(incoming, list):
            raise ValueError("workers.json inválido")

        faces_src = tmp_path / "faces"
        dest_workers = _workers_file()
        dest_faces = _faces_dir()
        dest_faces.mkdir(parents=True, exist_ok=True)

        if mode == "replace":
            if dest_faces.exists():
                shutil.rmtree(dest_faces)
            dest_faces.mkdir(parents=True, exist_ok=True)
            payload = {
                "workers": incoming,
                "updated_at": datetime.now(timezone.utc).isoformat(),
                "restored_at": datetime.now(timezone.utc).isoformat(),
            }
            dest_workers.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
            if faces_src.exists():
                for path in faces_src.rglob("*"):
                    if path.is_file():
                        rel = path.relative_to(faces_src)
                        target = dest_faces / rel
                        target.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(path, target)
            return {
                "ok": True,
                "mode": mode,
                "workers": len(incoming),
                "faces_copied": sum(1 for _ in dest_faces.rglob("face_*.jpg")),
            }

        # merge
        current: dict[str, Any] = {"workers": []}
        if dest_workers.exists():
            try:
                current = json.loads(dest_workers.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                current = {"workers": []}
        by_id: dict[str, dict] = {}
        for w in current.get("workers") or []:
            if isinstance(w, dict) and w.get("id"):
                by_id[str(w["id"])] = w
        added = 0
        updated = 0
        for w in incoming:
            if not isinstance(w, dict) or not w.get("id"):
                continue
            wid = str(w["id"])
            if wid in by_id:
                by_id[wid] = {**by_id[wid], **w}
                updated += 1
            else:
                by_id[wid] = w
                added += 1
            # copiar cara del worker
            src_folder = faces_src / wid
            if src_folder.exists():
                dst_folder = dest_faces / wid
                dst_folder.mkdir(parents=True, exist_ok=True)
                for path in src_folder.rglob("*"):
                    if path.is_file():
                        shutil.copy2(path, dst_folder / path.name)

        payload = {
            "workers": list(by_id.values()),
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "restored_at": datetime.now(timezone.utc).isoformat(),
        }
        dest_workers.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return {
            "ok": True,
            "mode": mode,
            "workers": len(by_id),
            "added": added,
            "updated": updated,
            "faces_copied": sum(1 for _ in dest_faces.rglob("face_*.jpg")),
        }


def reload_identity_registry() -> None:
    """Fuerza reinicio del singleton de identidad tras restore."""
    from .identity import IdentityRegistry

    with IdentityRegistry._lock:
        IdentityRegistry._instance = None
    IdentityRegistry.get()
