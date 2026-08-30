# Auditoría Enterprise VigiEPP — v63

**Fecha:** 2026-08-30  
**Build auditado:** `v62`  
**Rama:** `cursor/merge-v62-chain-8b97` · PR #13  
**Alcance:** edge/on-prem por faena (no SaaS multitenancy)

---

## Resumen ejecutivo

VigiEPP v62 consolida la cadena **v59→v62**: UI EPP profesional, wizard día cero, pestaña **Acciones** (conductas inseguras) y editor P1 con reglas por cámara y proximidad en metros. La plataforma mantiene postura **enterprise operativa en edge** con 14 controles P0/P1 automatizados, 107 tests pytest, ESLint en CI y 6 flujos E2E browser.

| Área | Estado | Nota v63 |
|------|--------|----------|
| Seguridad P0/P1 | ✅ Cerrado | 14/14 `test_security_audit.py` |
| Acciones inseguras | ✅ P1 | Proximidad, zonas, montacargas, celular, carga suspendida |
| Identidad + EPP unificado | ✅ Fuerte | Portería en un solo pipeline |
| Modularización frontend | ✅ Avanzada | 34 módulos ES · `app.js` 361 líneas (−92% vs v41) |
| CI (Ruff, Bandit, ESLint) | ✅ Verde | 107 pytest OK |
| E2E browser Playwright | ✅ 6 flujos | Login, Personas, enrolar, identificar, operador |
| Scripts review E2E | ⚠️ Desactualizados | Aún pinnean build `v58` |
| RBAC | ⚠️ Limitado | 2 roles (`admin` / `operator`) |
| Alta disponibilidad | ❌ No | Proceso único, lock de inferencia |
| Catálogo detecciones | ⚠️ vs enterprise | ~10 presets Acciones + teach; no 50–200 módulos |

**Veredicto:** apto para **despliegue productivo en faena edge** con EPP, identidad, NVR y Acciones. No compite como SaaS multi-cliente ni como plataforma EHS global de Fortune 500 sin inversión adicional.

---

## 1. Evolución desde v49/v53

| Indicador | v49 (2026-08-27) | v53 | **v62 (actual)** |
|-----------|------------------|-----|------------------|
| `app.js` líneas | 585 | 320 | **361** |
| Módulos ES | 29 | 31 | **34** (+`actions`, `day-zero-wizard`, `theme`) |
| Tests pytest | 68 | 70 | **107** |
| E2E browser | — | 4 | **6** |
| Acciones inseguras | — | — | **✅ motor + editor P1** |
| Wizard día cero | — | — | **✅** |
| Skins / temas | — | — | **✅** 5 skins |
| ESLint CI | pendiente | pendiente | **✅** |
| Ruff CI | fallaba | verde | **✅** |

---

## 2. Inventario funcional

### 2.1 Núcleo IA

| Capacidad | Implementación | APIs |
|-----------|----------------|------|
| Detección EPP (YOLO) | `detector.py`, `compliance.py` | `POST /api/detect`, `WS /ws/detect` |
| Inferencia combinada EPP+identidad | `inference.py`, `detect_pipeline.py` | Auto en edge (`VIGIEPP_COMBINED_INFERENCE=auto`) |
| Perfiles de faena | `profiles.py` | `GET /api/profiles` |
| Teach EPP custom | `teach.py`, `modules/teach.js` | `/api/teach/*` |
| Teach Acciones | `teach.py` — `montacargas`, `celular`, `carga_suspendida` | `/api/teach/*` |
| Agudeza / calidad facial | `identity.py` | Tests `test_detection_acuity.py` |

### 2.2 Acciones (v61–v62) — diferenciador clave

Motor en `backend/app/actions.py`, UI en `frontend/assets/modules/actions.js`.

**Presets de reglas:**

| Regla | Tipo | Severidad |
|-------|------|-----------|
| Sin EPP completo en faena | `epp_non_compliant` | alta |
| Caída detectada | `fall_detected` | crítica |
| Celular en zona restringida | `detect_in_zone` | media |
| Persona cerca montacargas/grúa | `proximity` | alta |
| Persona bajo carga suspendida | `proximity` | crítica |
| Near-miss: peatón en vía vehículos | `person_in_zone` | alta |

