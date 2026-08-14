"""Identificación de trabajadores: QR de cédula + reconocimiento facial (YuNet + SFace)."""

from __future__ import annotations

import json
import logging
import re
import threading
import time
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

# Modo precisión: OpenCV SFace ~0.363; usamos umbral más alto + margen obligatorio.
DEFAULT_THRESHOLD = 0.42
MIN_MATCH_MARGIN = 0.06  # diferencia mínima vs 2.º candidato
MIN_SAMPLES_READY = 4  # muestras de calidad para considerar ficha lista
MIN_SAMPLES_MATCH = 3  # por debajo: no se acepta match facial (evitar falsos)
MIN_FACE_AREA_RATIO = 0.045  # cara ≥ ~4.5% del frame
MIN_DETECT_SCORE = 0.65
MIN_SHARPNESS = 35.0  # varianza Laplaciana del crop

CONSENT_VERSION = "1"

# Liveness: pose distinta entre muestras (anti-foto impresa / replay)
MIN_LANDMARK_DELTA = 0.035
SCREEN_FLAT_MAX = 12.0  # varianza de bordes muy baja = posible pantalla/papel

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
    consent_at: str = ""
    consent_version: str = ""


def normalize_person_name(name: str) -> str:
    """Dr./Dra./Doctor → Especialista (expertos de faena, no título médico)."""
    n = (name or "").strip()
    if not n:
        return n
    n = re.sub(r"^(dra\.?|dr\.?|doctora|doctor)\b\.?\s*", "Especialista ", n, flags=re.IGNORECASE)
    return re.sub(r"\s{2,}", " ", n).strip()


def compute_quality(face_samples: int) -> int:
    """Score 0–100 según cantidad de muestras faciales de calidad."""
    n = int(face_samples or 0)
    if n <= 0:
        return 0
    if n == 1:
        return 20
    if n == 2:
        return 40
    if n == 3:
        return 60
    if n == 4:
        return 85
    if n == 5:
        return 92
    if n >= 6:
        return 100
    return 90


def is_identity_ready(face_samples: int) -> bool:
    return int(face_samples or 0) >= MIN_SAMPLES_READY


def assess_face_quality(
    frame_bgr: np.ndarray,
    face_row: np.ndarray,
) -> tuple[bool, str, dict[str, Any]]:
    """Valida tamaño, score YuNet, nitidez y frontalidad antes de enrolar/match."""
    h, w = frame_bgr.shape[:2]
    fx, fy, fw, fh = [float(v) for v in face_row[:4]]
    area_ratio = (fw * fh) / float(max(1, w * h))
    det_score = float(face_row[14]) if len(face_row) > 14 else 0.0
    meta: dict[str, Any] = {
        "area_ratio": round(area_ratio, 4),
        "detect_score": round(det_score, 3),
        "sharpness": None,
        "frontal": None,
    }

    if area_ratio < MIN_FACE_AREA_RATIO:
        return False, "Acercá más el rostro a la cámara (muy lejos).", meta
    if det_score and det_score < MIN_DETECT_SCORE:
        return False, "Rostro poco claro. Mejorá la luz y mirá de frente.", meta

    # Landmarks YuNet: RE, LE, nose, RM, LM
    if len(face_row) >= 14:
        re_x, re_y = float(face_row[4]), float(face_row[5])
        le_x, le_y = float(face_row[6]), float(face_row[7])
        nose_x = float(face_row[8])
        eye_dist = abs(le_x - re_x) + 1e-6
        eye_y_diff = abs(le_y - re_y) / max(fh, 1.0)
        nose_center = abs((nose_x - (re_x + le_x) / 2.0) / eye_dist)
        eye_span = eye_dist / max(fw, 1.0)
        frontal_ok = eye_y_diff < 0.22 and nose_center < 0.45 and 0.25 <= eye_span <= 0.95
        meta["frontal"] = round(1.0 - min(1.0, eye_y_diff + nose_center * 0.5), 3)
        if not frontal_ok:
            return False, "Mirá de frente a la cámara (sin perfil extremo).", meta

    x1 = max(0, int(fx))
    y1 = max(0, int(fy))
    x2 = min(w, int(fx + fw))
    y2 = min(h, int(fy + fh))
    crop = frame_bgr[y1:y2, x1:x2]
    if crop.size < 100:
        return False, "Recorte facial inválido. Reintentá.", meta
    gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
    sharp = float(cv2.Laplacian(gray, cv2.CV_64F).var())
    meta["sharpness"] = round(sharp, 1)
    if sharp < MIN_SHARPNESS:
        return False, "Imagen borrosa. Sostené firme y con buena luz.", meta
    return True, "ok", meta


