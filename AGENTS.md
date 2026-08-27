# AGENTS.md — VigiEPP

## Modelo de producto

**Edge / on-prem por faena.** Un servidor en LAN con NVR/cámaras. **No es SaaS multitenancy.**

Roles: `admin` (config completa) y `operator` (monitoreo / portería).

## Entorno local

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r backend/requirements.txt
pip install pytest ruff bandit pytest-playwright
export PYTHONPATH=backend
export VIGIEPP_DATA_DIR=backend/data
export VIGIEPP_AUTH=1
export VIGIEPP_ADMIN_PIN=vigiepp
export VIGIEPP_OPERATOR_PIN=porteria
uvicorn app.main:app --host 127.0.0.1 --port 8000 --app-dir backend
```

## Tests

```bash
ruff check backend/app tests
bandit -q -r backend/app
npm ci && npm run lint
pytest tests/ --ignore=tests/e2e -q
bash scripts/run_detection_acuity.sh      # agudeza detección (13 tests + reporte)
bash scripts/review_browser_e2e.sh   # Playwright 6 tests
```

CI usa `VIGIEPP_COMBINED_INFERENCE=0` (sin inferencia pesada).

## Ramas y PRs

- Prefijo ramas agente: `cursor/<nombre>-cce8`
- Base: `main`
- Bump `BUILD_VERSION` en `backend/app/routers/core.py`, `frontend/assets/lib/constants.js`, `sw.js`

## Qué NO construir

- Organizaciones / billing SaaS
- Sync cloud-edge como pilar
- RBAC multi-tenant con cuentas en `users.json`
- Dashboard central multi-cliente

## Qué SÍ priorizar

- Runbook edge (`docs/RUNBOOK_DEPLOY_EDGE.md`)
- Seguridad P0/P1 (`tests/test_security_audit.py`)
- Modularización frontend (`frontend/assets/modules/`)
- E2E browser + API (`scripts/review_*.sh`)
- UX operador / kiosk / PWA

## Cursor Cloud

Puerto dev: 8000 (`.cursor/environment.json`). Instalar deps vía `.cursor/install.sh`.
