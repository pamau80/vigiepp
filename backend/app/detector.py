"""Carga del modelo YOLO de EPP e inferencia sobre frames."""

from __future__ import annotations

import logging
import threading
from pathlib import Path
from typing import Any

import cv2
import numpy as np

from .paths import custom_weights_path

logger = logging.getLogger("vigiepp.detector")

# Etiquetas amigables en español para la UI
LABEL_ES: dict[str, str] = {
    "Hardhat": "Casco",
    "hardhat": "Casco",
    "Helmet": "Casco",
    "casco": "Casco",
    "Safety Vest": "Ropa completa / chaleco",
    "Vest": "Chaleco",
    "chaleco_fluor": "Chaleco / ropa flúor",
    "Goggles": "Lentes de seguridad",
    "lentes": "Lentes de seguridad",
    "Gloves": "Guantes",
    "guantes": "Guantes",
    "Person": "Persona",
    "Human": "Persona",
    "Mask": "Mascarilla",
    "polera": "Polera",
    "pantalon_azul_franja": "Pantalón azul c/ franja",
    "zapatos_seguridad": "Zapatos de seguridad",
    "arnes": "Arnés",
    "sin_casco": "SIN casco",
    "sin_chaleco": "SIN chaleco",
    "NO-Hardhat": "SIN casco",
    "No-Helmet": "SIN casco",
    "NO-Safety Vest": "SIN chaleco",
    "NO-Goggles": "SIN lentes",
    "NO-Gloves": "SIN guantes",
    "NO-Mask": "SIN mascarilla",
    "No_Harness": "SIN arnés",
    "Fall-Detected": "Caída detectada",
    "Ladder": "Escalera",
    "Safety Cone": "Cono de seguridad",
}

# Colores BGR por categoría (para dibujar)
COLOR_OK = (46, 160, 67)       # verde
COLOR_BAD = (50, 50, 220)      # rojo
COLOR_PERSON = (220, 160, 40)  # ámbar
COLOR_INFO = (200, 180, 80)


