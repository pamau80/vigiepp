"""Revisión de eventos por el operador — confirmar o descartar falsos positivos."""

from __future__ import annotations

import hashlib
import json
import logging
from datetime import UTC, datetime
from typing import Any

from .config import FORENSE_DATA, ensure_dirs

logger = logging.getLogger("vigiepp.forense.event_feedback")

_SUPPRESSION_FILE = FORENSE_DATA / "suppression_rules.json"
_VERDICT_CONFIRMED = "confirmed"
_VERDICT_DISMISSED = "dismissed"


def fingerprint_event(ev: dict[str, Any], index: int = 0) -> str:
    t = round(float(ev.get("time_sec") or 0), 2)
    etype = str(ev.get("type") or "unknown")
    rule = str(ev.get("rule_id") or "")
    msg = (ev.get("message") or "")[:96]
    raw = f"{etype}|{t}|{rule}|{msg}|{index}"
    return hashlib.sha1(raw.encode()).hexdigest()[:12]


def ensure_event_ids(timeline: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for i, ev in enumerate(timeline or []):
        item = dict(ev)
        if not item.get("event_id"):
            item["event_id"] = fingerprint_event(item, i)
        out.append(item)
    return out


def apply_review_state(
    timeline: list[dict[str, Any]],
    feedback: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    fb = feedback or {}
    out: list[dict[str, Any]] = []
    for ev in timeline or []:
        item = dict(ev)
        entry = fb.get(item.get("event_id") or "")
        if entry:
            item["review_status"] = entry.get("verdict")
            item["review_note"] = entry.get("note")
        else:
            item.pop("review_status", None)
            item.pop("review_note", None)
        out.append(item)
    return out


def active_timeline(timeline: list[dict[str, Any]], feedback: dict[str, Any] | None) -> list[dict[str, Any]]:
    """Eventos que cuentan para informe y alertas (excluye descartados)."""
    reviewed = apply_review_state(timeline, feedback)
    return [e for e in reviewed if e.get("review_status") != _VERDICT_DISMISSED]


def review_summary(timeline: list[dict[str, Any]], feedback: dict[str, Any] | None) -> dict[str, int]:
    reviewed = apply_review_state(timeline, feedback)
    pending = sum(1 for e in reviewed if not e.get("review_status"))
    confirmed = sum(1 for e in reviewed if e.get("review_status") == _VERDICT_CONFIRMED)
    dismissed = sum(1 for e in reviewed if e.get("review_status") == _VERDICT_DISMISSED)
    return {"pending": pending, "confirmed": confirmed, "dismissed": dismissed}


def _load_suppression_rules() -> list[dict[str, Any]]:
    ensure_dirs()
    if not _SUPPRESSION_FILE.is_file():
        return []
    try:
        data = json.loads(_SUPPRESSION_FILE.read_text(encoding="utf-8"))
        return list(data.get("rules") or [])
    except json.JSONDecodeError:
        return []


def _save_suppression_rules(rules: list[dict[str, Any]]) -> None:
    ensure_dirs()
    _SUPPRESSION_FILE.write_text(
        json.dumps({"updated_at": datetime.now(UTC).isoformat(), "rules": rules}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _rule_key(ev: dict[str, Any]) -> tuple[str, str]:
    return (str(ev.get("type") or ""), str(ev.get("rule_id") or ""))


def _rule_key_from_parts(event_type: str, rule_id: str | None) -> tuple[str, str]:
    return (str(event_type or ""), str(rule_id or ""))


def record_dismissal(ev: dict[str, Any], *, job_id: str) -> None:
    """Aprende de un falso positivo para futuros análisis en la faena."""
    rules = _load_suppression_rules()
    key = _rule_key(ev)
    found = None
    for r in rules:
        if (r.get("type"), r.get("rule_id") or "") == key:
            found = r
            break
    if found:
        found["dismissed_count"] = int(found.get("dismissed_count") or 0) + 1
        found["last_job_id"] = job_id
        found["last_message"] = (ev.get("message") or "")[:120]
    else:
        rules.append(
            {
                "type": key[0],
                "rule_id": key[1] or None,
                "dismissed_count": 1,
                "last_job_id": job_id,
                "last_message": (ev.get("message") or "")[:120],
            }
        )
    _save_suppression_rules(rules)


def remove_suppression_for_event(ev: dict[str, Any]) -> None:
    """Reduce o elimina la regla global cuando el operador restaura un evento."""
    rules = _load_suppression_rules()
    key = _rule_key(ev)
    out: list[dict[str, Any]] = []
    changed = False
    for r in rules:
        if (r.get("type"), r.get("rule_id") or "") != key:
            out.append(r)
            continue
        changed = True
        cnt = int(r.get("dismissed_count") or 0) - 1
        if cnt > 0:
            item = dict(r)
            item["dismissed_count"] = cnt
            out.append(item)
    if changed:
        _save_suppression_rules(out)


def delete_suppression_rule(event_type: str, rule_id: str | None = None) -> bool:
    """Elimina una regla de supresión (gobernanza del operador)."""
    key = _rule_key_from_parts(event_type, rule_id)
    rules = _load_suppression_rules()
    kept = [r for r in rules if (r.get("type"), r.get("rule_id") or "") != key]
    if len(kept) == len(rules):
        return False
    _save_suppression_rules(kept)
    return True


def is_suppressed(ev: dict[str, Any], rules: list[dict[str, Any]] | None = None) -> bool:
    rules = rules if rules is not None else _load_suppression_rules()
    etype, rule_id = _rule_key(ev)
    for r in rules:
        if r.get("type") != etype:
            continue
        r_rule = str(r.get("rule_id") or "")
        if r_rule and r_rule != rule_id:
            continue
        if int(r.get("dismissed_count") or 0) >= 1:
            return True
    return False


def filter_suppressed_events(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rules = _load_suppression_rules()
    if not rules:
        return events
    return [e for e in events if not is_suppressed(e, rules)]


def suppression_summary() -> dict[str, Any]:
    rules = _load_suppression_rules()
    return {"count": len(rules), "rules": rules[:100]}
