# 02 — Matriz funcional

## Módulos UI (pestañas `data-mode`)

| ID | Módulo | Acción esperada | Resultado prueba | Evidencia |
|----|--------|-----------------|------------------|-----------|
| F-01 | Vivo | Webcam / RTSP / foto + detect | OK | E2E login, computer-use `02-initial-load-vivo-tab.webp` |
| F-02 | Masivo | Barrido multi-canal | UI OK; barrido requiere NVR real | Screenshot `03-masivo-tab.webp` |
| F-03 | Equipos | CRUD NVR, import watchlist | API cubierta en pytest; UI OK | `04-equipos-tab.webp`, `test_nvr.py` |
| F-04 | Personas | Enrolamiento, backup | OK | E2E `test_browser_enroll_photos_in_ui`, `05-personas-tab.webp` |
| F-05 | EPP (teach) | Muestras, entrenar YOLO | UI OK; train requiere GPU/tiempo | `06-epp-tab.webp`, `test_api_full_coverage.py` |
| F-06 | Acciones | Reglas inseguras | OK | E2E `test_browser_actions_tab` |
| F-07 | Config | Apariencia, audio, zonas, privacidad, enterprise, audit | OK | `08-config-tab.webp` |
| F-08 | Informes | Stats, CSV, print | GET endpoints 200 sin auth en tests | `09-informes-tab.webp` |
| F-09 | Auth PIN | Login admin/operador | OK | E2E operator + kiosk |
| F-10 | Modo portería (kiosk) | Restringe UI operador | OK | `test_browser_operator_*` |
| F-11 | Day-zero wizard | Onboarding 8 pasos | Aparece post-login admin | computer-use report |
| F-12 | Logout | Cerrar sesión | Funcional vía API; botón puede quedar fuera de viewport en topbar estrecho | AUD-VIG-012 |

## Submenús Config (`data-cfg-sec`)

Apariencia, Guías, Audio, Zonas, Monitoreo, Privacidad, Enterprise, Bitácora — inspección visual OK (`08-config-tab.webp`).

## API CRUD representativos

| Recurso | Métodos | Auth | Tests |
|---------|---------|------|-------|
| `/api/identity/workers` | GET/POST/PATCH/DELETE | Admin | `test_api_full_coverage`, identity E2E |
| `/api/cameras` | GET/POST/DELETE | Admin | security RTSP tests |
| `/api/zones` | GET/POST | Admin lectura operador | `test_zones_by_source`, RBAC |
| `/api/detect` | POST | Ambos roles | acuity + `test_ws_detect` |
| `/api/privacy/config` | GET/POST | Admin | `test_privacy.py` |

## Entradas inválidas (muestra)

| Caso | Endpoint | Esperado | Verificado |
|------|----------|----------|------------|
| RTSP loopback | POST `/api/cameras` | 400 | `test_security_audit.py` |
| RTSP metadata SSRF | POST `/api/cameras` | 400 | idem |
| PIN como bearer permanente | GET `/api/zones` | 401 | idem |
| LAN RTSP en cloud | POST `/api/cameras` | 400 | idem |

## No verificado en esta corrida

- WhatsApp / hardware alarm en hardware real
- Forense UI completa (solo health + 53 tests unitarios forense)
- 16 canales RTSP concurrentes en LAN
- PWA offline prolongado / instalación móvil nativa

## Hallazgos funcionales

| ID | Sev | Descripción |
|----|-----|-------------|
| AUD-VIG-012 | LOW | Botón «Salir» puede no ser visible sin scroll en topbar densa; sesión sí revocable vía `/api/auth/logout` |
| AUD-VIG-013 | INFO | Webcam `NotFoundError` en VM sin cámara — esperado |
