"""Enseñanza de EPP personalizados: captura de ejemplos + entrenamiento YOLO."""

from __future__ import annotations

import json
import logging
import shutil
import subprocess
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import cv2
import numpy as np

from .paths import custom_weights_path, teach_dataset_dir, teach_runs_dir

logger = logging.getLogger("vigiepp.teach")

BASE = Path(__file__).resolve().parents[1]
DATASET_DIR = teach_dataset_dir()
META_FILE = DATASET_DIR / "meta.json"
RUNS_DIR = teach_runs_dir()

# Clases base + el cliente puede agregar prendas propias (meta.custom_classes)
TEACHABLE_CLASSES: list[dict[str, str]] = [
    {"id": "casco", "name": "Casco de seguridad", "hint": "Frente, lateral y con distintos colores"},
    {"id": "lentes", "name": "Lentes / gafas de seguridad", "hint": "Cerca del rostro, varios ángulos"},
    {"id": "chaleco_fluor", "name": "Chaleco / ropa flúor", "hint": "Alta visibilidad, de día y sombra"},
    {"id": "polera", "name": "Polera corporativa", "hint": "Color y logo de la empresa"},
    {"id": "casaca", "name": "Casaca / chaqueta de faena", "hint": "Torso completo, abiertas y cerradas"},
    {"id": "pantalon_azul_franja", "name": "Pantalón azul con franja flúor", "hint": "Cuerpo completo / medio cuerpo"},
    {"id": "pantalon_trabajo", "name": "Pantalón de trabajo", "hint": "Cualquier pantalón de uniforme"},
    {"id": "zapatos_seguridad", "name": "Zapatos de seguridad", "hint": "Cámara baja o acceso/torniquete"},
    {"id": "botas", "name": "Botas de seguridad", "hint": "Pie completo, distintos suelos"},
    {"id": "guantes", "name": "Guantes de seguridad", "hint": "Manos visibles, varios colores"},
    {"id": "arnes", "name": "Arnés anticaídas", "hint": "Torso con correas visibles"},
    {"id": "mascarilla", "name": "Mascarilla / respirador", "hint": "Rostro con EPP respiratorio"},
    {"id": "orejeras", "name": "Orejeras / protección auditiva", "hint": "Cabeza lateral"},
    {"id": "ropa_reflectante", "name": "Ropa reflectante / cinta", "hint": "Bandas reflectantes en torso/brazos"},
    {"id": "uniforme_completo", "name": "Uniforme completo (persona)", "hint": "Cuerpo entero con uniforme de empresa"},
    {"id": "sin_casco", "name": "SIN casco (violación)", "hint": "Cabeza descubierta — útil para alertas"},
    {"id": "sin_chaleco", "name": "SIN chaleco (violación)", "hint": "Persona sin alta visibilidad"},
    {"id": "sin_epp", "name": "SIN EPP (violación)", "hint": "Persona sin protección visible"},
]


