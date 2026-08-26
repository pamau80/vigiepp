from __future__ import annotations

import base64
import csv
import io
import threading
import zipfile
from datetime import datetime, timezone
from typing import Any

import cv2
from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import JSONResponse, Response

from .. import audit as audit_mod
from .. import privacy as privacy_mod
from ..detect_pipeline import detect_lock
from ..detector import decode_image_bytes, encode_jpeg
from ..identity import IdentityRegistry, IdentityService

router = APIRouter(prefix="/api/identity", tags=["identity"])

@router.get("/workers")
def identity_workers() -> list[dict[str, Any]]:
    return IdentityRegistry.get().list_workers()


@router.get("/consent.csv")
def identity_consent_csv() -> Response:
    """Export CSV de consentimiento biométrico (Ley 19.628 / DS 44)."""
    import csv
    import io

    workers = IdentityRegistry.get().list_workers()
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(
        [
            "id",
            "nombre",
            "rut",
            "grupo",
            "activo",
            "consentimiento_ok",
            "consentimiento_fecha",
            "consentimiento_version",
            "enrolado_en",
            "muestras_rostro",
        ]
    )
    for w in workers:
        writer.writerow(
            [
                w.get("id") or "",
                w.get("name") or "",
                w.get("rut") or "",
                w.get("group") or "",
                "si" if w.get("active", True) else "no",
                "si" if w.get("consent_ok") else "no",
                w.get("consent_at") or "",
                w.get("consent_version") or "",
                w.get("enrolled_at") or "",
                w.get("face_samples") or 0,
            ]
        )
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M")
    return Response(
        content=buf.getvalue().encode("utf-8-sig"),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="vigiepp-consentimiento-{stamp}.csv"'},
    )


@router.get("/backup")
def identity_backup() -> Response:
    """Descarga ZIP con workers.json + fotos/embeddings + config operativa."""
    from .. import backup as backup_mod

    data = backup_mod.build_backup_zip()
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M")
    return Response(
        content=data,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="vigiepp-personas-{stamp}.zip"'},
    )


@router.post("/backup/restore")
async def identity_backup_restore(
    file: UploadFile = File(...),
    mode: str = Form("merge"),
) -> dict[str, Any]:
    """Restaura backup ZIP. mode=merge|replace."""
    from .. import backup as backup_mod

    raw = await file.read()
    if not raw:
        raise HTTPException(400, "Archivo vacío")
    try:
        result = backup_mod.restore_backup_zip(raw, mode=mode.strip() or "merge")
        backup_mod.reload_identity_registry()
        try:
            from .. import cloud_persist as cloud_mod

            cloud_mod.schedule_push(2.0)
        except Exception:  # noqa: BLE001
            pass
        return result
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    except zipfile.BadZipFile as exc:
        raise HTTPException(400, "ZIP inválido") from exc


@router.delete("/workers/{worker_id}")
def identity_delete(worker_id: str) -> dict[str, Any]:
    ok = IdentityRegistry.get().delete_worker(worker_id)
    if not ok:
        raise HTTPException(404, "Trabajador no encontrado")
    from .. import audit as audit_mod

    audit_mod.log("worker_delete", detail=worker_id)
    return {"ok": True, "deleted": worker_id}


@router.patch("/workers/{worker_id}")
async def identity_update(worker_id: str, request: Request) -> dict[str, Any]:
    """Actualiza ficha: nombre, RUT, activo, grupo, notas."""
    from .identity import compute_quality, normalize_person_name, normalize_rut, validate_rut, worker_public

    body = await request.json()
    reg = IdentityRegistry.get()
    worker = reg._workers.get(worker_id)
    if not worker:
        raise HTTPException(404, "Trabajador no encontrado")
    if "name" in body:
        name = normalize_person_name(str(body.get("name") or "").strip())
        if name:
            worker.name = name
    if "rut" in body:
        rut_raw = str(body.get("rut") or "").strip()
        if rut_raw:
            rut = normalize_rut(rut_raw)
            if not validate_rut(rut) and not rut.startswith("SIN-RUT"):
                raise HTTPException(400, "RUT inválido")
            for wid, w in reg._workers.items():
                if wid != worker_id and w.rut == rut:
                    raise HTTPException(409, f"El RUT ya está en {w.name}")
            worker.rut = rut
    if "active" in body:
        worker.active = bool(body.get("active"))
    if "group" in body:
        worker.group = str(body.get("group") or "").strip()[:80]
    if "notes" in body:
        worker.notes = str(body.get("notes") or "").strip()[:500]
    worker.quality = compute_quality(worker.face_samples)
    reg._workers[worker_id] = worker
    reg._save()
    return {"ok": True, "worker": worker_public(worker)}


@router.get("/workers/{worker_id}/photo")
def identity_worker_photo(worker_id: str) -> Response:
    from .identity import FACES_DIR

    folder = FACES_DIR / worker_id
    if not folder.exists():
        raise HTTPException(404, "Sin foto")
    photos = sorted(folder.glob("face_*.jpg"))
    if not photos:
        raise HTTPException(404, "Sin foto")
    data = photos[-1].read_bytes()
    return Response(content=data, media_type="image/jpeg", headers={"Cache-Control": "private, max-age=60"})


