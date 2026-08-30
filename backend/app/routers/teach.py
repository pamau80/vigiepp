from __future__ import annotations

from typing import Any

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import JSONResponse

from ..detector import PPEDetector, decode_image_bytes
from ..teach import TeachStore

router = APIRouter(prefix="/api/teach", tags=["teach"])

@router.get("/guide")
def teach_guide() -> dict[str, Any]:
    return TeachStore.get().guide()


@router.get("/classes")
def teach_classes() -> list[dict[str, Any]]:
    return TeachStore.get().list_classes()


@router.get("/stats")
def teach_stats() -> dict[str, Any]:
    return TeachStore.get().stats()


@router.post("/sample")
async def teach_sample(
    file: UploadFile = File(...),
    class_id: str = Form(...),
) -> JSONResponse:
    data = await file.read()
    try:
        frame = decode_image_bytes(data)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    result = TeachStore.get().add_sample(frame, class_id=class_id)
    if not result.get("ok"):
        raise HTTPException(400, result.get("error", "Error al guardar"))
    return JSONResponse(result)


@router.post("/class")
async def teach_create_class(
    name: str = Form(...),
    hint: str = Form(""),
) -> JSONResponse:
    result = TeachStore.get().add_custom_class(name=name, hint=hint)
    if not result.get("ok"):
        raise HTTPException(400, result.get("error", "No se pudo crear la clase"))
    return JSONResponse(result)


@router.post("/samples")
async def teach_samples_multi(
    files: list[UploadFile] = File(...),
    class_id: str = Form(...),
) -> JSONResponse:
    frames: list[Any] = []
    for f in files[:80]:
        data = await f.read()
        if not data:
            continue
        try:
            frames.append(decode_image_bytes(data))
        except ValueError:
            continue
    if not frames:
        raise HTTPException(400, "No se pudieron leer las fotos")
    result = TeachStore.get().add_samples_batch(frames, class_id=class_id)
    if not result.get("ok"):
        raise HTTPException(400, result.get("error") or result.get("message") or "Error")
    return JSONResponse(result)


@router.post("/video")
async def teach_video(
    file: UploadFile = File(...),
    class_id: str = Form(...),
    max_frames: int = Form(40),
    stride: int = Form(12),
) -> JSONResponse:
    data = await file.read()
    if not data:
        raise HTTPException(400, "Video vacío")
    if len(data) > 120 * 1024 * 1024:
        raise HTTPException(400, "Video demasiado grande (máx. ~120 MB)")
    result = TeachStore.get().add_from_video(
        data,
        class_id=class_id,
        max_frames=max_frames,
        stride=stride,
    )
    if not result.get("ok"):
        raise HTTPException(400, result.get("error", "No se pudo procesar el video"))
    return JSONResponse(result)


@router.post("/train")
def teach_train(epochs: int = 40) -> dict[str, Any]:
    result = TeachStore.get().start_training(epochs=epochs)
    if not result.get("ok"):
        raise HTTPException(400, result.get("error", "No se pudo entrenar"))
    return result


@router.post("/activate")
def teach_activate() -> dict[str, Any]:
    result = PPEDetector.get().load_custom_model()
    if not result.get("ok"):
        raise HTTPException(400, result.get("error", "Modelo no disponible"))
    return result


