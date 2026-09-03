# VigiEPP Forense

Producto **aislado** de análisis forense de video (informes IA de incidentes).

No modifica VigiEPP principal (`frontend/`, `backend/app/main.py`, pestañas, etc.).

## Arranque

```bash
bash forense/start.sh
```

Abre **http://127.0.0.1:8001/** (VigiEPP sigue en `:8000`).

## Licencia (plan Forense)

```env
VIGIEPP_FORENSE=1
VIGIEPP_FORENSE_LICENSE=dev          # desarrollo
# Producción: ver docs/FORENSE_LICENSE_EDGE.md
```

Emitir licencia edge:

```bash
PYTHONPATH=backend:forense python forense/scripts/issue_forense_license.py --site faena-norte --years 1
```

Solo rol **admin** puede usar Forense (mismo PIN que VigiEPP).

## Datos

Almacenados en `forense/data/` (separado de `backend/data/`).

## Funcionalidades (forense-p4)

### P0 — Base
- Muestreo adaptivo de video
- Timeline de eventos (EPP, zonas, Acciones)
- Informe Markdown + auth admin

### P1 — Cinemática
- Tracking IoU persona / maquinaria
- Velocidades estimadas (km/h) con calibración m/px
- Límites configurables (km/h maquinaria, persona, distancia mínima)
- Mapa de calor de tránsito
- Export PDF (`report.pdf`) + Markdown

### P2 — Gráficos y exportación
- Series de velocidad vs tiempo (API `/charts` + canvas en UI)
- Export EHS (`POST /export-ehs`) reutilizando conectores VigiEPP
- Informe comité paritario (`committee.md`)

### P3 — Multi-cámara y comparación
- Hasta 3 videos con offset temporal por cámara
- Fusión de timeline y cinemática multi-fuente
- Comparación incidente vs trabajo de referencia (escenario seguro)

### P4 — Plantillas y bundle
- Plantillas por industria: minería, portuario, bodega, construcción, general
- Bundle de caso (`case_bundle.zip`): job.json, informes, EHS JSON, series

### P12 — Ojo clínico
- Barra de auditoría del instante sincronizada al playhead
- Panel colapsable con detecciones, cinemática y proximidad

### P13 — Análisis visual IA del video
- Modelo de visión sobre fotogramas clave (keyframes, alertas, timeline)
- Sección en informe **2c. Observaciones visuales IA**
- Panel UI + integración en ojo clínico al scrub
- Requiere API OpenAI-compatible (`VIGIEPP_FORENSE_OPENAI_KEY`); edge: Ollama + `llava`

- Emisión de licencias firmadas (`forense/scripts/issue_forense_license.py`) — ver `docs/FORENSE_LICENSE_EDGE.md`
- SERNAGEOMIN y EMCIP: intento de fetch live + fallback a JSON curado (offline-safe)

### P10 — Sesión y UX operador
- Token en `GET /api/forense/auth/status` para hidratar sesión (cookie o puente `?key=` desde VigiEPP)
- Reintento automático ante 401 con token expirado
- Toasts de feedback, badge de sesión y `POST /api/forense/auth/logout`

### P9 — Fuentes mundiales (biblioteca)
- Catálogo de 13 fuentes por industria: semillas, OSHA, SERNAGEOMIN, EMCIP, HSE UK, parking
- Sincronización por fuente o por industria completa
- Importación desde URL oficial (lista blanca: osha.gov, sernageomin.cl, hse.gov.uk, emsa.europa.eu, …)
- Validación masiva de registros antes de incorporar a la biblioteca CLIP

Variables opcionales:

```env
VIGIEPP_FORENSE_DOL_API_KEY=   # OSHA vía API DOL (si no, fetch público limitado)
```

## API principal

| Método | Ruta | Descripción |
|--------|------|-------------|
| GET | `/api/forense/templates` | Plantillas industria |
| POST | `/api/forense/jobs` | Crear análisis (video + opcionales video2/3, template, referencia) |
| GET | `/api/forense/jobs/{id}/charts` | Series velocidad |
| GET | `/api/forense/jobs/{id}/committee.md` | Informe comité |
| GET | `/api/forense/jobs/{id}/case_bundle.zip` | Bundle completo |
| POST | `/api/forense/jobs/{id}/export-ehs` | Push a conectores EHS |
| GET | `/api/forense/knowledge/sources/catalog` | Catálogo de fuentes por industria |
| POST | `/api/forense/knowledge/sources/sync` | Sincronizar una fuente (`source_id`) |
| POST | `/api/forense/knowledge/sources/sync-industry` | Sincronizar todas las fuentes de una industria |
| POST | `/api/forense/knowledge/sources/ingest-url` | Importar informe desde URL oficial |
| POST | `/api/forense/knowledge/bulk-validate` | Validar lote de registros |
| POST | `/api/forense/auth/logout` | Cerrar sesión Forense |

## Tests

```bash
PYTHONPATH=backend:. pytest forense/tests/ -q
```

Los informes son **generación IA asistida**. No constituyen peritaje legal ni dictamen oficial.