@router.post("/workers/{worker_id}/reset-faces")
def identity_reset_faces(worker_id: str) -> dict[str, Any]:
    """Borra solo las fotos/embeddings; mantiene nombre y RUT para re-enrolar."""
    from .identity import FACES_DIR, compute_quality, worker_public

    reg = IdentityRegistry.get()
    worker = reg._workers.get(worker_id)
    if not worker:
        raise HTTPException(404, "Trabajador no encontrado")
    folder = FACES_DIR / worker_id
    if folder.exists():
        for f in folder.iterdir():
            f.unlink(missing_ok=True)
    reg._embeddings[worker_id] = []
    worker.face_samples = 0
    worker.quality = compute_quality(0)
    reg._workers[worker_id] = worker
    reg._save()
    return {
        "ok": True,
        "worker": worker_public(worker),
        "message": "Rostros borrados. Volvé a enrolar 4 posiciones.",
    }


@router.post("/enroll")
async def identity_enroll(
    file: UploadFile = File(...),
    name: str = Form(""),
    rut: str = Form(""),
    notes: str = Form(""),
    consent: str = Form("false"),
) -> JSONResponse:
    data = await file.read()
    try:
        frame = decode_image_bytes(data)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    agreed = str(consent).strip().lower() in ("1", "true", "yes", "on")
    if privacy_mod.qr_only_enabled():
        raise HTTPException(400, "Modo QR-only activo: enrolamiento facial deshabilitado.")
    result = IdentityService().enroll(frame, name=name, rut=rut, notes=notes, consent=agreed)
    if not result.get("ok"):
        raise HTTPException(400, result.get("error", "No se pudo enrolar"))
    if result.get("face_enrolled"):
        from .. import audit as audit_mod

        w = result.get("worker") or {}
        audit_mod.log("enroll_face", detail=str(w.get("name") or name), extra={"samples": result.get("samples")})
    return JSONResponse(result)


@router.post("/enroll-photos")
async def identity_enroll_photos(
    files: list[UploadFile] = File(...),
    name: str = Form(""),
    rut: str = Form(""),
    consent: str = Form("false"),
) -> JSONResponse:
    """Entrena rostros adjuntando varias fotos (sin countdown de poses)."""
    if not name.strip() and not rut.strip():
        raise HTTPException(400, "Indicá nombre o RUT")
    agreed = str(consent).strip().lower() in ("1", "true", "yes", "on")
    if not agreed:
        raise HTTPException(400, "Falta consentimiento biométrico para registrar el rostro.")
    if privacy_mod.qr_only_enabled():
        raise HTTPException(400, "Modo QR-only activo: enrolamiento facial deshabilitado.")
    saved = 0
    failed = 0
    last_worker = None
    errors: list[str] = []
    for f in files[:40]:
        data = await f.read()
        if not data:
            continue
        try:
            frame = decode_image_bytes(data)
        except ValueError:
            failed += 1
            continue
        result = IdentityService().enroll(
            frame, name=name, rut=rut, notes="foto_adjunta", consent=agreed
        )
        if result.get("face_enrolled"):
            saved += 1
            last_worker = result.get("worker")
        else:
            failed += 1
            err = result.get("error") or result.get("message") or "sin rostro"
            errors.append(str(err))
    if saved == 0:
        raise HTTPException(
            400,
            errors[0] if errors else "Ninguna foto tuvo rostro usable. Subí fotos de frente, con buena luz.",
        )
    ready = bool(last_worker and last_worker.get("ready"))
    return JSONResponse(
        {
            "ok": True,
            "saved": saved,
            "failed": failed,
            "worker": last_worker,
            "ready": ready,
            "message": (
                f"Rostro: {saved} fotos de calidad"
                + (f" · {failed} descartadas (borrosas/ángulo/lejos)" if failed else "")
                + (
                    " · ficha lista para identificación estricta."
                    if ready
                    else " · incompleta: necesitás al menos 4 muestras aceptadas."
                )
            ),
        }
    )


@router.post("/identify")
async def identity_identify(
    file: UploadFile = File(...),
    threshold: float = Form(0.33),
    return_image: str = Form("false"),
) -> JSONResponse:
    data = await file.read()
    if not data:
        raise HTTPException(400, "Archivo vacío")
    if not detect_lock.acquire(blocking=False):
        return JSONResponse(
            {"ok": False, "busy": True, "error": "IA ocupada, esperá un momento."},
            status_code=429,
        )
    try:
        try:
            frame = decode_image_bytes(data)
        except ValueError as exc:
            raise HTTPException(400, str(exc)) from exc
        reg = IdentityRegistry.peek()
        if reg is None:
            threading.Thread(target=IdentityRegistry.get, name="id-load", daemon=True).start()
            return JSONResponse(
                {
                    "ok": False,
                    "booting": True,
                    "error": "Reconocimiento facial cargando…",
                    "matches": [],
                    "identified": None,
                    "faces_detected": 0,
                    "gallery_size": 0,
                },
                status_code=503,
            )
        h, w = frame.shape[:2]
        max_side = 480
        if max(h, w) > max_side:
            scale = max_side / max(h, w)
            frame = cv2.resize(frame, (int(w * scale), int(h * scale)))
        thr = max(0.25, min(0.7, float(threshold or 0.33)))
        result = IdentityService().identify(frame, threshold=thr)
        annotated = result.pop("annotated", None)
        want_img = str(return_image).lower() in ("1", "true", "yes", "on")
        if want_img and annotated is not None:
            jpeg = encode_jpeg(annotated, quality=72)
            result["image_b64"] = base64.b64encode(jpeg).decode("ascii")
        return JSONResponse(result)
    finally:
        detect_lock.release()


# ── Enseñar EPP personalizado ───────────────────────────────────────────────