def _landmarks(face_row: np.ndarray) -> list[float]:
    if len(face_row) < 14:
        return []
    return [float(face_row[i]) for i in range(4, 14)]


def _landmark_delta(a: list[float], b: list[float], face_w: float) -> float:
    if not a or not b or len(a) != len(b) or face_w <= 1:
        return 1.0
    dist = float(np.linalg.norm(np.asarray(a) - np.asarray(b)))
    return dist / face_w


def assess_liveness(
    frame_bgr: np.ndarray,
    face_row: np.ndarray,
    prev_lm: list[float] | None,
) -> tuple[bool, str, dict[str, Any]]:
    """Anti-spoof básico: no pantalla plana + pose distinta a la muestra anterior."""
    h, w = frame_bgr.shape[:2]
    fx, fy, fw, fh = [float(v) for v in face_row[:4]]
    x1, y1 = max(0, int(fx)), max(0, int(fy))
    x2, y2 = min(w, int(fx + fw)), min(h, int(fy + fh))
    crop = frame_bgr[y1:y2, x1:x2]
    meta: dict[str, Any] = {"liveness": "ok", "pose_delta": None}
    if crop.size < 100:
        return False, "Rostro inválido para liveness.", meta
    gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
    # Recorte interno vs borde: una foto en celular suele tener borde más “plano”
    gh, gw = gray.shape[:2]
    if gh > 12 and gw > 12:
        inner = gray[4 : gh - 4, 4 : gw - 4]
        edge = np.concatenate([gray[0:3, :].ravel(), gray[-3:, :].ravel()])
        edge_var = float(np.var(edge))
        inner_var = float(cv2.Laplacian(inner, cv2.CV_64F).var())
        meta["edge_var"] = round(edge_var, 1)
        meta["inner_sharp"] = round(inner_var, 1)
        if inner_var < SCREEN_FLAT_MAX and edge_var < 40:
            return False, "Parece foto o pantalla. Enrolá con cara real, en vivo.", meta
    lm = _landmarks(face_row)
    if prev_lm:
        delta = _landmark_delta(lm, prev_lm, max(fw, 1.0))
        meta["pose_delta"] = round(delta, 4)
        if delta < MIN_LANDMARK_DELTA:
            return False, "Mové un poco la cabeza (otra pose). No uses la misma foto.", meta
    return True, "ok", meta


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
        consent_at=str(item.get("consent_at") or ""),
        consent_version=str(item.get("consent_version") or ""),
    )


