"""Identificación de trabajadores: QR de cédula + reconocimiento facial (YuNet + SFace)."""

from __future__ import annotations

import json
import logging
import re
import threading
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

import cv2
import numpy as np

logger = logging.getLogger("vigiepp.identity")

from .paths import data_dir, face_models_dir

DATA_DIR = data_dir()
WORKERS_FILE = DATA_DIR / "workers.json"
FACES_DIR = DATA_DIR / "faces"
MODELS_DIR = face_models_dir()
YUNET_PATH = MODELS_DIR / "face_detection_yunet_2023mar.onnx"
SFACE_PATH = MODELS_DIR / "face_recognition_sface_2021dec.onnx"

# Umbral cosine SFace (OpenCV recomienda ~0.363). Un poco más permisivo para demo.
DEFAULT_THRESHOLD = 0.36

RUT_RE = re.compile(r"\b(\d{1,2}\.?\d{3}\.?\d{3})\-?([0-9Kk])\b")


@dataclass
class Worker:
    id: str
    name: str
    rut: str
    enrolled_at: str
    face_samples: int = 0
    source: str = "manual"
    notes: str = ""
    active: bool = True
    group: str = ""
    last_seen: str = ""
    quality: int = 0


def compute_quality(face_samples: int) -> int:
    """Score 0–100 según cantidad de muestras faciales."""
    n = int(face_samples or 0)
    if n <= 0:
        return 0
    if n == 1:
        return 25
    if n == 2:
        return 50
    if n == 3:
        return 70
    if n == 4:
        return 85
    if n >= 6:
        return 100
    return 90


def worker_from_dict(item: dict[str, Any]) -> Worker:
    return Worker(
        id=str(item.get("id") or ""),
        name=str(item.get("name") or ""),
        rut=str(item.get("rut") or ""),
        enrolled_at=str(item.get("enrolled_at") or ""),
        face_samples=int(item.get("face_samples") or 0),
        source=str(item.get("source") or "manual"),
        notes=str(item.get("notes") or ""),
        active=bool(item.get("active", True)),
        group=str(item.get("group") or ""),
        last_seen=str(item.get("last_seen") or ""),
        quality=int(item.get("quality") or compute_quality(item.get("face_samples") or 0)),
    )


def worker_public(w: Worker) -> dict[str, Any]:
    d = asdict(w)
    folder = FACES_DIR / w.id
    has_photo = False
    if folder.exists():
        has_photo = any(folder.glob("face_*.jpg"))
    d["has_photo"] = has_photo
    d["photo_url"] = f"/api/identity/workers/{w.id}/photo" if has_photo else None
    d["quality"] = w.quality or compute_quality(w.face_samples)
    return d


def _download(url: str, target: Path) -> None:
    import subprocess

    target.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(["curl", "-k", "-L", url, "-o", str(target)], check=True)
    if not target.exists() or target.stat().st_size < 1000:
        raise RuntimeError(f"No se pudo descargar {target.name}")


