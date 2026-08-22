"""Reglas de cumplimiento: asocia detecciones a personas y evalúa EPP."""

from __future__ import annotations

from dataclasses import dataclass, field

from .profiles import IndustryProfile, get_profile


# Mapeo: clase del modelo → categoría interna
CLASS_TO_CATEGORY: dict[str, str] = {
    "hardhat": "casco",
    "Hardhat": "casco",
    "helmet": "casco",
    "Helmet": "casco",
    "casco": "casco",
    "Safety Vest": "chaleco",
    "safety vest": "chaleco",
    "Vest": "chaleco",
    "vest": "chaleco",
    "chaleco": "chaleco",
    "chaleco_fluor": "chaleco",
    "Goggles": "lentes",
    "goggles": "lentes",
    "lentes": "lentes",
    "Gloves": "guantes",
    "gloves": "guantes",
    "guantes": "guantes",
    "No_Harness": "sin_arnes",
    "Harness": "arnes",
    "arnes": "arnes",
    "polera": "polera",
    "pantalon_azul_franja": "pantalon",
    "pantalon_trabajo": "pantalon",
    "zapatos_seguridad": "zapatos",
    "botas": "zapatos",
    "Safety-Shoes": "zapatos",
    "safety_shoes": "zapatos",
    "casaca": "casaca",
    "chaleco_fluor": "chaleco",
    "buzo_papel": "buzo",
    "buzo": "buzo",
    "coverall": "buzo",
    "disposable_coverall": "buzo",
    "overol": "buzo",
    "uniforme_completo": "vestimenta",
    "ropa_reflectante": "reflectante",
    "Person": "persona",
    "person": "persona",
    "Human": "persona",
    "human": "persona",
    "NO-Hardhat": "sin_casco",
    "No-Helmet": "sin_casco",
    "sin_casco": "sin_casco",
    "NO-Safety Vest": "sin_chaleco",
    "sin_chaleco": "sin_chaleco",
    "NO-Goggles": "sin_lentes",
    "NO-Gloves": "sin_guantes",
    "NO-Mask": "sin_mascarilla",
    "Mask": "mascarilla",
    "mask": "mascarilla",
    "mascarilla": "mascarilla",
    "Fall-Detected": "caida",
}

# Franja vertical relativa al bbox de la persona (0 = cabeza, 1 = pies)
PPE_Y_BAND: dict[str, tuple[float, float]] = {
    "casco": (0.0, 0.50),
    "sin_casco": (0.0, 0.52),
    "lentes": (0.0, 0.42),
    "sin_lentes": (0.0, 0.42),
    "mascarilla": (0.0, 0.48),
    "sin_mascarilla": (0.0, 0.48),
    "chaleco": (0.10, 0.90),
    "sin_chaleco": (0.10, 0.90),
    "arnes": (0.08, 0.95),
    "sin_arnes": (0.08, 0.95),
    "guantes": (0.30, 1.08),
    "sin_guantes": (0.30, 1.08),
    "zapatos": (0.72, 1.15),
    "buzo": (0.05, 0.98),
    "casaca": (0.08, 0.95),
    "pantalon": (0.45, 1.05),
    "reflectante": (0.10, 0.95),
    "vestimenta": (0.05, 0.98),
}

POSITIVE_PPE = {
    "casco",
    "chaleco",
    "lentes",
    "guantes",
    "arnes",
    "mascarilla",
    "polera",
    "pantalon",
    "zapatos",
    "buzo",
    "casaca",
    "reflectante",
    "vestimenta",
}
NEGATIVE_PPE = {
    "sin_casco": "casco",
    "sin_chaleco": "chaleco",
    "sin_lentes": "lentes",
    "sin_guantes": "guantes",
    "sin_arnes": "arnes",
}


@dataclass
class Detection:
    label: str
    category: str
    confidence: float
    box: list[float]  # xyxy


@dataclass
class PersonCompliance:
    person_id: int
    box: list[float]
    present: list[str] = field(default_factory=list)
    missing: list[str] = field(default_factory=list)
    violations: list[str] = field(default_factory=list)
    compliant: bool = True
    score: float = 1.0


@dataclass
class ComplianceResult:
    profile_id: str
    profile_name: str
    persons: list[PersonCompliance]
    detections: list[Detection]
    overall_compliant: bool
    summary: str
    alerts: list[str]


def _iou(a: list[float], b: list[float]) -> float:
    ax1, ay1, ax2, ay2 = a
    bx1, by1, bx2, by2 = b
    ix1, iy1 = max(ax1, bx1), max(ay1, by1)
    ix2, iy2 = min(ax2, bx2), min(ay2, by2)
    iw, ih = max(0.0, ix2 - ix1), max(0.0, iy2 - iy1)
    inter = iw * ih
    if inter <= 0:
        return 0.0
    area_a = max(0.0, ax2 - ax1) * max(0.0, ay2 - ay1)
    area_b = max(0.0, bx2 - bx1) * max(0.0, by2 - by1)
    union = area_a + area_b - inter
    return inter / union if union > 0 else 0.0


