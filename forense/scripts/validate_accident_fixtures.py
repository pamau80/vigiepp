#!/usr/bin/env python3
"""Valida fixtures fotorrealistas de escenarios de accidente."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import cv2

FIXTURES = Path(__file__).resolve().parents[1] / "tests" / "fixtures" / "accident_simulations"
MANIFEST = FIXTURES / "manifest.json"
MIN_BYTES = 50_000


def main() -> int:
    if not MANIFEST.is_file():
        print("ERROR: manifest.json no encontrado", file=sys.stderr)
        return 1
    data = json.loads(MANIFEST.read_text(encoding="utf-8"))
    scenes = data.get("scenes") or []
    errors: list[str] = []
    for scene in scenes:
        path = FIXTURES / scene["file"]
        if not path.is_file():
            errors.append(f"Falta {scene['file']}")
            continue
        if path.stat().st_size < MIN_BYTES:
            errors.append(f"{scene['file']} demasiado pequeño (¿placeholder?)")
        img = cv2.imread(str(path))
        if img is None:
            errors.append(f"{scene['file']} no es imagen válida")
            continue
        h, w = img.shape[:2]
        if w < 640 or h < 360:
            errors.append(f"{scene['file']} resolución baja: {w}x{h}")
    if errors:
        for e in errors:
            print("ERROR:", e, file=sys.stderr)
        return 1
    print(f"OK {len(scenes)} escenarios fotorrealistas en {FIXTURES}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
