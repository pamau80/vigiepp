"""Transcodificación a MP4 H.264 para reproducción en navegador."""

from __future__ import annotations

import logging
import shutil
import subprocess
from pathlib import Path

from .video_formats import SUPPORTED_VIDEO_EXTENSIONS

logger = logging.getLogger("vigiepp.forense.video_transcode")

_BROWSER_SAFE_CODECS = {"h264", "avc1", "avc3"}


def _ffprobe_codec(path: Path) -> str | None:
    if not shutil.which("ffprobe"):
        return None
    try:
        out = subprocess.run(
            [
                "ffprobe",
                "-v",
                "error",
                "-select_streams",
                "v:0",
                "-show_entries",
                "stream=codec_name",
                "-of",
                "default=noprint_wrappers=1:nokey=1",
                str(path),
            ],
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )
        codec = (out.stdout or "").strip().lower()
        return codec or None
    except (OSError, subprocess.TimeoutExpired):
        return None


def needs_browser_transcode(path: Path) -> bool:
    if not path.is_file():
        return True
    ext = path.suffix.lower()
    if ext not in SUPPORTED_VIDEO_EXTENSIONS:
        return True
    codec = _ffprobe_codec(path)
    if not codec:
        return ext != ".mp4"
    return codec not in _BROWSER_SAFE_CODECS


def transcode_for_browser(source: Path, dest: Path) -> bool:
    """Genera MP4 H.264 + faststart para <video> HTML5."""
    if not shutil.which("ffmpeg"):
        logger.warning("ffmpeg no disponible — reproducción web puede fallar para %s", source.name)
        return False
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(".part.mp4")
    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        str(source),
        "-map",
        "0:v:0?",
        "-c:v",
        "libx264",
        "-preset",
        "veryfast",
        "-crf",
        "23",
        "-pix_fmt",
        "yuv420p",
        "-movflags",
        "+faststart",
        "-an",
        str(tmp),
    ]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=900, check=False)
        if proc.returncode != 0:
            logger.warning("ffmpeg falló (%s): %s", proc.returncode, (proc.stderr or "")[-400:])
            if tmp.is_file():
                tmp.unlink(missing_ok=True)
            return False
        if not tmp.is_file() or tmp.stat().st_size < 1000:
            tmp.unlink(missing_ok=True)
            return False
        tmp.replace(dest)
        return True
    except (OSError, subprocess.TimeoutExpired) as exc:
        logger.warning("Transcodificación interrumpida: %s", exc)
        tmp.unlink(missing_ok=True)
        return False


def web_playback_path(sources_dir: Path, cam: int = 0) -> Path | None:
    """Ruta MP4 lista para navegador; transcodifica bajo demanda si hace falta."""
    web = sources_dir / f"cam{cam}_web.mp4"
    if web.is_file() and web.stat().st_size > 1000:
        return web
    for ext in SUPPORTED_VIDEO_EXTENSIONS:
        src = sources_dir / f"cam{cam}{ext}"
        if not src.is_file():
            continue
        if not needs_browser_transcode(src):
            if ext == ".mp4":
                return src
            if transcode_for_browser(src, web):
                return web
            return None
        if transcode_for_browser(src, web):
            return web
        return src if ext == ".mp4" else None
    return None
