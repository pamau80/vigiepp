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
    "Goggles": "lentes",
    "gloves": "guantes",
    "guantes": "guantes",
    "No_Harness": "sin_arnes",
    "Harness": "arnes",
    "arnes": "arnes",
    "polera": "polera",
    "pantalon_azul_franja": "pantalon",
    "zapatos_seguridad": "zapatos",
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
    "Fall-Detected": "caida",
}

POSITIVE_PPE = {"casco", "chaleco", "lentes", "guantes", "arnes", "polera", "pantalon", "zapatos"}
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


def _category_for_label(label: str) -> str:
    key = str(label or "").strip()
    if not key:
        return "unknown"
    if key in CLASS_TO_CATEGORY:
        return CLASS_TO_CATEGORY[key]
    low = key.lower()
    if low in CLASS_TO_CATEGORY:
        return CLASS_TO_CATEGORY[low]
    norm = low.replace("-", "_").replace(" ", "_")
    for src, cat in CLASS_TO_CATEGORY.items():
        if src.lower().replace("-", "_").replace(" ", "_") == norm:
            return cat
    return norm


def _positive_ppe_family(category: str) -> str | None:
    """Familia EPP del perfil (casco, chaleco, …) incl. clases entrenadas en faena."""
    if category in POSITIVE_PPE:
        return category
    low = category.lower().replace("-", "_")
    needles = (
        ("casco", "casco"),
        ("hardhat", "casco"),
        ("helmet", "casco"),
        ("chaleco", "chaleco"),
        ("vest", "chaleco"),
        ("fluor", "chaleco"),
        ("uniforme", "chaleco"),
        ("lente", "lentes"),
        ("goggle", "lentes"),
        ("guante", "guantes"),
        ("glove", "guantes"),
        ("arnes", "arnes"),
        ("harness", "arnes"),
    )
    for needle, family in needles:
        if needle in low:
            return family
    return None


def _violation_missing_key(category: str) -> str | None:
    if category in NEGATIVE_PPE:
        return NEGATIVE_PPE[category]
    low = category.lower().replace("-", "_")
    if "sin_casco" in low or "no_hardhat" in low:
        return "casco"
    if "sin_chaleco" in low or "no_safety_vest" in low or "no_vest" in low:
        return "chaleco"
    if "sin_lente" in low or "no_goggle" in low:
        return "lentes"
    if "sin_guante" in low or "no_glove" in low:
        return "guantes"
    if "sin_arnes" in low or "no_harness" in low:
        return "arnes"
    return None


def normalize_detections(raw: list[dict]) -> list[Detection]:
    out: list[Detection] = []
    for item in raw:
        label = str(item.get("label", ""))
        category = _category_for_label(label)
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

    # Si no hay persona pero hay EPP / violaciones, crear un "trabajador implícito"
    if not persons_boxes and ppe_items:
        # bbox envolvente de todo lo detectado
        xs1 = [d.box[0] for d in ppe_items]
        ys1 = [d.box[1] for d in ppe_items]
        xs2 = [d.box[2] for d in ppe_items]
        ys2 = [d.box[3] for d in ppe_items]
        persons_boxes = [
            Detection(
                label="Person",
                category="persona",
                confidence=0.5,
                box=[min(xs1), min(ys1), max(xs2), max(ys2)],
            )
        ]

    persons: list[PersonCompliance] = []
    alerts: list[str] = []

    for idx, person in enumerate(persons_boxes):
        present: set[str] = set()
        violations: list[str] = []

        for item in ppe_items:
            related = _iou(person.box, item.box) > 0.05 or _center_inside(item.box, person.box)
            if not related:
                continue
            if item.category in POSITIVE_PPE:
                present.add(item.category)
            else:
                family = _positive_ppe_family(item.category)
                if family:
                    present.add(family)
            if item.category in NEGATIVE_PPE:
                missing_key = NEGATIVE_PPE[item.category]
                violations.append(missing_key)
            else:
                miss = _violation_missing_key(item.category)
                if miss:
                    violations.append(miss)
            if item.category == "caida":
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