**P1 v62:** reglas por `source_id` (cámara/NVR), distancia en **metros** (`meters_per_pixel`), zonas `by_source`, editor visual con slider y calibración.

### 2.3 Identidad y portería

- Enrolamiento multi-foto, umbrales de nitidez/área, liveness heurístico
- Identificación live con margen vs. 2.º candidato
- QR cédula, modo `qr_only` (privacidad Ley 21.719)
- Consentimiento DS 44 / Ley 19.628 (`consent.csv`)
- Backup ZIP workers + rostros (`backup.py`)

### 2.4 Video / NVR / masivo

- NVR: Hikvision, Dahua, Uniview, ONVIF, genérico (`nvr.py`)
- RTSP con anti-SSRF (`rtsp_security.py`, `security_urls.py`)
- Escaneo masivo hasta 16 canales (`mass_scan.py`, `watchlist.py`)
- Zonas por fuente con presets faena/portería/bodega (`zones.py`)

### 2.5 Salidas físicas e integraciones

| Integración | Estado |
|-------------|--------|
| Webhook EHS | ✅ |
| SafetyCloud JSON | ✅ |
| SAP EWM | ⚠️ stub |
| WhatsApp Cloud API | ✅ |
| Email SMTP | ✅ |
| ESP32 alarma | ✅ (`hardware/esp32-alarm/`) |
| Modbus / Wiegand portería | ✅ (`access_gate.py`) |

### 2.6 UX operativa

| Feature | Módulo |
|---------|--------|
| Wizard día cero | `day-zero-wizard.js` |
| Kiosk portería | `kiosk.js` |
| Modo operador (RBAC UI) | `auth.js`, CSS `data-role` |
| PWA + service worker v62 | `sw.js`, `manifest.webmanifest` |
| Skins | `theme.js` — faena, portuario, minería, claro, alto contraste |
| Alertas sonoras | `audio-alerts.js` |
| Informes / Safety Score | `reports.js` |

---

## 3. Seguridad (P0 / P1 / P2)

### P0 — Crítico (cerrado)

| Control | Test |
|---------|------|
| PIN no es bearer permanente | `test_pin_not_permanent_bearer` |
| PINs por defecto bloqueados en cloud | `test_default_pins_blocked_on_cloud` |
| SSRF RTSP (loopback, metadata, LAN cloud) | 3 tests RTSP |
| Secretos EHS cifrados en disco (Fernet) | `test_ehs_secrets_encrypted_on_disk` |

### P1 — Alto (cerrado)

| Control | Test |
|---------|------|
| Sesión post-login | `test_login_session_works` |
| API key estática opcional | `test_api_key_still_works_as_bearer` |
| Métricas no públicas en cloud | `test_metrics_not_public_on_cloud` |
| Headers seguridad (CSP, nosniff, X-Request-Id) | `test_security_headers_present` |
| WebSocket autenticado | `test_ws_detect.py` |
| OIDC callback + state (Redis opcional) | `test_oidc_callback_public_without_auth` |

### P2 — Medio (abierto / monitorear)

1. **RBAC superficial** — solo `admin` / `operator`; sin ACL por recurso, sin SCIM/LDAP
2. **CSP permisiva** — `'unsafe-inline'` en estilos
3. **Sesiones en JSON** — no cluster-safe (Redis solo para OIDC state)
4. **Liveness biométrico heurístico** — no anti-spoof enterprise
5. **Scripts E2E desactualizados** — `review_e2e.sh` y `review_full_e2e.sh` exigen `v58`
6. **Dependencias ML** — pins amplios (`ultralytics`, OpenCV)
7. **Sin certificación formal** — controles alineados SOC2-style, sin attestation

### P3 — Bajo

1. Iconos PWA reutilizan un solo favicon
2. Salida kiosk vía `window.prompt` (funcional, no hardened)
3. Dockerfile comentado en v32 (cosmético)

---

## 4. Despliegue y operaciones

