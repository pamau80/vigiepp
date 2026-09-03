"""Biblioteca de situaciones etiquetadas — aprendizaje incremental Forense."""

from __future__ import annotations

import json
import logging
import re
import shutil
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import cv2
import numpy as np

from .config import KNOWLEDGE_DIR, ensure_dirs
from .path_safety import safe_entry_id
from .vision_embed import (
    cosine_similarity,
    embed_image_bgr,
    embed_text,
    max_visual_similarity,
    sample_video_signatures,
)

logger = logging.getLogger("vigiepp.forense.knowledge")

SITUATION_TYPES: dict[str, str] = {
    "near_miss": "Casi accidente / near-miss",
    "collision": "Colisión o golpe",
    "epp_violation": "Incumplimiento EPP",
    "zone_intrusion": "Ingreso a zona restringida",
    "speed_excess": "Exceso de velocidad",
    "proximity": "Proximidad persona–maquinaria",
    "fall_risk": "Riesgo de caída / altura",
    "unsafe_act": "Acto inseguro",
    "other": "Otro / general",
}

_INDEX_PATH = KNOWLEDGE_DIR / "index.json"
_lock = __import__("threading").Lock()

_STOPWORDS = {
    "para", "con", "sin", "por", "del", "las", "los", "una", "uno", "que", "como",
    "the", "and", "for", "with", "from", "this", "that", "were", "was", "are",
    "analisis", "análisis", "forense", "faena", "sitio", "caso", "video", "near",
    "miss", "patio", "principal", "general",
}

_DOMAIN_TERMS = {
    "grua", "grúa", "crane", "spreader", "bobina", "contenedor", "montacargas",
    "forklift", "reach", "stacker", "izaje", "estiba", "muelle", "portuario",
    "camion", "camión", "truck", "basura", "residuo", "recolector", "lxhw32",
    "andamio", "scaffold", "arnes", "arnés", "casco", "ppe", "soldadura",
    "mineria", "mina", "pala", "retroexcavadora", "excavadora", "vehiculo",
    "vehículo", "peaton", "peatón", "colision", "colisión", "atropello",
}

_MATCH_STRONG_MIN = 0.58
_MATCH_CONJECTURE_MIN = 0.36


