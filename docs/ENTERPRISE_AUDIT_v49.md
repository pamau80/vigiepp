# Auditoría Enterprise VigiEPP — v49

**Fecha:** 2026-08-27  
**Rama:** `cursor/nvr-mass-navigation-cce8` · PR #8  
**Build:** `v49`

## Resumen ejecutivo

La modularización del frontend alcanzó **585 líneas** en `app.js` (desde ~4354 en v41), con **29 módulos ES** en `frontend/assets/modules/`. La superficie de seguridad P0/P1 validada por `tests/test_security_audit.py` pasa al 100%. E2E API completo: **34/34** checks.

| Área | Estado | Notas |
|------|--------|-------|
| Auth PIN / sesión | ✅ OK | PIN no válido como bearer permanente |
| SSRF RTSP | ✅ OK | Loopback, metadata host, LAN en cloud |
| OIDC | ✅ OK | Callback público; state en Redis (v42+) |
| EHS secretos | ✅ OK | Encriptados en disco |
| Métricas Prometheus | ✅ OK | Protegidas en cloud por defecto |
| Headers seguridad | ✅ OK | CSP, nosniff, X-Request-Id |
| Modularización frontend | ✅ Avanzada | `app.js` ~86% reducido vs v41 |
| CI Ruff | ⚠️ Falla | 137+ avisos en tests (preexistente) |
| OpenTelemetry | ⚠️ Stub | Solo spans locales con `VIGIEPP_OTEL` |
| Cobertura E2E script | ✅ OK | Orden login corregido en v49 |

---

## 1. Modularización frontend (v41 → v49)

### Evolución

| Build | `app.js` líneas | Módulos ES |
|-------|-----------------|------------|
| v41 | ~4354 | 0 (monolito) |
| v47 | ~1053 | 22 |
| v48 | ~729 | 28 |
| **v49** | **585** | **29** |

### Módulos v49 (nuevos o ampliados)

- `enterprise.js` — `bindEnterpriseEvents()` (sites, OIDC, EHS)
- `zones.js` — `bindZonesEditorEvents()` (editor UI)
- `app-shell-events.js` — logout, upload archivo, resize

### Lo que queda en `app.js`

- Mapa `els` (DOM refs)
- Wiring / orden de inicialización de controladores
- Estado compartido (`lastIdentity`, `eppStreak`, etc.)
- Callbacks `setConfigSection` en `app-modes`

**P3 recomendado:** extraer mapa `els` + estado a `app-state.js` o factory `createApp()`.

---

## 2. Seguridad (P0 / P1)

### P0 — Crítico (cerrado)

| Control | Verificación |
|---------|--------------|
| PIN no es API key | `test_pin_not_permanent_bearer` |
| PIN por defecto bloqueado en cloud | `test_default_pins_blocked_on_cloud` |
| SSRF RTSP | `test_rtsp_blocks_loopback`, metadata, LAN cloud |
| Secretos EHS en disco | `test_ehs_secrets_encrypted_on_disk` |

### P1 — Alto (cerrado)

| Control | Verificación |
|---------|--------------|
| Sesión post-login | `test_login_session_works` |
| API key estática opcional | `test_api_key_still_works_as_bearer` |
| Métricas no públicas en cloud | `test_metrics_not_public_on_cloud` |
| Headers de seguridad | `test_security_headers_present` |
| WebSocket auth | `tests/test_ws_detect.py` |
| OIDC callback/state | `test_oidc_callback_public_without_auth` |

### P2 — Medio (abierto / monitorear)

1. **CI Ruff** — El job `CI / test` falla por Ruff en archivos de test (`F401`, `SIM117`, etc.). No bloquea runtime pero impide merge limpio.
2. **OpenTelemetry** — `otel_trace.py` es stub local; sin export OTLP/Jaeger.
3. **Dependencias ML** — `ultralytics`, `opencv` sin pin estricto de parches de seguridad en `requirements.txt`.
4. **CSP** — Presente pero permisiva para CDN/scripts inline del shell PWA.

### P3 — Bajo / mejoras

1. Reducir `app.js` a wiring puro (&lt;400 líneas).
2. Tests E2E browser (Playwright) para flujos enrolar/identificar.
3. Documentar runbook de rotación PIN y backup identity.
4. Lint frontend (ESLint) en CI.

---

## 3. Tests ejecutados (v49)

```
pytest tests/           → 68 passed
test_security_audit.py  → 14 passed
review_e2e.sh           → 12/12
review_full_e2e.sh      → 34/34
node --check app.js + modules → OK
```

---

## 4. API y endpoints

Cobertura smoke vía `test_api_full_coverage.py` y `review_full_e2e.sh`: health, auth, zones, scans, reports, notifications, cameras, mass, NVR, identity, teach, sites, privacy, EHS, audit, metrics.

---

## 5. Recomendaciones priorizadas

| Prioridad | Acción |
|-----------|--------|
| **P2** | `ruff check --fix` en `tests/` y fijar CI |
| **P2** | OTLP exporter opcional en `otel_trace.py` |
| **P3** | `app-state.js` + factory de arranque |
| **P3** | E2E UI con computer use / Playwright |

---

## 6. Conclusión

VigiEPP v49 cumple criterios **enterprise** en seguridad operativa (auth, SSRF, secretos, headers, métricas) y arquitectura frontend modular. El principal gap de ingeniería es **calidad de CI (Ruff)** y **telemetría distribuida completa**, no vulnerabilidades P0 abiertas en el código auditado.