class IdentityRegistry:
    """Registro local de trabajadores + embeddings faciales SFace."""

    _instance: IdentityRegistry | None = None
    _lock = threading.Lock()

    def __init__(self) -> None:
        global DATA_DIR, WORKERS_FILE, FACES_DIR, MODELS_DIR, YUNET_PATH, SFACE_PATH
        DATA_DIR = data_dir()
        WORKERS_FILE = DATA_DIR / "workers.json"
        FACES_DIR = DATA_DIR / "faces"
        MODELS_DIR = face_models_dir()
        YUNET_PATH = MODELS_DIR / "face_detection_yunet_2023mar.onnx"
        SFACE_PATH = MODELS_DIR / "face_recognition_sface_2021dec.onnx"
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        FACES_DIR.mkdir(parents=True, exist_ok=True)
        MODELS_DIR.mkdir(parents=True, exist_ok=True)
        self._workers: dict[str, Worker] = {}
        self._embeddings: dict[str, list[np.ndarray]] = {}
        self._qr = cv2.QRCodeDetector()
        self._detector: Any = None
        self._recognizer: Any = None
        self._backend = "none"
        self._init_face_models()
        self._load()
        self._migrate_embeddings()

    def _init_face_models(self) -> None:
        try:
            if not YUNET_PATH.exists():
                _download(
                    "https://github.com/opencv/opencv_zoo/raw/main/models/face_detection_yunet/face_detection_yunet_2023mar.onnx",
                    YUNET_PATH,
                )
            if not SFACE_PATH.exists():
                _download(
                    "https://github.com/opencv/opencv_zoo/raw/main/models/face_recognition_sface/face_recognition_sface_2021dec.onnx",
                    SFACE_PATH,
                )
            self._detector = cv2.FaceDetectorYN_create(
                str(YUNET_PATH), "", (320, 320), 0.45, 0.3, 5000
            )
            self._recognizer = cv2.FaceRecognizerSF_create(str(SFACE_PATH), "")
            self._backend = "sface"
            logger.info("Identidad facial: YuNet + SFace listos")
        except Exception as exc:  # noqa: BLE001
            logger.exception("No se pudo cargar YuNet/SFace: %s", exc)
            self._backend = "none"

    @classmethod
    def get(cls) -> IdentityRegistry:
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls()
            return cls._instance

    def _load(self) -> None:
        if not WORKERS_FILE.exists():
            return
        raw = json.loads(WORKERS_FILE.read_text(encoding="utf-8"))
        for item in raw.get("workers", []):
            try:
                w = worker_from_dict(item)
                if w.id:
                    self._workers[w.id] = w
            except Exception:  # noqa: BLE001
                logger.exception("Worker inválido en workers.json: %s", item)

    def _save(self) -> None:
        payload = {
            "workers": [asdict(w) for w in self._workers.values()],
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        WORKERS_FILE.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    def _migrate_embeddings(self) -> None:
        """Regenera embeddings SFace desde fotos guardadas (invalida .npy antiguos)."""
        if self._backend != "sface" or self._recognizer is None:
            return
        for wid, worker in list(self._workers.items()):
            folder = FACES_DIR / wid
            if not folder.exists():
                continue
            # borrar embeddings viejos (histograma 256-d)
            for old in folder.glob("emb_*.npy"):
                old.unlink(missing_ok=True)
            embs: list[np.ndarray] = []
            for img_path in sorted(folder.glob("face_*.jpg")):
                img = cv2.imread(str(img_path))
                if img is None:
                    continue
                feat = self.extract_feature_from_image(img)
                if feat is None:
                    # la foto guardada ya es un crop: forzar feature directa
                    try:
                        aligned = cv2.resize(img, (112, 112))
                        feat = self._recognizer.feature(aligned).flatten().astype(np.float32)
                    except Exception:  # noqa: BLE001
                        continue
                embs.append(feat)
                np.save(folder / f"emb_{len(embs):03d}.npy", feat)
            self._embeddings[wid] = embs
            worker.face_samples = len(embs)
            logger.info("Migrados %s embeddings SFace para %s", len(embs), worker.name)
        self._save()

    def extract_feature_from_image(self, frame_bgr: np.ndarray) -> Optional[np.ndarray]:
        faces = self.detect_faces(frame_bgr)
        if not faces:
            return None
        # cara más grande
        face_row = max(faces, key=lambda f: f[2] * f[3])
        return self.feature_from_face(frame_bgr, face_row)

    def detect_faces(self, frame_bgr: np.ndarray) -> list[np.ndarray]:
        """Devuelve filas YuNet [x,y,w,h, landmarks..., score]."""
        if self._backend != "sface" or self._detector is None:
            return []
        h, w = frame_bgr.shape[:2]
        self._detector.setInputSize((w, h))
        _, faces = self._detector.detect(frame_bgr)
        if faces is not None and len(faces) > 0:
            return [f for f in faces]

        # Reintento: espejo (muchas webcams se ven espejadas al usuario)
        mirrored = cv2.flip(frame_bgr, 1)
        self._detector.setInputSize((w, h))
        _, faces_m = self._detector.detect(mirrored)
        if faces_m is None or len(faces_m) == 0:
            return []
        # Remapear coords al frame original
        out = []
        for f in faces_m:
            f2 = f.copy()
            f2[0] = w - f[0] - f[2]  # x espejado
            # landmarks x (índices 4,6,8,10,12)
            for i in (4, 6, 8, 10, 12):
                f2[i] = w - f[i]
            out.append(f2)
        return out

    def feature_from_face(self, frame_bgr: np.ndarray, face_row: np.ndarray) -> Optional[np.ndarray]:
        if self._recognizer is None:
            return None
        try:
            aligned = self._recognizer.alignCrop(frame_bgr, face_row)
            feat = self._recognizer.feature(aligned)
            return feat.flatten().astype(np.float32)
        except Exception as exc:  # noqa: BLE001
            logger.warning("feature_from_face falló: %s", exc)
            return None

    def match_score(self, a: np.ndarray, b: np.ndarray) -> float:
        if self._recognizer is None:
            return float(np.dot(a, b) / ((np.linalg.norm(a) * np.linalg.norm(b)) + 1e-8))
        # SFace cosine
        return float(
            self._recognizer.match(
                a.reshape(1, -1),
                b.reshape(1, -1),
                cv2.FaceRecognizerSF_FR_COSINE,
            )
        )

    def list_workers(self) -> list[dict[str, Any]]:
        return [
            worker_public(w)
            for w in sorted(self._workers.values(), key=lambda x: x.name.lower())
        ]

    def touch_last_seen(self, worker_id: str) -> None:
        w = self._workers.get(worker_id)
        if not w:
            return
        now = datetime.now(timezone.utc)
        now_iso = now.isoformat()
        prev = w.last_seen or ""
        w.last_seen = now_iso
        self._workers[worker_id] = w
        should_save = True
        if prev:
            try:
                older = datetime.fromisoformat(prev.replace("Z", "+00:00"))
                if older.tzinfo is None:
                    older = older.replace(tzinfo=timezone.utc)
                should_save = (now - older).total_seconds() > 45
            except Exception:  # noqa: BLE001
                should_save = True
        if should_save:
            self._save()

    def set_quality(self, worker_id: str) -> None:
        w = self._workers.get(worker_id)
        if not w:
            return
        w.quality = compute_quality(w.face_samples)
        self._workers[worker_id] = w

    def delete_worker(self, worker_id: str) -> bool:
        if worker_id not in self._workers:
            return False
        del self._workers[worker_id]
        self._embeddings.pop(worker_id, None)
        folder = FACES_DIR / worker_id
        if folder.exists():
            for f in folder.iterdir():
                f.unlink(missing_ok=True)
            folder.rmdir()
        self._save()
        return True


def normalize_rut(value: str) -> str:
    clean = re.sub(r"[^0-9Kk]", "", value.upper())
    if len(clean) < 2:
        return value.strip().upper()
    body, dv = clean[:-1], clean[-1]
    return f"{int(body)}-{dv}"


def validate_rut(rut: str) -> bool:
    try:
        clean = re.sub(r"[^0-9Kk]", "", rut.upper())
        body, dv = clean[:-1], clean[-1]
        if not body.isdigit():
            return False
        factors = [2, 3, 4, 5, 6, 7]
        total = 0
        for i, digit in enumerate(reversed(body)):
            total += int(digit) * factors[i % len(factors)]
        rest = 11 - (total % 11)
        check = "0" if rest == 11 else "K" if rest == 10 else str(rest)
        return check == dv
    except Exception:  # noqa: BLE001
        return False


def extract_rut_from_text(text: str) -> Optional[str]:
    if not text:
        return None
    for match in RUT_RE.finditer(text):
        candidate = f"{match.group(1)}-{match.group(2)}"
        norm = normalize_rut(candidate)
        if validate_rut(norm):
            return norm
    compact = re.sub(r"[^0-9Kk]", "", text.upper())
    m = re.search(r"(\d{7,8}[0-9K])", compact)
    if m:
        norm = normalize_rut(m.group(1))
        if validate_rut(norm):
            return norm
    return None


class IdentityService:
    def __init__(self) -> None:
        self.registry = IdentityRegistry.get()

    def read_qr(self, frame_bgr: np.ndarray) -> dict[str, Any]:
        data, points, _ = self.registry._qr.detectAndDecode(frame_bgr)
        result: dict[str, Any] = {
            "found": bool(data),
            "raw": data or None,
            "rut": extract_rut_from_text(data) if data else None,
            "points": None,
        }
        if points is not None:
            result["points"] = points.reshape(-1, 2).astype(float).tolist()
        if not result["found"]:
            h, w = frame_bgr.shape[:2]
            crop = frame_bgr[h // 6 : 5 * h // 6, w // 6 : 5 * w // 6]
            big = cv2.resize(crop, None, fx=1.8, fy=1.8, interpolation=cv2.INTER_CUBIC)
            data2, points2, _ = self.registry._qr.detectAndDecode(big)
            if data2:
                result["found"] = True
                result["raw"] = data2
                result["rut"] = extract_rut_from_text(data2)
                if points2 is not None:
                    result["points"] = points2.reshape(-1, 2).astype(float).tolist()
        return result

    def enroll(
        self,
        frame_bgr: np.ndarray,
        name: str,
        rut: str = "",
        source: str = "manual",
        notes: str = "",
    ) -> dict[str, Any]:
        if self.registry._backend != "sface":
            return {"ok": False, "error": "Motor facial no disponible (YuNet/SFace)"}

        qr = self.read_qr(frame_bgr)
        if not rut and qr.get("rut"):
            rut = qr["rut"]
            source = "qr" if source == "manual" else source
        rut_norm = normalize_rut(rut) if rut else ""
        if rut_norm and not validate_rut(rut_norm):
            return {"ok": False, "error": f"RUT inválido: {rut_norm}"}

        faces = self.registry.detect_faces(frame_bgr)
        if not faces:
            if rut_norm:
                worker = self._upsert_worker(
                    name or f"Trabajador {rut_norm}", rut_norm, source="qr", notes=notes
                )
                return {
                    "ok": True,
                    "worker": asdict(worker),
                    "qr": qr,
                    "face_enrolled": False,
                    "message": "Registrado por QR/RUT (acercá la cara a la cámara para enrolar rostro)",
                }
            return {
                "ok": False,
                "error": "No se detectó rostro. Mirá de frente a la cámara con buena luz.",
            }

        face_row = max(faces, key=lambda f: float(f[2]) * float(f[3]))
        feat = self.registry.feature_from_face(frame_bgr, face_row)
        if feat is None:
            return {"ok": False, "error": "No se pudo extraer huella facial. Reintentá."}

        x, y, w, h = [int(v) for v in face_row[:4]]
        H, W = frame_bgr.shape[:2]
        pad = int(0.2 * max(w, h))
        x1, y1 = max(0, x - pad), max(0, y - pad)
        x2, y2 = min(W, x + w + pad), min(H, y + h + pad)
        crop = frame_bgr[y1:y2, x1:x2]

        existing = None
        if rut_norm:
            existing = next((w for w in self.registry._workers.values() if w.rut == rut_norm), None)
        if not existing and name.strip():
            # si mismo nombre reciente sin RUT, sumar muestra
            existing = next(
                (
                    w
                    for w in self.registry._workers.values()
                    if w.name.lower() == name.strip().lower() and w.rut.startswith("SIN-RUT")
                ),
                None,
            )

        if existing:
            worker = existing
            if name.strip():
                worker.name = name.strip()
        else:
            display_name = name.strip() or (
                f"Trabajador {rut_norm}" if rut_norm else f"Persona {len(self.registry._workers) + 1}"
            )
            worker = self._upsert_worker(
                display_name,
                rut_norm or f"SIN-RUT-{uuid.uuid4().hex[:6]}",
                source=source,
                notes=notes,
            )

        folder = FACES_DIR / worker.id
        folder.mkdir(parents=True, exist_ok=True)
        idx = worker.face_samples + 1
        np.save(folder / f"emb_{idx:03d}.npy", feat)
        cv2.imwrite(str(folder / f"face_{idx:03d}.jpg"), crop)
        worker.face_samples = idx
        worker.quality = compute_quality(idx)
        self.registry._embeddings.setdefault(worker.id, []).append(feat)
        self.registry._workers[worker.id] = worker
        self.registry._save()

        return {
            "ok": True,
            "worker": worker_public(worker),
            "qr": qr,
            "face_enrolled": True,
            "face_box": [x1, y1, x2, y2],
            "samples": worker.face_samples,
            "message": (
                f"Enrolado: {worker.name} — muestra {worker.face_samples} · calidad {worker.quality}%. "
                f"{'Listo para identificar.' if worker.face_samples >= 2 else 'Recomendado: enrolá 2–3 veces más (gira un poco la cabeza).'}"
            ),
        }

    def _upsert_worker(self, name: str, rut: str, source: str, notes: str) -> Worker:
        for w in self.registry._workers.values():
            if w.rut == rut:
                w.name = name or w.name
                w.source = source
                if notes:
                    w.notes = notes
                self.registry._save()
                return w
        worker = Worker(
            id=uuid.uuid4().hex[:10],
            name=name,
            rut=rut,
            enrolled_at=datetime.now(timezone.utc).isoformat(),
            face_samples=0,
            source=source,
            notes=notes,
        )
        self.registry._workers[worker.id] = worker
        self.registry._save()
        return worker

    def identify(self, frame_bgr: np.ndarray, threshold: float = DEFAULT_THRESHOLD) -> dict[str, Any]:
        qr = self.read_qr(frame_bgr)
        by_qr = None
        if qr.get("rut"):
            by_qr = next(
                (
                    w
                    for w in self.registry._workers.values()
                    if w.rut == qr["rut"] and getattr(w, "active", True)
                ),
                None,
            )

        annotated = frame_bgr.copy()
        matches: list[dict[str, Any]] = []

        if qr.get("points"):
            pts = np.array(qr["points"], dtype=np.int32)
            cv2.polylines(annotated, [pts], True, (0, 180, 255), 2)

        faces = self.registry.detect_faces(frame_bgr)
        if not faces and self.registry._backend != "sface":
            cv2.putText(
                annotated,
                "Motor facial no disponible",
                (20, 40),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.8,
                (50, 50, 220),
                2,
            )

        for face_row in faces:
            x, y, w, h = [int(v) for v in face_row[:4]]
            feat = self.registry.feature_from_face(frame_bgr, face_row)
            best_id, best_score, second = None, -1.0, -1.0
            if feat is not None:
                for wid, embs in self.registry._embeddings.items():
                    cand = self.registry._workers.get(wid)
                    if not cand or not getattr(cand, "active", True) or not embs:
                        continue
                    score = max(self.registry.match_score(feat, e) for e in embs)
                    if score > best_score:
                        second = best_score
                        best_score, best_id = score, wid
                    elif score > second:
                        second = score

            worker = None
            # Acepta si supera umbral, o si es claramente el mejor (margen vs 2do)
            accepted = False
            if best_id is not None and best_score >= threshold:
                accepted = True
            elif best_id is not None and best_score >= threshold * 0.85 and (best_score - second) >= 0.08:
                accepted = True

            if accepted:
                worker = self.registry._workers[best_id]
                if not getattr(worker, "active", True):
                    worker = None
                    accepted = False
                else:
                    label = f"{worker.name}"
            if not accepted:
                label = "Desconocido"

            color = (46, 160, 67) if worker else (50, 50, 220)
            cv2.rectangle(annotated, (x, y), (x + w, y + h), color, 2)
            score_txt = f"{best_score:.0%}" if best_id is not None else "—"
            cv2.putText(
                annotated,
                f"{label} {score_txt}",
                (x, max(24, y - 8)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.65,
                color,
                2,
            )
            matches.append(
                {
                    "box": [x, y, x + w, y + h],
                    "score": round(float(best_score), 3) if best_id is not None else None,
                    "threshold": threshold,
                    "worker": worker_public(worker) if worker else None,
                    "known": worker is not None,
                    "best_candidate": (
                        worker_public(self.registry._workers[best_id]) if best_id and not worker else None
                    ),
                }
            )

        if not faces:
            cv2.putText(
                annotated,
                "Sin rostro detectado — mira de frente",
                (20, 40),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.75,
                (50, 50, 220),
                2,
            )

        identified = None
        if by_qr:
            identified = worker_public(by_qr)
            method = "qr"
            self.registry.touch_last_seen(by_qr.id)
        elif matches and matches[0].get("worker"):
            identified = matches[0]["worker"]
            method = "face"
            wid = identified.get("id")
            if wid:
                self.registry.touch_last_seen(wid)
        else:
            method = "none"
            if qr.get("rut") and not by_qr:
                identified = {
                    "id": None,
                    "name": "No enrolado",
                    "rut": qr["rut"],
                    "enrolled_at": None,
                    "face_samples": 0,
                    "source": "qr",
                    "notes": "RUT leído pero no está en la base local",
                    "active": True,
                    "group": "",
                    "last_seen": "",
                    "quality": 0,
                    "has_photo": False,
                    "photo_url": None,
                }
                method = "qr_unknown"

        return {
            "ok": True,
            "method": method,
            "qr": qr,
            "matches": matches,
            "identified": identified,
            "faces_detected": len(faces),
            "backend": self.registry._backend,
            "threshold": threshold,
            "annotated": annotated,
        }
