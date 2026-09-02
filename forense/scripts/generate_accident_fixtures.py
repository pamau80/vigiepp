#!/usr/bin/env python3
"""Genera imágenes sintéticas de escenarios de accidente para pruebas Forense."""

from __future__ import annotations

import json
from pathlib import Path

import cv2
import numpy as np

OUT_DIR = Path(__file__).resolve().parents[1] / "tests" / "fixtures" / "accident_simulations"
W, H = 960, 540


def _base_scene(title: str, subtitle: str) -> np.ndarray:
    img = np.full((H, W, 3), (42, 48, 58), dtype=np.uint8)
    for y in range(H // 2, H):
        shade = 55 + int((y - H // 2) * 0.12)
        img[y, :] = (shade, shade + 4, shade + 8)
    cv2.line(img, (0, H // 2), (W, H // 2), (90, 95, 105), 2)
    cv2.putText(img, title, (24, 42), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (240, 245, 255), 2, cv2.LINE_AA)
    cv2.putText(img, subtitle, (24, 72), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (170, 180, 195), 1, cv2.LINE_AA)
    cv2.putText(img, "SIMULACION FORENSE — NO ES VIDEO REAL", (24, H - 18), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (120, 130, 145), 1, cv2.LINE_AA)
    return img


def _person(img: np.ndarray, cx: int, cy: int, scale: float = 1.0, color=(80, 200, 120)) -> None:
    s = int(40 * scale)
    cv2.circle(img, (cx, cy - s), int(14 * scale), color, -1)
    cv2.line(img, (cx, cy - s + 14), (cx, cy + s // 2), color, int(5 * scale))
    cv2.line(img, (cx, cy), (cx - s // 2, cy + s), color, int(4 * scale))
    cv2.line(img, (cx, cy), (cx + s // 2, cy + s), color, int(4 * scale))
    cv2.line(img, (cx, cy - 10), (cx - s // 2, cy + 5), color, int(3 * scale))
    cv2.line(img, (cx, cy - 10), (cx + s // 2, cy + 5), color, int(3 * scale))


def _truck(img: np.ndarray, x: int, y: int, w: int = 220, h: int = 90, color=(60, 140, 230)) -> None:
    cv2.rectangle(img, (x, y), (x + w, y + h), color, -1)
    cv2.rectangle(img, (x + w - 70, y - 35), (x + w, y + h), (50, 120, 210), -1)
    cv2.circle(img, (x + 45, y + h), 22, (30, 30, 35), -1)
    cv2.circle(img, (x + w - 40, y + h), 22, (30, 30, 35), -1)


def _forklift(img: np.ndarray, x: int, y: int) -> None:
    cv2.rectangle(img, (x, y), (x + 120, y + 70), (230, 170, 60), -1)
    cv2.rectangle(img, (x + 120, y + 10), (x + 200, y + 55), (200, 140, 40), -1)
    cv2.line(img, (x + 200, y + 30), (x + 260, y - 40), (180, 180, 190), 8)
    cv2.rectangle(img, (x + 250, y - 70), (x + 310, y - 20), (150, 150, 160), -1)
    cv2.circle(img, (x + 35, y + 70), 18, (25, 25, 30), -1)
    cv2.circle(img, (x + 95, y + 70), 18, (25, 25, 30), -1)


def _crane(img: np.ndarray) -> None:
    cv2.rectangle(img, (700, 180), (740, 420), (200, 200, 210), -1)
    cv2.line(img, (720, 180), (520, 120), (220, 220, 230), 10)
    cv2.line(img, (520, 120), (480, 200), (180, 180, 190), 4)
    cv2.rectangle(img, (455, 195), (505, 245), (240, 80, 70), -1)


def _danger_zone(img: np.ndarray, pts: list[tuple[int, int]]) -> None:
    overlay = img.copy()
    arr = np.array(pts, dtype=np.int32)
    cv2.fillPoly(overlay, [arr], (0, 0, 180))
    cv2.addWeighted(overlay, 0.35, img, 0.65, 0, img)
    cv2.polylines(img, [arr], True, (80, 80, 255), 2)


def scene_atropello() -> np.ndarray:
    img = _base_scene("ATROPELLO — Peaton en trayectoria de camion", "Velocidad estimada camion: 18 km/h · Distancia: 0.8 m")
    _truck(img, 120, 330, w=280, h=100)
    _person(img, 360, 360, scale=1.1, color=(80, 220, 120))
    _danger_zone(img, [(300, 300), (520, 300), (500, 450), (280, 450)])
    cv2.arrowedLine(img, (400, 380), (250, 380), (0, 0, 255), 3, tipLength=0.2)
    cv2.putText(img, "IMPACTO INMINENTE", (310, 290), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (100, 100, 255), 2)
    return img


def scene_caida_altura() -> np.ndarray:
    img = _base_scene("CAIDA DESDE ALTURA — Sin arnes en borde de losa", "Altura estimada: 4.2 m · Sin linea de vida")
    cv2.rectangle(img, (80, 160), (420, 200), (120, 125, 135), -1)
    cv2.rectangle(img, (100, 200), (400, 220), (90, 95, 105), -1)
    _person(img, 390, 195, scale=0.9, color=(80, 200, 120))
    fallen = _base_scene("", "")
    _person(fallen, 500, 430, scale=1.0, color=(80, 200, 120))
    cv2.ellipse(fallen, (500, 455), (55, 18), 0, 0, 360, (60, 60, 70), -1)
    img[220:540, 430:960] = fallen[220:540, 430:960]
    cv2.arrowedLine(img, (400, 220), (500, 380), (0, 180, 255), 3, tipLength=0.15)
    cv2.putText(img, "TRAYECTORIA DE CAIDA", (430, 250), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 200, 255), 2)
    return img


def scene_caida_mismo_nivel() -> np.ndarray:
    img = _base_scene("CAIDA MISMO NIVEL — Resbalon en piso mojado", "Superficie contaminada · Sin señalizacion")
    cv2.ellipse(img, (480, 400), (120, 35), 0, 0, 360, (70, 110, 180), -1)
    _person(img, 500, 390, scale=1.0, color=(80, 200, 120))
    cv2.putText(img, "!", (540, 350), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 0, 255), 3)
    cv2.putText(img, "PISO MOJADO", (420, 460), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (100, 180, 255), 2)
    return img


def scene_maniobra_temeraria() -> np.ndarray:
    img = _base_scene("MANIOBRA TEMERARIA — Retroceso sin spotter", "Montacargas a 12 km/h · Peaton en punto ciego")
    _forklift(img, 180, 340)
    _person(img, 330, 370, scale=0.95, color=(80, 220, 120))
    cv2.arrowedLine(img, (220, 400), (320, 400), (0, 0, 255), 4, tipLength=0.25)
    _danger_zone(img, [(280, 320), (420, 320), (400, 450), (260, 450)])
    cv2.putText(img, "PUNTO CIEGO", (285, 315), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (100, 100, 255), 2)
    return img


def scene_proximidad_grua() -> np.ndarray:
    img = _base_scene("PROXIMIDAD CRITICA — Carga suspendida sobre personal", "Distancia vertical < 2 m · Sin zona de exclusion")
    _crane(img)
    _person(img, 470, 400, scale=0.9)
    _person(img, 520, 410, scale=0.85)
    _danger_zone(img, [(430, 250), (560, 250), (580, 460), (410, 460)])
    cv2.putText(img, "LINEA DE FUEGO", (440, 245), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (100, 100, 255), 2)
    return img


def scene_colision_vehiculos() -> np.ndarray:
    img = _base_scene("COLISION — Interseccion de patio sin prioridad", "Dos equipos convergen · Sin señalero")
    _truck(img, 140, 320, w=200, h=80, color=(60, 140, 230))
    _forklift(img, 360, 300)
    _danger_zone(img, [(300, 280), (420, 280), (440, 420), (280, 420)])
    cv2.putText(img, "X", (350, 360), cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0, 0, 255), 3)
    return img


def scene_atrapamiento() -> np.ndarray:
    img = _base_scene("ATRAPAMIENTO — Persona entre vehiculo y mamparo", "Ro-Ro / patio cerrado · Sin guia visible")
    cv2.rectangle(img, (620, 200), (900, 450), (100, 105, 115), -1)
    _truck(img, 500, 330, w=180, h=75, color=(55, 120, 200))
    _person(img, 610, 380, scale=0.9, color=(80, 220, 120))
    _danger_zone(img, [(580, 300), (650, 300), (650, 450), (560, 450)])
    cv2.putText(img, "ATRAPADO", (575, 295), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (100, 100, 255), 2)
    return img


SCENES: list[dict] = [
    {
        "id": "sim_atropello",
        "file": "01_atropello_camion_peaton.png",
        "title": "Atropello — camión vs peatón",
        "situation_type": "collision",
        "industry": "general",
        "description": "Camión en movimiento con peatón en trayectoria de impacto. Simulación para prueba de proximidad y velocidad.",
        "tags": ["atropello", "camion", "peaton", "colision"],
        "generator": scene_atropello,
    },
    {
        "id": "sim_caida_altura",
        "file": "02_caida_desde_altura.png",
        "title": "Caída desde altura sin arnés",
        "situation_type": "fall_risk",
        "industry": "construccion",
        "description": "Trabajador en borde de losa sin línea de vida. Trayectoria de caída simulada.",
        "tags": ["caida", "altura", "arnes", "construccion"],
        "generator": scene_caida_altura,
    },
    {
        "id": "sim_caida_nivel",
        "file": "03_caida_mismo_nivel.png",
        "title": "Caída mismo nivel — resbalón",
        "situation_type": "fall_risk",
        "industry": "general",
        "description": "Resbalón en superficie mojada sin señalización.",
        "tags": ["caida", "resbalon", "piso mojado"],
        "generator": scene_caida_mismo_nivel,
    },
    {
        "id": "sim_maniobra_temeraria",
        "file": "04_maniobra_temeraria_montacargas.png",
        "title": "Maniobra temeraria — retroceso montacargas",
        "situation_type": "unsafe_act",
        "industry": "bodega",
        "description": "Montacargas retrocede en punto ciego hacia peatón sin spotter.",
        "tags": ["montacargas", "retroceso", "punto ciego", "maniobra temeraria"],
        "generator": scene_maniobra_temeraria,
    },
    {
        "id": "sim_proximidad_grua",
        "file": "05_proximidad_carga_suspendida.png",
        "title": "Proximidad crítica bajo carga suspendida",
        "situation_type": "proximity",
        "industry": "portuario",
        "description": "Personal bajo carga de grúa sin zona de exclusión delimitada.",
        "tags": ["grua", "carga suspendida", "linea de fuego", "portuario"],
        "generator": scene_proximidad_grua,
    },
    {
        "id": "sim_colision",
        "file": "06_colision_interseccion_patio.png",
        "title": "Colisión en intersección de patio",
        "situation_type": "collision",
        "industry": "general",
        "description": "Dos equipos convergen en cruce sin señalero ni prioridad definida.",
        "tags": ["colision", "interseccion", "patio", "vehiculos"],
        "generator": scene_colision_vehiculos,
    },
    {
        "id": "sim_atrapamiento",
        "file": "07_atrapamiento_vehiculo_mamparo.png",
        "title": "Atrapamiento vehículo–estructura",
        "situation_type": "collision",
        "industry": "portuario",
        "description": "Persona atrapada entre vehículo y mamparo en patio cerrado.",
        "tags": ["atrapamiento", "ro-ro", "vehiculo", "estructura"],
        "generator": scene_atrapamiento,
    },
]


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    manifest: list[dict] = []
    for scene in SCENES:
        img = scene["generator"]()
        path = OUT_DIR / scene["file"]
        cv2.imwrite(str(path), img)
        entry = {k: v for k, v in scene.items() if k != "generator"}
        entry["path"] = str(path.relative_to(OUT_DIR.parents[1]))
        entry["width"] = W
        entry["height"] = H
        manifest.append(entry)
        print(f"OK {path.name}")
    manifest_path = OUT_DIR / "manifest.json"
    manifest_path.write_text(json.dumps({"version": 1, "scenes": manifest}, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Manifest: {manifest_path}")


if __name__ == "__main__":
    main()
