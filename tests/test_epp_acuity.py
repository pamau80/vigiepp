"""Agudeza de detección EPP: casco, ropa (chaleco), lentes, guantes."""

from __future__ import annotations

from pathlib import Path

import cv2
import pytest

ROOT = Path(__file__).resolve().parents[1]
PPE_DIR = ROOT / "tests" / "fixtures" / "ppe"
EPP_KEYS = ("casco", "chaleco", "lentes", "guantes")

# Imagen → categorías EPP que el dataset construction-ppe marca (referencia)
PPE_FIXTURE_EXPECT = {
    "image1009.jpg": {"casco", "chaleco"},
    "image1037.jpeg": {"casco", "chaleco"},
    "image116.jpg": {"casco", "chaleco"},
    "image122.jpeg": {"casco", "chaleco", "lentes"},
    "image1003.jpg": {"casco", "chaleco", "guantes"},
}


def _require_yolo():
    from app.detector import PPEDetector

    det = PPEDetector.get()
    if not det.ready:
        pytest.skip(f"YOLO EPP no listo: {det.error}")


def _ppe_fixtures():
    if not PPE_DIR.is_dir():
        pytest.skip("Sin fixtures tests/fixtures/ppe/")
    files = sorted(
        p for p in PPE_DIR.iterdir() if p.suffix.lower() in (".jpg", ".jpeg") and p.name != "worker_ppe.jpg"
    )
    if not files:
        pytest.skip("Sin imágenes PPE en fixtures")
    return files


@pytest.mark.acuity
def test_hardhat_maps_to_casco_in_compliance():
    from app.compliance import evaluate

    dets = [{"label": "Hardhat", "confidence": 0.8, "box": [10, 10, 100, 100]}]
    result = evaluate(dets, "general", required_override=["casco"])
    assert result.persons
    assert "casco" in result.persons[0].present


@pytest.mark.acuity
def test_epp_completo_profile_requires_four_items():
    from app.profiles import get_profile

    p = get_profile("epp_completo")
    assert p["required"] == ["casco", "chaleco", "lentes", "guantes"]


@pytest.mark.acuity
@pytest.mark.parametrize("fixture_name", sorted(PPE_FIXTURE_EXPECT.keys()))
def test_epp_fixture_detects_expected_items(fixture_name):
    """YOLO + compliance deben reconocer casco y ropa en fotos de obra reales."""
    _require_yolo()
    from app.compliance import evaluate
    from app.detector import PPEDetector

    path = PPE_DIR / fixture_name
    if not path.is_file():
        pytest.skip(f"Fixture {fixture_name} no disponible")
    img = cv2.imread(str(path))
    assert img is not None

    det = PPEDetector.get()
    detections, _ = det.predict(img, conf=0.15, imgsz=640)
    assert detections, f"Sin detecciones en {fixture_name}"

    result = evaluate(detections, "epp_completo")
    assert result.persons, f"Sin persona implícita en {fixture_name}"
    present = set(result.persons[0].present)
    expected = PPE_FIXTURE_EXPECT[fixture_name]
    missing_expected = expected - present
    assert not missing_expected, f"{fixture_name}: faltó detectar {missing_expected} · present={present}"


@pytest.mark.acuity
def test_epp_scan_reports_per_category_confidence():
    """Informe por ítem: casco, ropa, lentes, guantes con % mínimo si aparecen."""
    _require_yolo()
    from app.compliance import _category_for_label
    from app.detector import PPEDetector

    best: dict[str, float] = {k: 0.0 for k in EPP_KEYS}
    for path in _ppe_fixtures():
        img = cv2.imread(str(path))
        if img is None:
            continue
        dets, _ = PPEDetector.get().predict(img, conf=0.15, imgsz=640)
        for d in dets:
            cat = _category_for_label(d.get("label", ""))
            if cat in best:
                best[cat] = max(best[cat], float(d.get("confidence") or 0))

    # En el set de fixtures de obra, los 4 ítems deben ser detectables
    assert best["casco"] >= 0.25, f"Casco débil: {best}"
    assert best["chaleco"] >= 0.25, f"Ropa/chaleco débil: {best}"
    assert best["lentes"] >= 0.15, f"Lentes débiles: {best}"
    assert best["guantes"] >= 0.15, f"Guantes débiles: {best}"