def _load_index() -> list[dict[str, Any]]:
    ensure_dirs()
    if not _INDEX_PATH.is_file():
        return []
    try:
        data = json.loads(_INDEX_PATH.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []
    except json.JSONDecodeError:
        return []


def _save_index(entries: list[dict[str, Any]]) -> None:
    ensure_dirs()
    _INDEX_PATH.write_text(json.dumps(entries, ensure_ascii=False, indent=2), encoding="utf-8")


def _entry_dir(entry_id: str) -> Path | None:
    safe = safe_entry_id(entry_id)
    if not safe:
        return None
    return KNOWLEDGE_DIR / safe


def _thumb_path(entry_id: str) -> Path | None:
    base = _entry_dir(entry_id)
    return base / "thumb.jpg" if base else None


def _media_path(entry_id: str, media_type: str) -> Path | None:
    base = _entry_dir(entry_id)
    if not base:
        return None
    ext = ".mp4" if media_type == "video" else ".jpg"
    return base / f"media{ext}"


def _keyword_overlap(text_a: str, text_b: str) -> float:
    wa = _significant_tokens(text_a)
    wb = _significant_tokens(text_b)
    if not wa or not wb:
        return 0.0
    return len(wa & wb) / len(wa | wb)


def _significant_tokens(text: str) -> set[str]:
    words = set(re.findall(r"[a-záéíóúñ0-9]+", (text or "").lower()))
    return {w for w in words if len(w) > 2 and w not in _STOPWORDS}


def _domain_tokens(text: str) -> set[str]:
    return _significant_tokens(text) & _DOMAIN_TERMS


def _job_text_blob(job: dict[str, Any]) -> str:
    timeline = (job.get("analysis") or {}).get("timeline") or []
    detector_msgs = " ".join(
        (e.get("message") or "")
        for e in timeline[:30]
        if e.get("type") not in ("knowledge_match", "knowledge_conjecture")
    )
    return " ".join(
        x
        for x in (
            job.get("title"),
            job.get("site"),
            job.get("case_notes"),
            detector_msgs,
        )
        if x
    )


def _entry_text_blob(entry: dict[str, Any]) -> str:
    return " ".join(
        x
        for x in (
            entry.get("title"),
            entry.get("description"),
            entry.get("situation_label"),
            entry.get("situation_type"),
        )
        if x
    )


def _classify_match_strength(
    *,
    score: float,
    kw: float,
    tsim: float,
    vis: float,
    job_tokens: set[str],
    entry_tokens: set[str],
    job_domain: set[str],
    entry_domain: set[str],
    entry: dict[str, Any],
) -> tuple[str, list[str]]:
    """Retorna ('match'|'conjecture'|'reject', reasons_adjusted)."""
    reasons: list[str] = []
    source = (entry.get("source") or "user").lower()
    user_trained = source == "user"

    if entry_domain and job_domain and not (entry_domain & job_domain):
        if vis < 0.84 and not (user_trained and vis >= 0.62):
            return "reject", ["contexto distinto (sin términos de situación en común)"]

    if entry_domain and not job_domain and kw < 0.08:
        if not (user_trained and vis >= 0.70):
            return "reject", ["situación de biblioteca no relacionada con el caso descrito"]

    if len(job_tokens) < 4 and not user_trained:
        if vis < 0.78 and kw < 0.10:
            return "reject", ["título del caso muy genérico — describí qué ocurrió"]

    strong = False
    if score >= _MATCH_STRONG_MIN:
        if kw >= 0.14:
            strong = True
            reasons.append("texto del caso alineado")
        elif user_trained and vis >= 0.62 and kw >= 0.05:
            strong = True
            reasons.append("entrenamiento propio + similitud visual")
        elif vis >= 0.72 and (kw >= 0.06 or (entry_domain & job_domain)):
            strong = True
            reasons.append("video muy similar + contexto compatible")
        elif tsim >= 0.84 and kw >= 0.08:
            strong = True
            reasons.append("semántica fuerte + palabras clave")

    if strong:
        return "match", reasons

    if score >= _MATCH_CONJECTURE_MIN and (kw >= 0.08 or (entry_domain & job_domain)) and (kw >= 0.05 or vis >= 0.55 or tsim >= 0.72):
        return "conjecture", ["similitud parcial — validar con el video"]

    return "reject", []


def _resize_and_save_thumb(img: np.ndarray, thumb: Path, max_w: int = 320) -> None:
    h, w = img.shape[:2]
    if w > max_w:
        scale = max_w / w
        img = cv2.resize(img, (max_w, max(1, int(h * scale))))
    cv2.imwrite(str(thumb), img, [int(cv2.IMWRITE_JPEG_QUALITY), 85])


def _ensure_entry_embeddings(entry: dict[str, Any]) -> dict[str, Any]:
    """Completa embeddings faltantes (migración de entradas antiguas)."""
    changed = False
    blob = _entry_text_blob(entry)
    if blob and not entry.get("text_signature"):
        sig, backend = embed_text(blob)
        if sig:
            entry["text_signature"] = sig
            entry["text_backend"] = backend
            changed = True

    entry_dir = _entry_dir(entry["id"])
    frame_sigs: list[list[float]] = list(entry.get("frame_signatures") or [])
    if entry.get("signature") and not frame_sigs:
        frame_sigs = [entry["signature"]]

    if entry.get("media_type") == "video":
        video_path = entry_dir / "media.mp4"
        if video_path.is_file() and len(frame_sigs) < 4:
            frame_sigs = sample_video_signatures(str(video_path), max_frames=10)
            changed = True
            if frame_sigs and not entry.get("signature"):
                entry["signature"] = frame_sigs[0]
                entry["embedding_backend"] = "clip"

    thumb = _thumb_path(entry["id"])
    if thumb.is_file() and thumb.stat().st_size > 400_000:
        img = cv2.imread(str(thumb))
        if img is not None:
            _resize_and_save_thumb(img, thumb)
            changed = True

    if frame_sigs:
        entry["frame_signatures"] = frame_sigs[:16]
        changed = True

    if changed:
        with _lock:
            entries = _load_index()
            for i, e in enumerate(entries):
                if e.get("id") == entry.get("id"):
                    entries[i] = entry
                    break
            _save_index(entries)
    return entry


def _collect_job_visual_signatures(job: dict[str, Any]) -> list[list[float]]:
    from .jobs import keyframe_path

    sigs: list[list[float]] = []
    job_id = job.get("id")
    if not job_id:
        return sigs

    for kf in (job.get("analysis") or {}).get("keyframes") or []:
        name = kf.get("image")
        if not name:
            continue
        kp = keyframe_path(job_id, name)
        if kp and kp.is_file():
            img = cv2.imread(str(kp))
            if img is not None:
                vec, _ = _signature_from_image(img)
                if vec:
                    sigs.append(vec)

    for src in job.get("sources") or []:
        path = src.get("path")
        if path and Path(path).is_file():
            sigs.extend(sample_video_signatures(path, max_frames=8))

    return sigs[:20]


def _signature_from_image(image_bgr: np.ndarray) -> tuple[list[float], str]:
    return embed_image_bgr(image_bgr)


def _similarity(a: list[float], b: list[float]) -> float:
    return cosine_similarity(a, b)


def _extract_video_thumb(video_bytes: bytes, out_path: Path) -> bool:
    tmp = out_path.parent / "_tmp_upload.mp4"
    try:
        tmp.write_bytes(video_bytes)
        cap = cv2.VideoCapture(str(tmp))
        ok, frame = cap.read()
        cap.release()
        if not ok or frame is None:
            return False
        cv2.imwrite(str(out_path), frame, [int(cv2.IMWRITE_JPEG_QUALITY), 82])
        return out_path.is_file()
    except Exception:
        logger.exception("No se pudo extraer thumb de video")
        return False
    finally:
        tmp.unlink(missing_ok=True)


def list_knowledge(*, industry: str | None = None) -> list[dict[str, Any]]:
    with _lock:
        entries = _load_index()
    if industry:
        industry = industry.strip().lower()
        entries = [e for e in entries if not e.get("industry") or e.get("industry") == industry]
    return sorted(entries, key=lambda e: e.get("created_at", ""), reverse=True)


def get_knowledge(entry_id: str) -> dict[str, Any] | None:
    with _lock:
        for e in _load_index():
            if e.get("id") == entry_id:
                return dict(e)
    return None


def knowledge_stats() -> dict[str, Any]:
    entries = list_knowledge()
    by_type: dict[str, int] = {}
    by_industry: dict[str, int] = {}
    by_source: dict[str, int] = {}
    for e in entries:
        st = e.get("situation_type") or "other"
        by_type[st] = by_type.get(st, 0) + 1
        ind = e.get("industry") or "general"
        by_industry[ind] = by_industry.get(ind, 0) + 1
        src = e.get("source") or "user"
        by_source[src] = by_source.get(src, 0) + 1
    return {
        "total": len(entries),
        "by_situation_type": by_type,
        "by_industry": by_industry,
        "by_source": by_source,
        "situation_types": SITUATION_TYPES,
    }


def find_by_source_id(source: str, source_id: str) -> dict[str, Any] | None:
    source = (source or "").strip().lower()
    source_id = (source_id or "").strip()
    if not source or not source_id:
        return None
    for e in list_knowledge():
        if (e.get("source") or "").lower() == source and (e.get("source_id") or "") == source_id:
            return e
    return None


def create_knowledge(
    *,
    title: str,
    situation_type: str,
    description: str = "",
    industry: str = "general",
    labels: list[str] | None = None,
    event_types: list[str] | None = None,
    media_bytes: bytes | None = None,
    media_filename: str | None = None,
    from_job_id: str | None = None,
    source: str = "user",
    source_id: str | None = None,
    tags: list[str] | None = None,
) -> dict[str, Any]:
    ensure_dirs()
    entry_id = f"kn-{uuid.uuid4().hex[:10]}"
    st = situation_type if situation_type in SITUATION_TYPES else "other"
    media_type = "none"
    signature: list[float] = []
    frame_signatures: list[list[float]] = []
    embedding_backend = "none"
    text_signature: list[float] = []
    text_backend = "none"

    entry_dir = _entry_dir(entry_id)
    entry_dir.mkdir(parents=True, exist_ok=True)

    if media_bytes and len(media_bytes) > 100:
        fname = (media_filename or "").lower()
        if fname.endswith((".mp4", ".mov", ".avi", ".webm")):
            media_type = "video"
            media_path = _media_path(entry_id, "video")
            media_path.write_bytes(media_bytes)
            thumb = _thumb_path(entry_id)
            if _extract_video_thumb(media_bytes, thumb):
                img = cv2.imread(str(thumb))
                if img is not None:
                    _resize_and_save_thumb(img, thumb)
                    img = cv2.imread(str(thumb))
                    if img is not None:
                        signature, embedding_backend = _signature_from_image(img)
            frame_signatures = sample_video_signatures(str(media_path), max_frames=10)
            if frame_signatures and not signature:
                signature = frame_signatures[0]
        else:
            media_type = "image"
            media_path = _media_path(entry_id, "image")
            media_path.write_bytes(media_bytes)
            thumb = _thumb_path(entry_id)
            arr = np.frombuffer(media_bytes, dtype=np.uint8)
            img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
            if img is not None:
                _resize_and_save_thumb(img, thumb)
                signature, embedding_backend = _signature_from_image(img)
                frame_signatures = [signature] if signature else []

    text_blob = f"{title.strip() or SITUATION_TYPES.get(st, st)}. {description.strip()}. {SITUATION_TYPES.get(st, st)}"
    text_signature, text_backend = embed_text(text_blob)

    entry = {
        "id": entry_id,
        "title": title.strip() or SITUATION_TYPES.get(st, st),
        "situation_type": st,
        "situation_label": SITUATION_TYPES.get(st, st),
        "description": description.strip(),
        "industry": (industry or "general").strip().lower(),
        "labels": [x.strip() for x in (labels or []) if x.strip()],
        "event_types": [x.strip() for x in (event_types or []) if x.strip()],
        "media_type": media_type,
        "has_thumb": bool(_thumb_path(entry_id) and _thumb_path(entry_id).is_file()),
        "signature": signature,
        "frame_signatures": frame_signatures[:16],
        "text_signature": text_signature,
        "text_backend": text_backend,
        "embedding_backend": embedding_backend,
        "reinforce_count": 0,
        "from_job_id": from_job_id,
        "source": (source or "user").strip().lower(),
        "source_id": (source_id or "").strip() or None,
        "tags": [x.strip() for x in (tags or []) if x.strip()],
        "created_at": datetime.now(UTC).isoformat(),
    }
    with _lock:
        entries = _load_index()
        entries.append(entry)
        _save_index(entries)
    return entry


def bulk_import_knowledge(
    records: list[dict[str, Any]],
    *,
    skip_existing: bool = True,
) -> dict[str, Any]:
    """Importa entradas textuales; omite duplicados por source+source_id."""
    imported: list[dict[str, Any]] = []
    skipped = 0
    errors: list[str] = []

    for i, rec in enumerate(records):
        src = (rec.get("source") or "import").strip().lower()
        sid = (rec.get("source_id") or "").strip()
        if skip_existing and sid and find_by_source_id(src, sid):
            skipped += 1
            continue
        title = (rec.get("title") or "").strip()
        if not title:
            errors.append(f"registro {i}: sin título")
            continue
        try:
            entry = create_knowledge(
                title=title[:200],
                situation_type=rec.get("situation_type") or "other",
                description=(rec.get("description") or "")[:4000],
                industry=rec.get("industry") or "general",
                labels=rec.get("labels"),
                event_types=rec.get("event_types"),
                source=src,
                source_id=sid or None,
                tags=rec.get("tags"),
            )
            imported.append(entry)
        except Exception as exc:
            errors.append(f"registro {i}: {exc}")

    return {
        "imported": len(imported),
        "skipped": skipped,
        "errors": errors[:20],
        "entries": [{"id": e["id"], "title": e["title"], "source": e.get("source")} for e in imported[:50]],
    }


def delete_knowledge(entry_id: str) -> bool:
    if not safe_entry_id(entry_id):
        return False
    with _lock:
        entries = _load_index()
        new_entries = [e for e in entries if e.get("id") != entry_id]
        if len(new_entries) == len(entries):
            return False
        _save_index(new_entries)
    d = _entry_dir(entry_id)
    if d and d.exists():
        shutil.rmtree(d, ignore_errors=True)
    return True


def reset_knowledge() -> int:
    """Elimina toda la biblioteca de aprendizaje. Retorna cantidad eliminada."""
    with _lock:
        count = len(_load_index())
        _save_index([])
    if KNOWLEDGE_DIR.exists():
        for child in KNOWLEDGE_DIR.iterdir():
            if child.name == "index.json":
                continue
            if child.is_dir():
                shutil.rmtree(child, ignore_errors=True)
            else:
                child.unlink(missing_ok=True)
    return count


def promote_job_keyframe(
    job: dict[str, Any],
    *,
    keyframe_name: str,
    title: str,
    situation_type: str,
    description: str = "",
) -> dict[str, Any] | None:
    from .jobs import keyframe_path

    job_id = job.get("id")
    if not job_id:
        return None
    path = keyframe_path(job_id, keyframe_name)
    if not path or not path.is_file():
        return None
    media_bytes = path.read_bytes()
    timeline = (job.get("analysis") or {}).get("timeline") or []
    event_types = sorted({e.get("type") for e in timeline if e.get("type")})
    labels = sorted({e.get("severity") for e in timeline if e.get("severity")})
    return create_knowledge(
        title=title,
        situation_type=situation_type,
        description=description,
        industry=job.get("template_id") or "general",
        labels=[str(x) for x in labels if x],
        event_types=[str(x) for x in event_types if x],
        media_bytes=media_bytes,
        media_filename=keyframe_name,
        from_job_id=job_id,
    )


def match_knowledge_for_job(job: dict[str, Any], *, limit: int = 5) -> list[dict[str, Any]]:
    """Encuentra situaciones similares en la biblioteca para enriquecer el análisis."""
    raw_entries = list_knowledge()
    if not raw_entries:
        return []

    entries = [_ensure_entry_embeddings(dict(e)) for e in raw_entries]
    template_id = (job.get("template_id") or "general").lower()
    timeline = (job.get("analysis") or {}).get("timeline") or []
    job_types = {e.get("type") for e in timeline if e.get("type") and e.get("type") not in ("knowledge_match", "knowledge_conjecture")}
    job_labels = {e.get("severity") for e in timeline if e.get("severity")}
    job_text = _job_text_blob(job)
    job_tokens = _significant_tokens(job_text)
    job_domain = _domain_tokens(job_text)
    job_text_sig, _ = embed_text(job_text) if job_text else ([], "none")
    job_visual_sigs = _collect_job_visual_signatures(job)

    scored: list[tuple[float, dict[str, Any]]] = []
    for entry in entries:
        score = 0.0
        reasons: list[str] = []
        entry_text = _entry_text_blob(entry)
        entry_tokens = _significant_tokens(entry_text)
        entry_domain = _domain_tokens(entry_text)

        entry_industry = (entry.get("industry") or "general").lower()
        if entry_industry == template_id:
            score += 0.06
            reasons.append("misma industria")

        kw = _keyword_overlap(job_text, entry_text)
        if kw > 0.05:
            score += min(0.42, kw * 1.1)
            reasons.append(f"texto relacionado ({kw:.0%})")

        tsim = 0.0
        if job_text_sig and entry.get("text_signature"):
            tsim = _similarity(job_text_sig, entry["text_signature"])
            clip_w = 0.18 if len(job_tokens) < 5 else 0.28
            score += tsim * clip_w
            if tsim > 0.30:
                reasons.append(f"semántica CLIP {tsim:.0%}")

        entry_types = set(entry.get("event_types") or [])
        if entry_types and job_types:
            overlap = len(entry_types & job_types) / max(len(entry_types | job_types), 1)
            score += overlap * 0.15
            if overlap > 0:
                reasons.append(f"eventos ({', '.join(sorted(entry_types & job_types))})")

        entry_labels = set(entry.get("labels") or [])
        if entry_labels and job_labels and (entry_labels & job_labels):
            score += 0.05

        vis = 0.0
        entry_sigs: list[list[float]] = []
        if entry.get("media_type") in ("video", "image"):
            entry_sigs = list(entry.get("frame_signatures") or [])
            if entry.get("signature") and entry["signature"] not in entry_sigs:
                entry_sigs.append(entry["signature"])
        if job_visual_sigs and entry_sigs:
            vis = max_visual_similarity(job_visual_sigs, entry_sigs)
            score += vis * 0.38
            if vis > 0.62:
                reasons.append(f"video/imagen similar {vis:.0%}")
            elif vis > 0.48:
                reasons.append(f"posible similitud visual {vis:.0%}")

        if entry_domain and job_domain and not (entry_domain & job_domain) and vis < 0.80:
            score -= 0.28

        strength, extra_reasons = _classify_match_strength(
            score=score,
            kw=kw,
            tsim=tsim,
            vis=vis,
            job_tokens=job_tokens,
            entry_tokens=entry_tokens,
            job_domain=job_domain,
            entry_domain=entry_domain,
            entry=entry,
        )
        if strength == "reject":
            continue

        conjecture = strength == "conjecture"
        all_reasons = reasons + extra_reasons
        scored.append(
            (
                score,
                {
                    "id": entry["id"],
                    "title": entry.get("title"),
                    "situation_type": entry.get("situation_type"),
                    "situation_label": entry.get("situation_label"),
                    "description": entry.get("description"),
                    "industry": entry.get("industry"),
                    "score": round(max(0.0, score), 3),
                    "confidence_pct": int(min(99, max(12, score * 100))),
                    "reasons": all_reasons,
                    "has_thumb": entry.get("has_thumb"),
                    "conjecture": conjecture,
                    "match_strength": strength,
                    "reinforce_count": entry.get("reinforce_count", 0),
                },
            )
        )

    scored.sort(key=lambda x: x[0], reverse=True)
    return [item for _, item in scored[:limit]]


def apply_knowledge_insights(job: dict[str, Any], matches: list[dict[str, Any]]) -> dict[str, Any]:
    """Añade coincidencias y conjeturas de la biblioteca al análisis."""
    if not matches:
        return {"matches": [], "boosted_events": 0, "conjectures": 0}

    analysis = job.setdefault("analysis", {})
    timeline = list(analysis.get("timeline") or [])
    boosted = 0
    conjectures = 0

    for m in matches[:5]:
        score = m.get("score", 0)
        is_conjecture = m.get("conjecture", m.get("match_strength") == "conjecture")
        if m.get("match_strength") == "reject" or score < _MATCH_CONJECTURE_MIN:
            continue

        if is_conjecture:
            prefix = "Conjetura (revisar manualmente)"
            ev_type = "knowledge_conjecture"
            severity = "medium"
            conjectures += 1
        else:
            prefix = "Coincidencia entrenada"
            ev_type = "knowledge_match"
            severity = "high" if score < 0.72 else "critical"
            boosted += 1

        timeline.append(
            {
                "time_sec": 0,
                "time_label": "—",
                "type": ev_type,
                "severity": severity,
                "message": (
                    f"{prefix}: «{m.get('title')}» ({m.get('situation_label')}) — "
                    f"{m.get('description') or 'situación en biblioteca'} "
                    f"[{m.get('confidence_pct', 0)}% · {', '.join(m.get('reasons') or [])}]"
                ),
                "knowledge_id": m.get("id"),
                "confidence_pct": m.get("confidence_pct"),
            }
        )

    timeline.sort(key=lambda e: e.get("time_sec", 0))
    analysis["timeline"] = timeline
    analysis["event_count"] = len(timeline)
    return {"matches": matches, "boosted_events": boosted, "conjectures": conjectures}


def reinforce_knowledge_from_job(job: dict[str, Any], matches: list[dict[str, Any]]) -> int:
    """Aprendizaje continuo: refuerza entradas coincidentes con frames del análisis."""
    if not matches:
        return 0
    job_sigs = _collect_job_visual_signatures(job)
    if not job_sigs:
        return 0

    reinforced = 0
    with _lock:
        entries = _load_index()
        id_map = {e["id"]: i for i, e in enumerate(entries)}

        for m in matches:
            if m.get("score", 0) < 0.45 or m.get("match_strength") != "match":
                continue
            idx = id_map.get(m.get("id"))
            if idx is None:
                continue
            entry = entries[idx]
            if entry.get("media_type") not in ("video", "image") and (entry.get("source") or "user") != "user":
                continue
            frames = list(entry.get("frame_signatures") or [])
            if entry.get("signature"):
                frames.append(entry["signature"])
            for sig in job_sigs[:3]:
                if all(cosine_similarity(sig, existing) < 0.92 for existing in frames):
                    frames.append(sig)
            entry["frame_signatures"] = frames[-16:]
            entry["reinforce_count"] = int(entry.get("reinforce_count") or 0) + 1
            entry["last_reinforced_at"] = datetime.now(UTC).isoformat()
            entry["last_job_id"] = job.get("id")
            entries[idx] = entry
            reinforced += 1

        if reinforced:
            _save_index(entries)
    return reinforced
