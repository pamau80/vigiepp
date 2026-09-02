#!/usr/bin/env bash
# Demo caso completo Forense — biblioteca + análisis + informe
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"
PY="${ROOT}/.venv/bin/python"
if [ ! -x "$PY" ]; then PY=python3; fi
export PYTHONPATH="${ROOT}/backend:${ROOT}"
export VIGIEPP_FORENSE_LICENSE="${VIGIEPP_FORENSE_LICENSE:-dev}"
export VIGIEPP_FORENSE="${VIGIEPP_FORENSE:-1}"
export VIGIEPP_AUTH="${VIGIEPP_AUTH:-1}"
export VIGIEPP_ADMIN_PIN="${VIGIEPP_ADMIN_PIN:-vigiepp}"
exec "$PY" forense/scripts/demo_caso_completo.py "$@"
