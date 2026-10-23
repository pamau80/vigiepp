# 13 — Roadmap mejora continua

## 30 días

| Prioridad | Item | Impacto | Esfuerzo | Justificación |
|-----------|------|---------|----------|---------------|
| P0 | Paquete legal privacidad + contrato faena | Comercial | Medio | AUD-VIG-050 |
| P0 | CI: `docker compose build` + smoke | Confianza deploy | Medio | Gap infra auditoría |
| P1 | `pip-audit` + npm audit en CI | Seguridad | Bajo | Supply chain |
| P1 | Documentar **single-worker** Uvicorn edge | Integridad datos | Bajo | AUD-VIG-020 |

## 60 días

| Item | Impacto | Esfuerzo |
|------|---------|----------|
| Rate limiting `/api/detect` y login global | Anti-abuso | Medio |
| axe-core o Lighthouse CI accesibilidad | UX/compliance | Medio |
| Mejorar visibilidad botón logout (topbar) | UX | Bajo |
| Forense E2E en CI | Regresión producto 2 | Medio |

## 90 días

| Item | Impacto | Esfuerzo |
|------|---------|----------|
| Prueba carga 16 canales RTSP en lab | Rendimiento | Alto |
| gitleaks en CI | Secretos | Bajo |
| Modularizar `index.html` / code-split | Performance móvil | Alto |
| Métricas OTEL export real (no stub) | Observabilidad | Medio |

## KPIs sugeridos

- Tiempo medio `/api/detect` en hardware referencia faena
- % faenas con backup restore probado trimestral
- CVE abiertos en dependencias = 0 >7 días
- Incidentes auth / RTSP SSRF = 0
