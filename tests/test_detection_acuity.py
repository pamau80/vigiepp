"""Pruebas de agudeza de detección — nitidez facial, match y EPP."""

from __future__ import annotations

import os
from pathlib import Path

import cv2
import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
LENA = ROOT / "tests" / "fixtures" / "lena.jpg"


def _require_face_models() -> None:
    from app.identity import SFACE_PATH, YUNET_PATH

    if not YUNET_PATH.is_file() or not SFACE_PATH.is_file():
        pytest.skip("Modelos ONNX YuNet/SFace no disponibles")


def _require_yolo() -> None:
    from app.detector import PPEDetector

    det = PPEDetector.get()
    if not det.ready:
        pytest.skip(f"Modelo YOLO EPP no listo: {det.error}")


def _load_lena() -> np.ndarray:
    if not LENA.is_file():
        pytest.skip("Fixture lena.jpg no disponible")
    img = cv2.imread(str(LENA))
    if img is None:
        pytest.skip("No se pudo decodificar lena.jpg")
    return img


def _largest_face(reg, frame: np.ndarray) -> np.ndarray:
    faces = reg.detect_faces(frame)
    if not faces:
        pytest.fail("Sin rostro detectado en fixture lena.jpg")
    return max(faces, key=lambda f: float(f[2]) * float(f[3]))


def _enroll_lena_variants(svc, count: int = 6) -> int:
    from app.detector import decode_image_bytes
    from tests.e2e.helpers import _face_jpeg_variants

    saved = 0
    for blob in _face_jpeg_variants(LENA, count):
        frame = decode_image_bytes(blob)
        result = svc.enroll(
            frame,
            name="Acuity Lena",
            rut="55.555.555-5",
            consent=True,
            notes="detection_acuity_test",
        )
        if result.get("face_enrolled"):
            saved += 1
    assert saved >= 4, f"Enrolamiento insuficiente ({saved}/4 muestras)"
    return saved


@pytest.fixture(scope="session")
def acuity_session(tmp_path_factory):
    """Carga modelos una vez y enrola fixture compartido (evita timeouts por reload)."""
    data = tmp_path_factory.mktemp("acuity")
    os.environ["VIGIEPP_DATA_DIR"] = str(data)
    os.environ["VIGIEPP_COMBINED_INFERENCE"] = "0"
    _require_face_models()
    from app.identity import IdentityRegistry, IdentityService

    reg = IdentityRegistry.get()
    svc = IdentityService()
    samples = _enroll_lena_variants(svc)
    _require_yolo()
    return {"registry": reg, "service": svc, "samples": samples}


@pytest.mark.acuity
def test_face_quality_strict_meets_enroll_thresholds(acuity_session):
    del acuity_session
    from app.identity import MIN_DETECT_SCORE, MIN_FACE_AREA_RATIO, MIN_SHARPNESS, IdentityRegistry, assess_face_quality

    img = _load_lena()
    face = _largest_face(IdentityRegistry.get(), img)
    ok, msg, meta = assess_face_quality(img, face, strict=True)
    assert ok, f"{msg} · {meta}"
    assert meta["detect_score"] >= MIN_DETECT_SCORE
    assert meta["sharpness"] >= MIN_SHARPNESS
    assert meta["area_ratio"] >= MIN_FACE_AREA_RATIO


@pytest.mark.acuity
def test_face_quality_live_accepts_porteria_frame(acuity_session):
    del acuity_session
    from app.identity import MIN_DETECT_SCORE_LIVE, MIN_FACE_AREA_RATIO_LIVE, MIN_SHARPNESS_LIVE, IdentityRegistry, assess_face_quality

    img = _load_lena()
    face = _largest_face(IdentityRegistry.get(), img)
    ok, msg, meta = assess_face_quality(img, face, strict=False)
    assert ok, f"{msg} · {meta}"
    assert meta["detect_score"] >= MIN_DETECT_SCORE_LIVE
    assert meta["sharpness"] >= MIN_SHARPNESS_LIVE
    assert meta["area_ratio"] >= MIN_FACE_AREA_RATIO_LIVE


@pytest.mark.acuity
def test_identity_match_high_confidence_after_enroll(acuity_session):
    svc = acuity_session["service"]
    img = _load_lena()
    result = svc.identify(img)
    assert result.get("faces_detected", 0) >= 1
    match = (result.get("matches") or [{}])[0]
    assert match.get("known") is True
    assert float(match.get("score") or 0) >= 0.85
    assert match.get("confidence") in ("high", "medium")


@pytest.mark.acuity
@pytest.mark.parametrize("sigma,min_score,must_known", [(1, 0.90, True), (3, 0.75, True), (5, 0.55, True)])
def test_identity_survives_moderate_blur(acuity_session, sigma, min_score, must_known):
    svc = acuity_session["service"]
    img = _load_lena()
    blurred = cv2.GaussianBlur(img, (0, 0), sigma)
    result = svc.identify(blurred)
    match = (result.get("matches") or [{}])[0]
    if must_known:
        assert result.get("faces_detected", 0) >= 1
        assert match.get("known") is True
        assert float(match.get("score") or 0) >= min_score


@pytest.mark.acuity
def test_identity_rejects_heavy_blur(acuity_session):
    svc = acuity_session["service"]
    img = _load_lena()
    blurred = cv2.GaussianBlur(img, (0, 0), 8)
    result = svc.identify(blurred)
    match = (result.get("matches") or [{}])[0]
    faces = result.get("faces_detected", 0)
    if faces >= 1:
        assert match.get("known") is not True
    else:
        assert faces == 0


@pytest.mark.acuity
@pytest.mark.parametrize("scale,min_score", [(0.75, 0.85), (0.5, 0.80), (0.35, 0.75), (0.25, 0.70)])
def test_identity_survives_downscale(acuity_session, scale, min_score):
    svc = acuity_session["service"]
    img = _load_lena()
    h, w = img.shape[:2]
    small = cv2.resize(img, (max(32, int(w * scale)), max(32, int(h * scale))))
    result = svc.identify(small)
    match = (result.get("matches") or [{}])[0]
    assert result.get("faces_detected", 0) >= 1
    assert match.get("known") is True
    assert float(match.get("score") or 0) >= min_score


@pytest.mark.acuity
def test_epp_detector_returns_confident_labels(acuity_session):
    del acuity_session
    from app.detector import PPEDetector

    img = _load_lena()
    det = PPEDetector.get()
    detections, _ = det.predict(img, conf=0.30, imgsz=416)
    assert detections, "Se esperaba al menos una detección EPP en lena.jpg"
    top = max(detections, key=lambda d: float(d.get("confidence") or 0))
    assert float(top.get("confidence") or 0) >= 0.30
    assert top.get("label_es") or top.get("label")


@pytest.mark.acuity
def test_detect_pipeline_identity_fields(acuity_session):
    del acuity_session
    import json

    from app.detect_pipeline import detect_frame

    with open(LENA, "rb") as fh:
        data = fh.read()
    resp = detect_frame(
        data,
        profile="general",
        conf=0.35,
        identify=True,
        return_image=False,
        imgsz=416,
        threshold=0.33,
    )
    payload = json.loads(resp.body)
    assert payload.get("ok") is True
    identity = payload.get("identity") or {}
    assert identity.get("faces_detected", 0) >= 1
    assert identity.get("known") is True
    assert float(identity.get("score") or 0) >= 0.80
    assert identity.get("confidence") in ("high", "medium", "low", "ambiguous", "none")