def _center_inside(inner: list[float], outer: list[float], pad: float = 0.15) -> bool:
    ix1, iy1, ix2, iy2 = inner
    cx, cy = (ix1 + ix2) / 2, (iy1 + iy2) / 2
    ox1, oy1, ox2, oy2 = outer
    w, h = ox2 - ox1, oy2 - oy1
    return (ox1 - w * pad) <= cx <= (ox2 + w * pad) and (oy1 - h * pad) <= cy <= (oy2 + h * pad)


def category_of(label: str) -> str:
    key = str(label or "").strip()
    return CLASS_TO_CATEGORY.get(key) or CLASS_TO_CATEGORY.get(key.lower()) or key.lower().replace(" ", "_")


def _ppe_fits_person(item: Detection, person: Detection) -> bool:
    """Asocia EPP a una persona por overlap + franja anatómica (casco arriba, chaleco torso)."""
    iou = _iou(person.box, item.box)
    inside = _center_inside(item.box, person.box, pad=0.28)
    if iou < 0.04 and not inside:
        return False
    band = PPE_Y_BAND.get(item.category)
    if not band:
        return True
    py1, py2 = person.box[1], person.box[3]
    cy = (item.box[1] + item.box[3]) / 2
    rel = (cy - py1) / max(1.0, py2 - py1)
    lo, hi = band
    return (lo - 0.10) <= rel <= (hi + 0.10)


def normalize_detections(raw: list[dict]) -> list[Detection]:
    out: list[Detection] = []
    for item in raw:
        label = str(item.get("label", ""))
        category = str(item.get("category") or "") or category_of(label)
        out.append(
            Detection(
                label=label,
                category=category,
                confidence=float(item.get("confidence", 0)),
                box=[float(x) for x in item["box"]],
            )
        )
    return out


def evaluate(
    raw_detections: list[dict],
    profile_id: str = "general",
    required_override: list[str] | None = None,
) -> ComplianceResult:
    profile: IndustryProfile = get_profile(profile_id)
    required = list(required_override) if required_override is not None else list(profile["required"])
    detections = normalize_detections(raw_detections)

    persons_boxes = [d for d in detections if d.category == "persona"]
    ppe_items = [d for d in detections if d.category != "persona"]

    # Persona implícita solo con EPP positivo (no a partir de un solo NO-casco)
    if not persons_boxes:
        positives = [d for d in ppe_items if d.category in POSITIVE_PPE]
        if positives:
            xs1 = [d.box[0] for d in positives]
            ys1 = [d.box[1] for d in positives]
            xs2 = [d.box[2] for d in positives]
            ys2 = [d.box[3] for d in positives]
            x1, y1, x2, y2 = min(xs1), min(ys1), max(xs2), max(ys2)
            bw, bh = max(8.0, x2 - x1), max(8.0, y2 - y1)
            persons_boxes = [
                Detection(
                    label="Person",
                    category="persona",
                    confidence=0.5,
                    box=[x1 - 0.22 * bw, y1 - 0.18 * bh, x2 + 0.22 * bw, y2 + 0.55 * bh],
                )
            ]

    persons: list[PersonCompliance] = []
    alerts: list[str] = []

    for idx, person in enumerate(persons_boxes):
        present: set[str] = set()
        violations: list[str] = []

        for item in ppe_items:
            related = _ppe_fits_person(item, person)
            if not related:
                continue
            if item.category in POSITIVE_PPE:
                present.add(item.category)
            elif item.category in NEGATIVE_PPE:
                missing_key = NEGATIVE_PPE[item.category]
                violations.append(missing_key)
            elif item.category == "caida":
                violations.append("caida")

        missing = [r for r in required if r not in present]
        # violaciones explícitas del modelo cuentan como faltantes
        for v in violations:
            if v in required and v not in missing:
                missing.append(v)

        compliant = len(missing) == 0 and "caida" not in violations
        score = 1.0 - (len(missing) / max(len(required), 1)) * 0.7
        if "caida" in violations:
            score = 0.0
            compliant = False

        pc = PersonCompliance(
            person_id=idx + 1,
            box=person.box,
            present=sorted(present),
            missing=missing,
            violations=violations,
            compliant=compliant,
            score=round(max(0.0, min(1.0, score)), 2),
        )
        persons.append(pc)

        if not compliant:
            miss_txt = ", ".join(missing) if missing else "riesgo detectado"
            alerts.append(f"{profile['alert_message']}: falta {miss_txt} (persona #{pc.person_id})")

    overall = all(p.compliant for p in persons) if persons else True
    if not persons:
        summary = "Sin personas detectadas en el encuadre"
    elif overall:
        summary = f"Cumplimiento OK — {len(persons)} persona(s) con EPP según perfil {profile['name']}"
    else:
        n_bad = sum(1 for p in persons if not p.compliant)
        summary = f"Incumplimiento: {n_bad}/{len(persons)} persona(s) sin EPP completo"

    return ComplianceResult(
        profile_id=profile["id"],
        profile_name=profile["name"],
        persons=persons,
        detections=detections,
        overall_compliant=overall,
        summary=summary,
        alerts=alerts,
    )