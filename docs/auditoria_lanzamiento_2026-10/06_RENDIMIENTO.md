# 06 — Rendimiento y estabilidad

## Metodología

Mediciones locales contra Uvicorn en `127.0.0.1:8000` (VM auditoría, un worker, inferencia bajo demanda).

## Resultados medidos

| Métrica | Valor | Notas |
|---------|-------|-------|
| `/api/health` latencia (5 req) | **1,6–2,6 ms** | curl time_total |
| `/` HTML index | **~1,6 ms** | 50 182 bytes (`index.html`) |
| CSS + app.js estáticos | 56 KB + 10 KB | Sin compresión medida en middleware |
| Modelo EPP al arranque | Lazy (+10s thread) | `main.py` lifespan |
| Identidad al arranque | Precarga async | `identity_ready: true` en health |

## Agudeza / pipeline IA

Script `run_detection_acuity.sh`:

- Identidad fixtures: confianzas 83–99 % según escala facial.
- Pipeline `/api/detect` + identify: **cumple perfil** en fixture de prueba.

## No medido (honesto)

- Core Web Vitals en navegador real faena
- Usuarios concurrentes / barrido 16 canales
- Memoria bajo YOLO+SFace simultáneo (runbook recomienda 8–16 GB RAM)
- TTFB detrás de reverse proxy TLS

## Recomendaciones SLO orientativas (edge)

| SLO | Objetivo sugerido |
|-----|-------------------|
| Health p95 LAN | < 50 ms |
| POST `/api/detect` foto | < 3 s en CPU 8c (depende hardware) |
| Disponibilidad faena | 99 % mensual (UPS + restart Docker) |

## Hallazgos

| ID | Sev | Descripción |
|----|-----|-------------|
| AUD-VIG-030 | LOW | `index.html` ~50 KB monolítico — impacto parseo móvil | Modularización futura |
| AUD-VIG-031 | INFO | Sin CDN; correcto para edge air-gapped |
