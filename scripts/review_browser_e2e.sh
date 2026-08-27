#!/usr/bin/env bash
# E2E browser — Playwright (login, enrolar fotos, identificar)
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
PY="${ROOT}/.venv/bin/python"
if [ ! -x "$PY" ]; then
  PY=python3
fi

echo "=== VigiEPP Browser E2E (Playwright) ==="

if ! "$PY" -c "import playwright" 2>/dev/null; then
  echo "Instalando pytest-playwright…"
  "$PY" -m pip install -q pytest-playwright
  "$PY" -m playwright install chromium
fi

export PYTHONPATH="${PYTHONPATH:-}:$ROOT/backend"

echo "--- Bloque A: login, navegación, identificar, operador ---"
"$PY" -m pytest \
  tests/e2e/test_browser_core.py::test_browser_login_and_build \
  tests/e2e/test_browser_core.py::test_browser_navigate_personas_tab \
  tests/e2e/test_browser_identity.py \
  tests/e2e/test_browser_operator.py \
  -v --tb=short "$@"

echo "--- Bloque B: enrolar fotos por UI (servidor fresco) ---"
"$PY" -m pytest \
  tests/e2e/test_browser_core.py::test_browser_enroll_photos_in_ui \
  -v --tb=short "$@"

echo "=== Browser E2E OK ==="
