"""Formatos de video admitidos en Forense (subida, análisis OpenCV y reproducción web)."""

from __future__ import annotations

from pathlib import Path

# Contenedores habituales en NVR / cámaras / exportaciones de faena (LATAM).
SUPPORTED_VIDEO_EXTENSIONS: tuple[str, ...] = (
    ".avi",
    ".mp4",
    ".m4v",
    ".mov",
    ".mkv",
    ".webm",
    ".ts",
    ".mts",
    ".m2ts",
    ".wmv",
    ".asf",
    ".flv",
    ".f4v",
    ".3gp",
    ".3g2",
    ".mpg",
    ".mpeg",
    ".mpe",
    ".dav",  # Dahua NVR
    ".h264",
    ".264",
    ".ogv",
    ".ogg",
)

SUPPORTED_FORMATS_HINT = (
    "AVI, MP4, MOV, MKV, WMV, TS, MPG, FLV, 3GP, DAV, H.264 y otros contenedores de video"
)

# Para <input accept="...">
HTML_ACCEPT_VIDEO = "video/*," + ",".join(f"*{ext}" for ext in SUPPORTED_VIDEO_EXTENSIONS)


def video_extension(filename: str) -> str | None:
    ext = Path(filename or "").suffix.lower()
    if ext in SUPPORTED_VIDEO_EXTENSIONS:
        return ext
    return None


def is_supported_video_filename(filename: str) -> bool:
    return video_extension(filename) is not None


def normalize_video_filename(filename: str, *, fallback: str = "video.mp4") -> str:
    """Devuelve nombre con extensión admitida o lanza ValueError."""
    name = (filename or "").strip() or fallback
    ext = video_extension(name)
    if ext:
        return name
    raise ValueError(f"Formato no soportado. Formatos admitidos: {SUPPORTED_FORMATS_HINT}")


def resolve_source_path(sources_dir: Path, cam: int = 0) -> Path | None:
    """Busca cam{N}.* entre los contenedores admitidos."""
    if not sources_dir.is_dir():
        return None
    for ext in SUPPORTED_VIDEO_EXTENSIONS:
        p = sources_dir / f"cam{cam}{ext}"
        if p.is_file():
            return p
    return None
