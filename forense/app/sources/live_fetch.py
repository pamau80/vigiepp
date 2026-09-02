"""Conectores live HTML → registros biblioteca (con fallback curado)."""

from __future__ import annotations

import logging
import re
import urllib.parse
import urllib.request
from html import unescape
from typing import Any

from .schema import normalize_record

logger = logging.getLogger("vigiepp.forense.sources.live_fetch")

_HTTP_TIMEOUT = 25
_USER_AGENT = "VigiEPP-Forense/1.1 (live-knowledge-sync)"
_MAX_BYTES = 1_500_000

LIVE_SOURCE_CONFIG: dict[str, dict[str, Any]] = {
    "sernageomin_chile": {
        "url": "https://www.sernageomin.cl/accidentabilidad-minera/",
        "source": "sernageomin",
        "industry": "mineria",
        "situation_type": "other",
        "tags": ["Chile", "SERNAGEOMIN", "live"],
    },
    "emcip_port": {
        "url": "https://emsa.europa.eu/newsroom/press-releases.html",
        "source": "emcip",
        "industry": "portuario",
        "situation_type": "other",
        "tags": ["EMCIP", "EMSA", "live"],
    },
}


def _strip_html(html: str) -> str:
    text = re.sub(r"(?is)<script[^>]*>.*?</script>", " ", html)
    text = re.sub(r"(?is)<style[^>]*>.*?</style>", " ", text)
    text = re.sub(r"(?is)<[^>]+>", " ", text)
    text = unescape(text)
    return re.sub(r"\s+", " ", text).strip()


def _fetch_html(url: str) -> str | None:
    try:
        req = urllib.request.Request(
            url,
            headers={"User-Agent": _USER_AGENT, "Accept": "text/html,application/xhtml+xml"},
        )
        with urllib.request.urlopen(req, timeout=_HTTP_TIMEOUT) as resp:
            data = resp.read(_MAX_BYTES + 1)
            if len(data) > _MAX_BYTES:
                data = data[:_MAX_BYTES]
            return data.decode("utf-8", errors="replace")
    except Exception as exc:
        logger.warning("Live fetch falló %s: %s", url, exc)
        return None


def _chunks_from_html(html: str, *, min_len: int = 90, max_chunks: int = 20) -> list[tuple[str, str]]:
    """Extrae bloques (título, descripción) desde HTML público."""
    blocks: list[tuple[str, str]] = []
    for m in re.finditer(r"(?is)<(h[2-4]|li|p)[^>]*>(.*?)</\1>", html):
        raw = m.group(2)
        text = _strip_html(raw)
        if len(text) < min_len:
            continue
        title = text.split(".")[0].strip()[:120]
        if len(title) < 12:
            title = text[:120]
        blocks.append((title, text[:600]))
        if len(blocks) >= max_chunks:
            break
    if not blocks:
        plain = _strip_html(html)
        for sent in re.split(r"(?<=[.!?])\s+", plain):
            sent = sent.strip()
            if len(sent) >= min_len:
                blocks.append((sent[:120], sent[:600]))
            if len(blocks) >= max_chunks:
                break
    return blocks


def extract_records_from_html(
    html: str,
    *,
    source: str,
    industry: str,
    situation_type: str = "other",
    tags: list[str] | None = None,
    url: str = "",
    limit: int | None = None,
) -> list[dict[str, Any]]:
    chunks = _chunks_from_html(html)
    if limit and limit > 0:
        chunks = chunks[:limit]
    records: list[dict[str, Any]] = []
    for i, (title, description) in enumerate(chunks):
        rec = normalize_record(
            {
                "title": title,
                "description": description,
                "situation_type": situation_type,
                "industry": industry,
                "tags": tags or [],
                "labels": [source.upper(), "live"],
                "source": source,
                "source_id": f"{source}:live:{i}",
                "meta": {"url": url, "live": True},
            },
            default_industry=industry,
        )
        if rec.get("title") and len(rec.get("description") or "") >= 30:
            records.append(rec)
    return records


def fetch_live_records(source_id: str, *, limit: int | None = None) -> dict[str, Any]:
    """Intenta descargar y parsear fuente live. No lanza excepción."""
    cfg = LIVE_SOURCE_CONFIG.get(source_id)
    if not cfg:
        return {"ok": False, "error": f"Sin configuración live para {source_id}", "records": []}
    url = cfg["url"]
    html = _fetch_html(url)
    if not html:
        return {
            "ok": False,
            "error": "fetch_failed",
            "url": url,
            "records": [],
            "live_fetch": True,
        }
    records = extract_records_from_html(
        html,
        source=cfg["source"],
        industry=cfg["industry"],
        situation_type=cfg.get("situation_type", "other"),
        tags=list(cfg.get("tags") or []),
        url=url,
        limit=limit,
    )
    return {
        "ok": bool(records),
        "url": url,
        "records": records,
        "live_fetch": True,
        "fetched_chunks": len(records),
    }
