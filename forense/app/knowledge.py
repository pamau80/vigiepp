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


def _entry_dir(entry_id: str) -> Path:
    return KNOWLEDGE_DIR / entry_id


def _thumb_path(entry_id: str) -> Path:
    return _entry_dir(entry_id) / "thumb.jpg"


def _media_path(entry_id: str, media_type: str) -> Path:
    ext = ".mp4" if media_type == "video" else ".jpg"
    return _entry_dir(entry_id) / f"media{ext}"


def _keyword_overlap(text_a: str, text_b: str) -> float:
    wa = set(re.findall(r"[a-záéíóúñ0-9]+", (text_a or "").lower()))
    wb = set(re.findall(r"[a-záéíóúñ0-9]+", (text_b or "").lower()))
    if not wa or not wb:
        return 0.0
    return len(wa & wb) / len(wa | wb)


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


def _job_text_blob(job: dict[str, Any]) -> str:
    timeline = (job.get("analysis") or {}).get("timeline") or []
    msgs = " ".join((e.get("message") or "") for e in timeline[:30])
    return " ".join(x for x in (job.get("title"), job.get("site"), msgs) if x)


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
    for e in entries:
        st = e.get("situation_type") or "other"
        by_type[st] = by_type.get(st, 0) + 1
        ind = e.get("industry") or "general"
        by_industry[ind] = by_industry.get(ind, 0) + 1
    return {
        "total": len(entries),
        "by_situation_type": by_type,
        "by_industry": by_industry,
        "situation_types": SITUATION_TYPES,
    }


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
        "has_thumb": _thumb_path(entry_id).is_file(),
        "signature": signature,
        "frame_signatures": frame_signatures[:16],
        "text_signature": text_signature,
        "text_backend": text_backend,
        "embedding_backend": embedding_backend,
        "reinforce_count": 0,
        "from_job_id": from_job_id,
        "created_at": datetime.now(UTC).isoformat(),
    }
    with _lock:
        entries = _load_index()
        entries.append(entry)
        _save_index(entries)
    return entry


def delete_knowledge(entry_id: str) -> bool:
    with _lock:
        entries = _load_index()
        new_entries = [e for e in entries if e.get("id") != entry_id]
        if len(new_entries) == len(entries):
            return False
        _save_index(new_entries)
    d = _entry_dir(entry_id)
    if d.exists():
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
    job_types = {e.get("type") for e in timeline if e.get("type")}
    job_labels = {e.get("severity") for e in timeline if e.get("severity")}
    job_text = _job_text_blob(job)
    job_text_sig, _ = embed_text(job_text) if job_text else ([], "none")
    job_visual_sigs = _collect_job_visual_signatures(job)

    scored: list[tuple[float, dict[str, Any]]] = []
    for entry in entries:
        score = 0.0
        reasons: list[str] = []
        entry_text = _entry_text_blob(entry)

        entry_industry = (entry.get("industry") or "general").lower()
        if entry_industry == template_id:
            score += 0.2
            reasons.append("misma industria")

        kw = _keyword_overlap(job_text, entry_text)
        if kw > 0.05:
            score += min(0.45, kw * 0.9)
            reasons.append(f"texto relacionado ({kw:.0%})")

        if job_text_sig and entry.get("text_signature"):
            tsim = _similarity(job_text_sig, entry["text_signature"])
            score += tsim * 0.35
            if tsim > 0.25:
                reasons.append(f"semántica CLIP {tsim:.0%}")

        entry_types = set(entry.get("event_types") or [])
        if entry_types and job_types:
            overlap = len(entry_types & job_types) / max(len(entry_types | job_types), 1)
            score += overlap * 0.25
            if overlap > 0:
                reasons.append(f"eventos ({', '.join(sorted(entry_types & job_types))})")

        entry_labels = set(entry.get("labels") or [])
        if entry_labels and job_labels and (entry_labels & job_labels):
            score += 0.08
            reasons.append("severidad similar")

        entry_sigs = list(entry.get("frame_signatures") or [])
        if entry.get("signature") and entry["signature"] not in entry_sigs:
            entry_sigs.append(entry["signature"])
        if job_visual_sigs and entry_sigs:
            vis = max_visual_similarity(job_visual_sigs, entry_sigs)
            score += vis * 0.45
            if vis > 0.55:
                reasons.append(f"video/imagen similar {vis:.0%}")
            elif vis > 0.38:
                reasons.append(f"posible similitud visual {vis:.0%}")

        if score >= 0.18:
            conjecture = score < 0.42
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
                        "score": round(score, 3),
                        "confidence_pct": int(min(99, max(15, score * 100))),
                        "reasons": reasons,
                        "has_thumb": entry.get("has_thumb"),
                        "conjecture": conjecture,
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
        is_conjecture = m.get("conjecture", score < 0.42)
        if score < 0.18:
            continue

        if is_conjecture:
            prefix = "Conjetura (aprendizaje)"
            ev_type = "knowledge_conjecture"
            severity = "medium"
            conjectures += 1
        else:
            prefix = "Coincidencia entrenada"
            ev_type = "knowledge_match"
            severity = "high" if score < 0.65 else "critical"
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
            if m.get("score", 0) < 0.22:
                continue
            idx = id_map.get(m.get("id"))
            if idx is None:
                continue
            entry = entries[idx]
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
