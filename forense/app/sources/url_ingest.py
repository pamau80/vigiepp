"""Ingesta de informes desde URL con lista blanca de dominios."""

from __future__ import annotations

import logging
import re
import urllib.parse
import urllib.request
from html import unescape
from typing import Any

from ..knowledge import create_knowledge
from .registry import URL_ALLOWLIST_SUFFIXES
from .schema import normalize_record, validate_record

logger = logging.getLogger("vigiepp.forense.sources.url_ingest")

_HTTP_TIMEOUT = 30
_USER_AGENT = "VigiEPP-Forense/1.0 (knowledge-ingest)"
_MAX_BYTES = 2_500_000


def _host_allowed(url: str) -> bool:
    try:
        host = urllib.parse.urlparse(url).netloc.lower().split(":")[0]
    except Exception:
        return False
    if not host:
        return False
    for suffix in URL_ALLOWLIST_SUFFIXES:
        if host == suffix or host.endswith("." + suffix):
            return True
    return False


def _strip_html(html: str) -> str:
    text = re.sub(r"(?is)<script[^>]*>.*?</script>", " ", html)
    text = re.sub(r"(?is)<style[^>]*>.*?</style>", " ", text)
    text = re.sub(r"(?is)<[^>]+>", " ", text)
    text = unescape(text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _extract_title(html: str) -> str:
    m = re.search(r"(?is)<title[^>]*>(.*?)</title>", html)
    if m:
        return unescape(re.sub(r"\s+", " ", m.group(1)).strip())[:200]
    m = re.search(r"(?is)<h1[^>]*>(.*?)</h1>", html)
    if m:
        return _strip_html(m.group(1))[:200]
    return ""


def _fetch_url(url: str) -> tuple[bytes, str]:
    req = urllib.request.Request(url, headers={"User-Agent": _USER_AGENT, "Accept": "*/*"})
    with urllib.request.urlopen(req, timeout=_HTTP_TIMEOUT) as resp:
        data = resp.read(_MAX_BYTES + 1)
        if len(data) > _MAX_BYTES:
            data = data[:_MAX_BYTES]
        ctype = resp.headers.get("Content-Type", "")
        return data, ctype


def ingest_url(
    url: str,
    *,
    title: str = "",
    industry: str = "general",
    situation_type: str = "other",
    tags: list[str] | None = None,
    save: bool = True,
) -> dict[str, Any]:
    """Descarga URL permitida y crea entrada en biblioteca (o solo previsualiza)."""
    url = (url or "").strip()
    if not url.startswith(("http://", "https://")):
        return {"ok": False, "error": "URL debe comenzar con http:// o https://"}
    if not _host_allowed(url):
        return {
            "ok": False,
            "error": "Dominio no permitido. Usá fuentes oficiales (OSHA, HSE, EMSA, SERNAGEOMIN, etc.).",
            "allowlist": list(URL_ALLOWLIST_SUFFIXES),
        }

    try:
        data, ctype = _fetch_url(url)
    except Exception as exc:
        logger.warning("Fetch URL falló %s: %s", url, exc)
        return {"ok": False, "error": f"No se pudo descargar la URL: {exc}"}

    is_pdf = "pdf" in ctype.lower() or url.lower().endswith(".pdf")
    description = ""
    extracted_title = ""

    if is_pdf:
        try:
            import pypdf

            from io import BytesIO

            reader = pypdf.PdfReader(BytesIO(data))
            pages = []
            for page in reader.pages[:8]:
                pages.append(page.extract_text() or "")
            description = "\n".join(pages).strip()[:4000]
            extracted_title = (reader.metadata.title if reader.metadata else "") or ""
        except Exception as exc:
            return {"ok": False, "error": f"No se pudo leer el PDF: {exc}"}
    else:
        html = data.decode("utf-8", errors="replace")
        extracted_title = _extract_title(html)
        description = _strip_html(html)[:4000]

    final_title = (title or extracted_title or "Informe importado").strip()[:200]
    if not description:
        description = f"Contenido importado desde {urllib.parse.urlparse(url).netloc}"

    host = urllib.parse.urlparse(url).netloc.lower()
    source = "url"
    if "osha" in host or "dol.gov" in host:
        source = "osha"
    elif "emsa" in host:
        source = "emcip"
    elif "sernageomin" in host:
        source = "sernageomin"
    elif "hse.gov" in host:
        source = "hse"
    elif "maib" in host:
        source = "maib"

    rec = normalize_record(
        {
            "title": final_title,
            "description": description,
            "situation_type": situation_type,
            "industry": industry,
            "tags": tags or [],
            "labels": [source, "url_import"],
            "source": source,
            "source_id": f"url:{urllib.parse.quote(url, safe='')[:120]}",
            "meta": {"url": url, "content_type": ctype},
        },
        default_industry=industry,
    )
    issues = validate_record(rec)
    preview = {"record": rec, "issues": issues, "url": url}

    if not save:
        return {"ok": True, "preview": preview, "saved": False}

    if issues and "falta título" in issues:
        return {"ok": False, "error": "Registro inválido", "preview": preview}

    entry = create_knowledge(
        title=rec["title"],
        situation_type=rec["situation_type"],
        description=rec["description"],
        industry=rec["industry"],
        labels=rec["labels"],
        event_types=rec["event_types"],
        source=rec["source"],
        source_id=rec["source_id"],
        tags=rec["tags"],
    )
    return {"ok": True, "preview": preview, "saved": True, "entry": entry}
