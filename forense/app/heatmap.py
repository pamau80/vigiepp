"""Mapa de calor de tránsito de personas."""

from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np

from .tracker import Track


def render_heatmap(
    tracks: list[Track],
    *,
    frame_w: int,
    frame_h: int,
    out_path: Path,
    grid_scale: int = 8,
) -> bool:
    if frame_w < 1 or frame_h < 1:
        return False
    gw = max(32, frame_w // grid_scale)
    gh = max(32, frame_h // grid_scale)
    grid = np.zeros((gh, gw), dtype=np.float32)
    count = 0
    for tr in tracks:
        if tr.kind != "person":
            continue
        for pt in tr.points:
            gx = int(pt.cx / frame_w * (gw - 1))
            gy = int(pt.cy / frame_h * (gh - 1))
            gx = max(0, min(gw - 1, gx))
            gy = max(0, min(gh - 1, gy))
            grid[gy, gx] += 1.0
            count += 1
    if count == 0:
        return False
    grid = cv2.GaussianBlur(grid, (0, 0), sigmaX=2)
    norm = grid / (grid.max() or 1.0)
    colored = cv2.applyColorMap((norm * 255).astype(np.uint8), cv2.COLORMAP_JET)
    resized = cv2.resize(colored, (frame_w, frame_h), interpolation=cv2.INTER_LINEAR)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(out_path), resized)
    return out_path.is_file()