| Artefacto | Uso |
|-----------|-----|
| `docker-compose.yml` + `Dockerfile` | Edge producción, volumen `/data` |
| `render.yaml` | Demo cloud (sin RTSP real) |
| `docs/RUNBOOK_DEPLOY_EDGE.md` | VLAN, UPS, PIN, checklist hardware |
| `docs/RUNBOOK_BACKUP.md` | Rotación backup identity |
| `docs/RUNBOOK_ENTRENAR_EPP_FAENA.md` | Teach por perfil |
| `.env.example` | OIDC, Redis, OTEL, RTSP allowlist |
| `cloud_persist.py` | Persistencia Render Free vía HF Hub |
| `metrics.py` + `otel_trace.py` | Prometheus + OTLP opcional |

**Restricción arquitectónica:** RTSP/NVR requiere edge en LAN; cloud no alcanza cámaras privadas.

---

## 5. Tests ejecutados (v63)

```
pytest tests/ --ignore=tests/e2e     → 107 passed
test_security_audit.py               → 14 passed
npm run lint (ESLint)                → OK
ruff check backend/app tests         → OK (post-merge)
review_e2e.sh                        → 11/12 (falla pin build v58)
```

**CI** (`.github/workflows/ci.yml`): 2 jobs — `test` (Ruff, Bandit, ESLint, pytest) y `browser-e2e` (Playwright chromium, 6 tests).

**Cobertura E2E browser:** login, pestaña Personas, enrolar fotos, identificar, restricciones operador. **Sin E2E** aún para Acciones, NVR import, mass scan, kiosk, EHS push.

---

## 6. Gaps vs. producto enterprise comercial

| Gap | Impacto | Mitigación sugerida |
|-----|---------|---------------------|
| Catálogo limitado de detecciones (~10 vs 50–200) | Medio | Expandir presets Acciones P2; teach por clase |
| Sin workflows EHS bidireccionales | Medio | Conectores pull + estados de acción correctiva |
| Sin HA / failover | Alto en plantas críticas | Documentar topología activo-pasivo manual |
| Sin VMS nativo (Milestone, Genetec) | Medio | RTSP universal como estándar de facto |
| SAP EWM stub | Bajo si no hay SAP | Implementar o retirar del UI |
| Multi-faena local ≠ SaaS | Por diseño | No construir (ver `AGENTS.md`) |

---

## 7. Fortalezas diferenciadoras

1. **EPP + identidad en un solo frame** en portería — pocos competidores lo integran nativamente
2. **Teach EPP por faena** — adapta casco/chaleco a colores reales del sitio
3. **Acciones P1 con metros y cámara** — proximidad calibrable, no solo píxeles
4. **Salidas físicas** — ESP32, Modbus, Wiegand (cierre de loop vs. solo dashboard)
5. **Localización Chile** — RUT, consentimiento, perfiles portuario/minería/construcción
6. **NVR nativo** — import Dahua/Hikvision a escaneo masivo
7. **Soberanía de datos edge** — biometría y video no salen de LAN
8. **Disciplina de seguridad automatizada** — 14 tests P0/P1 (inusual en productos indie/open)
9. **Costo de entrada bajo** — Docker + cámaras existentes vs. contrato enterprise

---

## 8. Recomendaciones priorizadas

| Prioridad | Acción | Esfuerzo |
|-----------|--------|----------|
| **P1** | Actualizar `review_*_e2e.sh` a build `v62` | Bajo |
| **P1** | E2E Playwright: pestaña Acciones + editor regla | Medio |
| **P2** | Acciones P2: alertas sonoras por severidad, historial eventos | Medio |
| **P2** | Pin estricto dependencias ML en `requirements.txt` | Bajo |
| **P2** | CSP más estricta (nonce/hash para inline) | Medio |
| **P3** | RBAC granular (permisos por sección API) | Alto |
| **P3** | Tests de carga / concurrencia inferencia | Medio |

---

## 9. Conclusión

VigiEPP v62 es **enterprise-ready para edge faena** en seguridad operativa, integración NVR, identidad biométrica y vigilancia de conductas inseguras. El principal gap frente a Intenseye/Protex/viAct no es vulnerabilidad P0 abierta, sino **amplitud del catálogo de detecciones**, **profundidad EHS workflow** y **escala multi-sitio gestionada** — áreas explícitamente fuera del modelo de producto edge/on-prem.

**Score auditoría interna:** **8.8 / 10** operativo edge · **6.4 / 10** como plataforma SaaS EHS global (por diseño).

Ver ranking competitivo detallado en `docs/INFORME_AVANCES_RANKING_v63.md`.