class PPEDetector:
    """Singleton lazy: descarga el modelo la primera vez que se usa."""

    _instance: PPEDetector | None = None
    _lock = threading.Lock()
    _load_started = False

    def __init__(self) -> None:
        self.model = None
        self.model_name = "Cargando…"
        self.ready = False
        self.error: str | None = None
        self.using_custom = False

    @classmethod
    def get(cls) -> PPEDetector:
        """Devuelve el singleton. La carga pesada NO retiene el lock (evita timeouts en Render)."""
        if cls._instance is not None and cls._instance.ready:
            return cls._instance
        should_load = False
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls()
            if not cls._load_started:
                cls._load_started = True
                should_load = True
            inst = cls._instance
        if should_load:
            inst._load()
        return inst

    @classmethod
    def peek(cls) -> PPEDetector | None:
        """No bloquea ni inicia carga."""
        return cls._instance

    @classmethod
    def try_get(cls) -> PPEDetector | None:
        return cls._instance

    def load_custom_model(self, weights: Path | str | None = None) -> dict[str, Any]:
        """Activa un modelo entrenado por el cliente (teach)."""
        from ultralytics import YOLO

        path = Path(weights) if weights else custom_weights_path()
        if not path.exists():
            return {"ok": False, "error": f"No existe modelo personalizado en {path}"}
        self.model = YOLO(str(path))
        self.model_name = f"Personalizado ({path.name})"
        self.using_custom = True
        self.ready = True
        self.error = None
        return {"ok": True, "model": self.model_name, "path": str(path)}

    def _resolve_weights(self, cache: Path) -> Path:
        """Busca pesos locales o los descarga (con fallback por SSL corporativo)."""
        candidates = [
            cache / "best_ppe.pt",
            cache / "v2" / "best.pt",
            cache / "best.pt",
        ]
        for path in candidates:
            if path.exists() and path.stat().st_size > 1_000_000:
                return path

        # 1) Hugging Face hub
        try:
            from huggingface_hub import hf_hub_download

            weights = hf_hub_download(
                repo_id="ayushgupta7777/safetyvision-yolov8",
                filename="v2/best.pt",
                local_dir=str(cache),
            )
            return Path(weights)
        except Exception as exc:  # noqa: BLE001
            logger.warning("hf_hub_download falló (%s). Intentando curl...", exc)

        # 2) curl -k (útil con proxies/antivirus que rompen SSL)
        import subprocess

        target = cache / "best_ppe.pt"
        url = "https://huggingface.co/ayushgupta7777/safetyvision-yolov8/resolve/main/v2/best.pt"
        subprocess.run(
            ["curl", "-k", "-L", url, "-o", str(target)],
            check=True,
            capture_output=True,
            text=True,
        )
        if not target.exists() or target.stat().st_size < 1_000_000:
            raise RuntimeError("Descarga del modelo EPP incompleta")
        return target

    def _load(self) -> None:
        try:
            from ultralytics import YOLO

            cache = Path(__file__).resolve().parents[1] / "models"
            cache.mkdir(parents=True, exist_ok=True)

            logger.info("Cargando modelo EPP (primera vez puede descargar ~22 MB)...")
            weights = self._resolve_weights(cache)
            self.model = YOLO(str(weights))
            self.model_name = "SafetyVision YOLOv8s (EPP)"
            self.ready = True
            logger.info("Modelo listo: %s (%s)", self.model_name, weights.name)
        except Exception as exc:
            self.error = str(exc)
            self.ready = False
            logger.exception("No se pudo cargar el modelo EPP: %s", exc)
            # Fallback: YOLO genérico solo personas (demo degradada)
            try:
                from ultralytics import YOLO

                self.model = YOLO("yolov8n.pt")
                self.model_name = "YOLOv8n COCO (fallback — solo personas)"
                self.ready = True
                self.error = f"Modelo EPP no disponible ({exc}). Usando fallback."
                logger.warning(self.error)
            except Exception as exc2:  # noqa: BLE001
                self.error = f"Fallo total de carga: {exc2}"
                self.ready = False

    def predict(
        self,
        frame_bgr: np.ndarray,
        conf: float = 0.35,
        imgsz: int = 416,
        annotate: bool = True,
    ) -> tuple[list[dict[str, Any]], np.ndarray]:
        if not self.ready or self.model is None:
            annotated = frame_bgr.copy()
            cv2.putText(
                annotated,
                "Modelo no disponible",
                (20, 40),
                cv2.FONT_HERSHEY_SIMPLEX,
                1.0,
                COLOR_BAD,
                2,
            )
            return [], annotated

        results = self.model.predict(
            source=frame_bgr,
            conf=conf,
            imgsz=imgsz,
            verbose=False,
        )
        result = results[0]
        detections: list[dict[str, Any]] = []
        names = result.names or {}

        if result.boxes is not None:
            for box in result.boxes:
                cls_id = int(box.cls[0])
                label = names.get(cls_id, str(cls_id))
                # En fallback COCO solo nos interesan personas (clase 0)
                if "COCO" in self.model_name and label != "person":
                    continue
                conf_v = float(box.conf[0])
                xyxy = [float(x) for x in box.xyxy[0].tolist()]
                detections.append(
                    {
                        "label": label,
                        "label_es": LABEL_ES.get(label, label),
                        "confidence": round(conf_v, 3),
                        "box": xyxy,
                    }
                )

        # En monitoreo live no hace falta dibujar cajas en el servidor (el canvas del cliente lo hace).
        annotated = self.draw(frame_bgr, detections) if annotate else frame_bgr
        return detections, annotated

    def draw(self, frame_bgr: np.ndarray, detections: list[dict[str, Any]]) -> np.ndarray:
        out = frame_bgr.copy()
        for det in detections:
            label = det["label"]
            label_es = det.get("label_es", label)
            conf = det["confidence"]
            x1, y1, x2, y2 = [int(v) for v in det["box"]]

            lower = label.lower()
            if lower.startswith("no") or "fall" in lower:
                color = COLOR_BAD
            elif lower in {"person", "human"}:
                color = COLOR_PERSON
            elif any(k in lower for k in ("hat", "vest", "goggle", "glove", "mask", "helmet")):
                color = COLOR_OK
            else:
                color = COLOR_INFO

            cv2.rectangle(out, (x1, y1), (x2, y2), color, 2)
            text = f"{label_es} {conf:.0%}"
            (tw, th), _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 0.55, 2)
            cv2.rectangle(out, (x1, max(0, y1 - th - 8)), (x1 + tw + 6, y1), color, -1)
            cv2.putText(
                out,
                text,
                (x1 + 3, y1 - 5),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.55,
                (255, 255, 255),
                2,
                cv2.LINE_AA,
            )
        return out


def decode_image_bytes(data: bytes) -> np.ndarray:
    arr = np.frombuffer(data, dtype=np.uint8)
    frame = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if frame is None:
        raise ValueError("No se pudo decodificar la imagen")
    return frame


def encode_jpeg(frame_bgr: np.ndarray, quality: int = 80) -> bytes:
    ok, buf = cv2.imencode(".jpg", frame_bgr, [int(cv2.IMWRITE_JPEG_QUALITY), quality])
    if not ok:
        raise ValueError("No se pudo codificar JPEG")
    return buf.tobytes()