def worker_public(w: Worker) -> dict[str, Any]:
    d = asdict(w)
    d["name"] = normalize_person_name(w.name)
    folder = FACES_DIR / w.id
    has_photo = False
    emb_count = 0
    if folder.exists():
        has_photo = any(folder.glob("face_*.jpg"))
        emb_count = len(list(folder.glob("emb_*.npy")))
    samples = int(w.face_samples or emb_count or 0)
    d["has_photo"] = has_photo
    d["photo_url"] = f"/api/identity/workers/{w.id}/photo" if has_photo else None
    d["quality"] = w.quality or compute_quality(samples)
    d["ready"] = is_identity_ready(samples) and (emb_count > 0 or samples > 0)
    d["embedding_count"] = emb_count or samples
    d["min_samples_ready"] = MIN_SAMPLES_READY
    d["consent_ok"] = bool(w.consent_at)
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
    _load_started = False

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
        self._enroll_lm: dict[str, list[float]] = {}
        self._qr = cv2.QRCodeDetector()
        self._detector: Any = None
        self._recognizer: Any = None
        self._backend = "none"
        self._ready = False
        self._init_face_models()
        self._load()
        self._migrate_embeddings()
        self._ready = True

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
        if cls._instance is not None and getattr(cls._instance, "_ready", False):
            return cls._instance
        should_load = False
        with cls._lock:
            if cls._instance is not None and getattr(cls._instance, "_ready", False):
                return cls._instance
            if not cls._load_started:
                cls._load_started = True
                should_load = True
        if should_load:
            inst = cls.__new__(cls)
            inst.__init__()
            with cls._lock:
                cls._instance = inst
            return inst
        # Otro hilo está cargando: esperar sin retener lock
        for _ in range(200):  # ~20s
            time.sleep(0.1)
            if cls._instance is not None and getattr(cls._instance, "_ready", False):
                return cls._instance
        raise RuntimeError("Timeout cargando identidad facial")

    @classmethod
    def peek(cls) -> IdentityRegistry | None:
        inst = cls._instance
        if inst is None or not getattr(inst, "_ready", False):
            return None
        return inst

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
        try:
            from . import cloud_persist as cloud_mod

            cloud_mod.schedule_push()
        except Exception:  # noqa: BLE001
            logger.debug("cloud_persist schedule omitido", exc_info=True)

    def _migrate_embeddings(self) -> None:
        """Carga embeddings SFace; regenera solo si faltan .npy válidos."""
        if self._backend != "sface" or self._recognizer is None:
            return
        changed = False
        for wid, worker in list(self._workers.items()):
            folder = FACES_DIR / wid
            if not folder.exists():
                self._embeddings[wid] = []
                continue
            embs: list[np.ndarray] = []
            for emb_path in sorted(folder.glob("emb_*.npy")):
                try:
                    e = np.load(str(emb_path))
                    e = np.asarray(e, dtype=np.float32).flatten()
                    # SFace ~128-d; descartar histograma viejo u otros
                    if e.size < 64 or e.size > 512:
                        emb_path.unlink(missing_ok=True)
                        changed = True
                        continue
                    embs.append(e)
                except Exception:  # noqa: BLE001
                    emb_path.unlink(missing_ok=True)
                    changed = True

            if not embs:
                for img_path in sorted(folder.glob("face_*.jpg")):
                    img = cv2.imread(str(img_path))
                    if img is None:
                        continue
                    feat = self.extract_feature_from_image(img)
                    if feat is None:
                        # crop ya centrado: reintentar con padding + detección
                        pad = 24
                        padded = cv2.copyMakeBorder(
                            img, pad, pad, pad, pad, cv2.BORDER_REFLECT_101
                        )
                        feat = self.extract_feature_from_image(padded)
                    if feat is None:
                        logger.warning("No se pudo regenerar embedding desde %s", img_path.name)
                        continue
                    embs.append(feat)
                    np.save(folder / f"emb_{len(embs):03d}.npy", feat)
                    changed = True
                if embs:
                    logger.info("Regenerados %s embeddings SFace para %s", len(embs), worker.name)

            self._embeddings[wid] = embs
            if worker.face_samples != len(embs):
                worker.face_samples = len(embs)
                worker.quality = compute_quality(len(embs))
                changed = True
        if changed:
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
        consent: bool = False,
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
        name = normalize_person_name(name)

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
        ok_q, q_msg, q_meta = assess_face_quality(frame_bgr, face_row)
        if not ok_q:
            return {
                "ok": False,
                "error": q_msg,
                "quality_check": q_meta,
                "face_enrolled": False,
            }

        # Resolver worker candidato para liveness vs muestra previa
        existing_pre = None
        if rut_norm:
            existing_pre = next((w for w in self.registry._workers.values() if w.rut == rut_norm), None)
        if not existing_pre and name.strip():
            existing_pre = next(
                (
                    w
                    for w in self.registry._workers.values()
                    if w.name.lower() == name.strip().lower() and w.rut.startswith("SIN-RUT")
                ),
                None,
            )
        if existing_pre and not existing_pre.consent_at and not consent:
            return {
                "ok": False,
                "error": "Falta consentimiento biométrico. Marcá la casilla antes de enrolar.",
                "face_enrolled": False,
            }
        if not existing_pre and not consent:
            return {
                "ok": False,
                "error": "Falta consentimiento biométrico para registrar el rostro (Ley 19.628 / DS 44).",
                "face_enrolled": False,
            }

        prev_lm = self.registry._enroll_lm.get(existing_pre.id) if existing_pre else None
        ok_l, l_msg, l_meta = assess_liveness(frame_bgr, face_row, prev_lm)
        q_meta.update(l_meta)
        if not ok_l:
            return {
                "ok": False,
                "error": l_msg,
                "quality_check": q_meta,
                "face_enrolled": False,
            }

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
            # Evitar muestras casi idénticas (no aportan precisión)
            prior = self.registry._embeddings.get(worker.id) or []
            if prior:
                best_dup = max(self.registry.match_score(feat, e) for e in prior)
                if best_dup >= 0.97:
                    return {
                        "ok": False,
                        "error": "Muestra demasiado similar a una ya guardada. Cambiá un poco el ángulo o la expresión.",
                        "quality_check": q_meta,
                        "face_enrolled": False,
                        "duplicate_score": round(float(best_dup), 3),
                    }
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
        if consent or not worker.consent_at:
            worker.consent_at = datetime.now(timezone.utc).isoformat()
            worker.consent_version = CONSENT_VERSION
        self.registry._embeddings.setdefault(worker.id, []).append(feat)
        self.registry._enroll_lm[worker.id] = _landmarks(face_row)
        self.registry._workers[worker.id] = worker
        self.registry._save()

        ready = is_identity_ready(worker.face_samples)
        remain = max(0, MIN_SAMPLES_READY - worker.face_samples)
        return {
            "ok": True,
            "worker": worker_public(worker),
            "qr": qr,
            "face_enrolled": True,
            "face_box": [x1, y1, x2, y2],
            "samples": worker.face_samples,
            "quality_check": q_meta,
            "ready": ready,
            "message": (
                f"Enrolado: {worker.name} — muestra {worker.face_samples}/{MIN_SAMPLES_READY} · calidad {worker.quality}%. "
                + (
                    "Ficha lista para identificación estricta."
                    if ready
                    else f"Faltan {remain} muestra(s) de calidad (frente + ángulos leves)."
                )
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
            ok_q, q_msg, q_meta = assess_face_quality(frame_bgr, face_row)
            feat = self.registry.feature_from_face(frame_bgr, face_row) if ok_q else None
            best_id, best_score, second = None, -1.0, -1.0
            reject_reason = None if ok_q else q_msg

            if feat is not None:
                for wid, embs in self.registry._embeddings.items():
                    cand = self.registry._workers.get(wid)
                    if not cand or not getattr(cand, "active", True) or not embs:
                        continue
                    # Fichas con pocas muestras: no participan (evita falsos positivos)
                    if len(embs) < MIN_SAMPLES_MATCH and int(cand.face_samples or 0) < MIN_SAMPLES_MATCH:
                        continue
                    # Media de los 2 mejores matches contra la galería (más estable que un solo pico)
                    sample_scores = sorted(
                        (self.registry.match_score(feat, e) for e in embs),
                        reverse=True,
                    )
                    score = (
                        float(np.mean(sample_scores[:2]))
                        if len(sample_scores) >= 2
                        else float(sample_scores[0])
                    )
                    if score > best_score:
                        second = best_score
                        best_score, best_id = score, wid
                    elif score > second:
                        second = score

            worker = None
            accepted = False
            confidence = "none"
            thr = float(threshold)
            margin = float(best_score - second) if best_id is not None else 0.0

            if best_id is not None and feat is not None and not reject_reason:
                # Aceptación estricta: umbral + margen vs 2.º (si hay competencia)
                has_rival = second >= 0.0
                margin_ok = (not has_rival) or (margin >= MIN_MATCH_MARGIN)
                if best_score >= thr and margin_ok:
                    accepted = True
                    confidence = "high" if best_score >= thr + 0.08 and margin >= MIN_MATCH_MARGIN + 0.04 else "medium"
                elif best_score >= thr and not margin_ok:
                    reject_reason = "Ambigüedad entre dos personas parecidas"
                    confidence = "ambiguous"
                elif best_score >= thr - 0.04:
                    reject_reason = f"Score insuficiente ({best_score:.0%} < {thr:.0%})"
                    confidence = "low"
                else:
                    reject_reason = "Sin coincidencia suficiente"
                    confidence = "low"

            if accepted:
                worker = self.registry._workers[best_id]
                if not getattr(worker, "active", True):
                    worker = None
                    accepted = False
                    confidence = "none"
                    reject_reason = "Trabajador inactivo"
                else:
                    label = f"{worker.name}"
            if not accepted:
                label = "Desconocido"

            color = (46, 160, 67) if worker else (50, 50, 220)
            cv2.rectangle(annotated, (x, y), (x + w, y + h), color, 2)
            score_txt = f"{best_score:.0%}" if best_id is not None and best_score >= 0 else "—"
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
                    "score": round(float(best_score), 3) if best_id is not None and best_score >= 0 else None,
                    "second_score": round(float(second), 3) if second >= 0 else None,
                    "margin": round(float(margin), 3) if best_id is not None else None,
                    "threshold": thr,
                    "confidence": confidence,
                    "reject_reason": reject_reason,
                    "quality_check": q_meta,
                    "worker": worker_public(worker) if worker else None,
                    "known": worker is not None,
                    "best_candidate": (
                        worker_public(self.registry._workers[best_id])
                        if best_id and not worker and best_id in self.registry._workers
                        else None
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
