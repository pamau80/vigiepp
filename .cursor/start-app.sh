#!/usr/bin/env bash
# Arranca VigiEPP en :8000 (Cloud Agent / local). Idempotente.
set -euo pipefail
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT/backend"
export VIGIEPP_DOCS=1
export ULTRALYTICS_OFFLINE=false
UVICORN="$REPO_ROOT/.venv/bin/uvicorn"
if [ ! -x "$UVICORN" ]; then
  echo "[start-app] ERROR: no existe $UVICORN — ejecutá bash .cursor/install.sh"
  exit 1
fi
if curl -sf http://127.0.0.1:8000/api/health >/dev/null 2>&1; then
  echo "[start-app] VigiEPP ya responde en http://0.0.0.0:8000"
  exit 0
fi
exec "$UVICORN" app.main:app --host 0.0.0.0 --port 8000