class TeachStore:
    _instance: TeachStore | None = None
    _lock = threading.Lock()

    def __init__(self) -> None:
        global DATASET_DIR, META_FILE, RUNS_DIR
        DATASET_DIR = teach_dataset_dir()
        META_FILE = DATASET_DIR / "meta.json"
        RUNS_DIR = teach_runs_dir()
        DATASET_DIR.mkdir(parents=True, exist_ok=True)
        (DATASET_DIR / "images").mkdir(exist_ok=True)
        (DATASET_DIR / "labels").mkdir(exist_ok=True)
        self._meta = self._load_meta()
        self._train_proc: subprocess.Popen | None = None
        self._train_log: str = ""

    @classmethod
    def get(cls) -> TeachStore:
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls()
            return cls._instance

    def _load_meta(self) -> dict[str, Any]:
        if META_FILE.exists():
            raw = json.loads(META_FILE.read_text(encoding="utf-8"))
            raw.setdefault("custom_classes", [])
            raw.setdefault("samples", {})
            return raw
        meta = {
            "classes": [c["id"] for c in TEACHABLE_CLASSES],
            "custom_classes": [],
            "samples": {},
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        self._write_meta(meta)
        return meta

    def _write_meta(self, meta: dict[str, Any]) -> None:
        META_FILE.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
        self._meta = meta

    def all_class_defs(self) -> list[dict[str, str]]:
        customs = self._meta.get("custom_classes") or []
        base_ids = {c["id"] for c in TEACHABLE_CLASSES}
        out = [dict(c) for c in TEACHABLE_CLASSES]
        for c in customs:
            cid = str(c.get("id") or "").strip()
            if cid and cid not in base_ids:
                out.append(
                    {
                        "id": cid,
                        "name": str(c.get("name") or cid),
                        "hint": str(c.get("hint") or "Prenda / EPP personalizado"),
                    }
                )
                base_ids.add(cid)
        return out

    def class_index(self, class_id: str) -> int:
        ids = [c["id"] for c in self.all_class_defs()]
        return ids.index(class_id)

    def list_classes(self) -> list[dict[str, Any]]:
        counts = self._meta.get("samples", {})
        out = []
        for c in self.all_class_defs():
            out.append({**c, "count": int(counts.get(c["id"], 0)), "custom": c["id"] not in {x["id"] for x in TEACHABLE_CLASSES}})
        return out

    def add_custom_class(self, name: str, hint: str = "") -> dict[str, Any]:
        clean = "".join(ch if ch.isalnum() or ch in "_-" else "_" for ch in name.strip().lower())
        clean = clean.strip("_")[:48] or f"prenda_{uuid.uuid4().hex[:6]}"
        existing = {c["id"] for c in self.all_class_defs()}
        if clean in existing:
            return {"ok": False, "error": f"La clase '{clean}' ya existe"}
        customs = list(self._meta.get("custom_classes") or [])
        customs.append(
            {
                "id": clean,
                "name": name.strip() or clean,
                "hint": hint.strip() or "Subí muchas fotos/videos de esta prenda en tu faena real",
            }
        )
        self._meta["custom_classes"] = customs
        self._meta["classes"] = [c["id"] for c in self.all_class_defs()]
        self._write_meta(self._meta)
        return {"ok": True, "class": customs[-1], "classes": self.list_classes()}

    def stats(self) -> dict[str, Any]:
        samples = self._meta.get("samples", {})
        total = sum(int(v) for v in samples.values())
        return {
            "total_samples": total,
            "per_class": samples,
            "min_recommended": 30,
            "ready_to_train": total >= 30 and any(int(v) >= 10 for v in samples.values()),
            "dataset_dir": str(DATASET_DIR),
            "training": self.training_status(),
            "class_count": len(self.all_class_defs()),
        }

    def add_sample(
        self,
        frame_bgr: np.ndarray,
        class_id: str,
        box: list[float] | None = None,
    ) -> dict[str, Any]:
        valid = {c["id"] for c in self.all_class_defs()}
        if class_id not in valid:
            return {"ok": False, "error": f"Clase desconocida: {class_id}. Creá la prenda primero."}

        h, w = frame_bgr.shape[:2]
        if box and len(box) == 4:
            x1, y1, x2, y2 = box
        else:
            x1, y1, x2, y2 = 0.05 * w, 0.05 * h, 0.95 * w, 0.95 * h

        class_idx = self.class_index(class_id)
        cx = ((x1 + x2) / 2) / w
        cy = ((y1 + y2) / 2) / h
        bw = (x2 - x1) / w
        bh = (y2 - y1) / h
        cx, cy, bw, bh = [max(0.0, min(1.0, v)) for v in (cx, cy, bw, bh)]

        # Reducir frames muy grandes (ahorra disco/entrenamiento)
        max_side = 960
        if max(h, w) > max_side:
            scale = max_side / max(h, w)
            frame_bgr = cv2.resize(frame_bgr, (int(w * scale), int(h * scale)))

        sample_id = uuid.uuid4().hex[:12]
        img_path = DATASET_DIR / "images" / f"{sample_id}.jpg"
        lbl_path = DATASET_DIR / "labels" / f"{sample_id}.txt"
        cv2.imwrite(str(img_path), frame_bgr, [int(cv2.IMWRITE_JPEG_QUALITY), 88])
        lbl_path.write_text(f"{class_idx} {cx:.6f} {cy:.6f} {bw:.6f} {bh:.6f}\n", encoding="utf-8")

        samples = self._meta.setdefault("samples", {})
        samples[class_id] = int(samples.get(class_id, 0)) + 1
        self._write_meta(self._meta)

        return {
            "ok": True,
            "sample_id": sample_id,
            "class_id": class_id,
            "count": samples[class_id],
            "message": f"Ejemplo guardado para '{class_id}' (total {samples[class_id]})",
        }

    def add_samples_batch(self, frames: list[np.ndarray], class_id: str) -> dict[str, Any]:
        ok = 0
        errors: list[str] = []
        last: dict[str, Any] = {}
        for frame in frames:
            res = self.add_sample(frame, class_id=class_id)
            if res.get("ok"):
                ok += 1
                last = res
            else:
                errors.append(str(res.get("error")))
        return {
            "ok": ok > 0,
            "saved": ok,
            "failed": len(errors),
            "class_id": class_id,
            "count": last.get("count"),
            "message": f"Guardados {ok} ejemplos" + (f" · {len(errors)} con error" if errors else ""),
            "errors": errors[:5],
        }

    def add_from_video(
        self,
        video_bytes: bytes,
        class_id: str,
        *,
        max_frames: int = 40,
        stride: int = 12,
    ) -> dict[str, Any]:
        valid = {c["id"] for c in self.all_class_defs()}
        if class_id not in valid:
            return {"ok": False, "error": f"Clase desconocida: {class_id}"}
        if not video_bytes:
            return {"ok": False, "error": "Video vacío"}

        tmp = DATASET_DIR / "tmp_uploads"
        tmp.mkdir(parents=True, exist_ok=True)
        path = tmp / f"{uuid.uuid4().hex}.mp4"
        path.write_bytes(video_bytes)
        cap = cv2.VideoCapture(str(path))
        if not cap.isOpened():
            path.unlink(missing_ok=True)
            return {"ok": False, "error": "No se pudo leer el video. Probá MP4/MOV."}

        frames: list[np.ndarray] = []
        idx = 0
        max_frames = max(1, min(int(max_frames), 80))
        stride = max(1, int(stride))
        while len(frames) < max_frames:
            ok, frame = cap.read()
            if not ok:
                break
            if idx % stride == 0:
                frames.append(frame)
            idx += 1
        cap.release()
        path.unlink(missing_ok=True)

        if not frames:
            return {"ok": False, "error": "El video no entregó frames útiles"}

        batch = self.add_samples_batch(frames, class_id)
        batch["source"] = "video"
        batch["frames_extracted"] = len(frames)
        batch["message"] = (
            f"Video: {len(frames)} frames → {batch.get('saved', 0)} ejemplos de '{class_id}'"
        )
        return batch

    def write_data_yaml(self) -> Path:
        names = [c["id"] for c in self.all_class_defs()]
        yaml_path = DATASET_DIR / "data.yaml"
        content = (
            f"path: {DATASET_DIR.as_posix()}\n"
            f"train: images\n"
            f"val: images\n"
            f"names:\n"
            + "\n".join(f"  {i}: {n}" for i, n in enumerate(names))
            + "\n"
        )
        yaml_path.write_text(content, encoding="utf-8")
        return yaml_path

    def start_training(self, epochs: int = 40, model: str = "yolov8n.pt") -> dict[str, Any]:
        stats = self.stats()
        if stats["total_samples"] < 10:
            return {
                "ok": False,
                "error": "Necesitas al menos ~10–30 fotos/videos por clase clave. Seguí cargando ejemplos.",
            }
        if self._train_proc and self._train_proc.poll() is None:
            return {"ok": False, "error": "Ya hay un entrenamiento en curso"}

        yaml_path = self.write_data_yaml()
        RUNS_DIR.mkdir(parents=True, exist_ok=True)
        log_file = RUNS_DIR / "last_train.log"

        import sys

        cmd = [
            sys.executable,
            "-c",
            (
                "from ultralytics import YOLO; "
                f"m=YOLO({model!r}); "
                f"m.train(data=r'{yaml_path}', epochs={epochs}, imgsz=640, "
                f"project=r'{RUNS_DIR}', name='run', exist_ok=True)"
            ),
        ]

        self._train_log = ""
        log_fh = open(log_file, "w", encoding="utf-8")  # noqa: SIM115
        self._train_proc = subprocess.Popen(
            cmd,
            stdout=log_fh,
            stderr=subprocess.STDOUT,
            cwd=str(BASE),
        )
        return {
            "ok": True,
            "pid": self._train_proc.pid,
            "epochs": epochs,
            "log": str(log_file),
            "classes": len(self.all_class_defs()),
            "samples": stats["total_samples"],
            "message": (
                f"Entrenamiento iniciado ({epochs} épocas, {stats['total_samples']} ejemplos). "
                "Al terminar, activá el modelo personalizado."
            ),
        }

    def training_status(self) -> dict[str, Any]:
        running = self._train_proc is not None and self._train_proc.poll() is None
        best = RUNS_DIR / "run" / "weights" / "best.pt"
        return {
            "running": running,
            "exit_code": None if self._train_proc is None else self._train_proc.poll(),
            "custom_model_ready": best.exists(),
            "custom_model_path": str(best) if best.exists() else None,
        }

    def guide(self) -> dict[str, Any]:
        return {
            "title": "Cómo enseñar EPP y prendas nuevas a VigiEPP",
            "steps": [
                "1. Elegí una clase existente o creá una prenda nueva (ej. casaca naranja empresa X).",
                "2. Cargá muchas fotos y/o un video de esa prenda en tu faena real.",
                "3. Variá ángulos, luz, distancia y personas distintas.",
                "4. Incluí también violaciones (sin casco / sin chaleco / sin EPP).",
                "5. Cuando haya suficientes ejemplos, Entrená y luego Activá el modelo.",
            ],
            "tips": [
                "Prendas no establecidas: creá la clase y alimentala con 30–80 fotos o 1–2 videos.",
                "Video: el sistema extrae frames automáticamente (ideal para recorrer el uniforme).",
                "Mejor calidad > cantidad: nítidas, sin blur, EPP bien visible.",
                "Tras activar, el detector usa tu modelo propio además del flujo de identidad.",
            ],
            "classes": self.list_classes(),
            "stats": self.stats(),
        }
