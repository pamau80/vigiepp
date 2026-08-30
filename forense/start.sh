#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
export PYTHONPATH="${ROOT}/backend:${ROOT}"
export VIGIEPP_FORENSE_DATA_DIR="${VIGIEPP_FORENSE_DATA_DIR:-${ROOT}/forense/data}"
export VIGIEPP_FORENSE="${VIGIEPP_FORENSE:-1}"
export VIGIEPP_FORENSE_LICENSE="${VIGIEPP_FORENSE_LICENSE:-dev}"
export VIGIEPP_AUTH="${VIGIEPP_AUTH:-1}"
export VIGIEPP_ADMIN_PIN="${VIGIEPP_ADMIN_PIN:-vigiepp}"
export VIGIEPP_COMBINED_INFERENCE="${VIGIEPP_COMBINED_INFERENCE:-0}"
PY="${ROOT}/.venv/bin/python"
if [ ! -x "$PY" ]; then PY=python3; fi
exec "$PY" -m uvicorn forense.app.main:app --host 0.0.0.0 --port "${VIGIEPP_FORENSE_PORT:-8001}" --reload
