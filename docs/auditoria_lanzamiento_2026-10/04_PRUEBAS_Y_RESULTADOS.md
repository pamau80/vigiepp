# 04 — Pruebas y resultados

## Línea base (2026-10-22, America/Santiago)

Entorno: Cloud Agent VM, `.venv`, `VIGIEPP_COMBINED_INFERENCE=0`.

| Categoría | Comando | Resultado |
|-----------|---------|-----------|
| Lint Python | `ruff check backend/app tests --ignore E501` | **PASS** |
| Bandit | `bandit -q -r backend/app -x tests -lll` | **PASS** (sin salida) |
| Lint JS | `npm ci && npm run lint` | **PASS** |
| Pytest VigiEPP | `pytest tests/ --ignore=tests/e2e -q` | **127 passed** |
| Pytest Forense | `pytest forense/tests/ --ignore=forense/tests/e2e -q` | **53 passed** |
| Browser E2E | 7 tests Playwright (CI subset) | **7 passed** |
| Agudeza IA | `bash scripts/run_detection_acuity.sh` | **PASS** (reporte en `/opt/cursor/artifacts/detection-acuity-report.md`) |
| pip-audit | `pip-audit -r backend/requirements.txt` | **0 CVE** |
| probar.sh | `bash scripts/probar.sh` post-fix v68 | **PASS** (:8000/:8001 health) |

## E2E ejecutados

```
tests/e2e/test_browser_core.py::test_browser_login_and_build
tests/e2e/test_browser_core.py::test_browser_navigate_personas_tab
tests/e2e/test_browser_core.py::test_browser_enroll_photos_in_ui
tests/e2e/test_browser_identity.py::test_browser_identify_known_worker
tests/e2e/test_browser_operator.py (2)
tests/e2e/test_browser_actions.py::test_browser_actions_tab
```

## Pruebas no ejecutadas / bloqueadas

| Prueba | Motivo |
|--------|--------|
| `tests/e2e` restantes | No listados en CI subset |
| `forense/tests/e2e` | No corrido |
| `bash scripts/review_browser_e2e.sh` completo | Equivalente parcial ya ejecutado |
| Docker `compose build` | Tiempo; imagen no rebuild en VM |
| Carga / estrés | Sin autorización ni baseline hardware faena |
| Accesibilidad WCAG automatizada | Sin axe/lighthouse en corrida |

## Cobertura

- **No** se midió cobertura de líneas (`coverage.py` no ejecutado).
- Cobertura **por riesgo:** endpoints GET listados en `test_all_get_endpoints` (27+ rutas), seguridad P0/P1 dedicada, RBAC, NVR, privacy, mass scan.

## Totales

| | Pass | Fail | Block |
|---|-----:|-----:|------:|
| Automatizadas (unit/integration) | 180 | 0 | 0 |
| Browser E2E | 7 | 0 | 0 |
| Manuales GUI | 12 escenarios | 0 | 0 |
| **Total ejecutado** | **199** | **0** | **0** |

## Regresión post-correcciones v68

`pytest tests/ --ignore=tests/e2e` → 127 passed (incl. CSP fonts assertion).
