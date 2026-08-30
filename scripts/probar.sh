#!/usr/bin/env bash
# Arranque rápido VigiEPP + Forense para pruebas locales / Cloud Agent.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

PY="${ROOT}/.venv/bin/python"
UVICORN="${ROOT}/.venv/bin/uvicorn"
if [ ! -x "$PY" ]; then
  echo "Ejecutá primero: bash .cursor/install.sh"
  exit 1
fi

export PYTHONPATH="${ROOT}/backend"
export VIGIEPP_DATA_DIR="${VIGIEPP_DATA_DIR:-${ROOT}/backend/data}"
export VIGIEPP_AUTH="${VIGIEPP_AUTH:-1}"
export VIGIEPP_ADMIN_PIN="${VIGIEPP_ADMIN_PIN:-vigiepp}"
export VIGIEPP_OPERATOR_PIN="${VIGIEPP_OPERATOR_PIN:-porteria}"
export VIGIEPP_COMBINED_INFERENCE="${VIGIEPP_COMBINED_INFERENCE:-0}"
export VIGIEPP_DOCS="${VIGIEPP_DOCS:-1}"
export ULTRALYTICS_OFFLINE="${ULTRALYTICS_OFFLINE:-false}"

mkdir -p "$VIGIEPP_DATA_DIR" "${ROOT}/forense/data"

stop_port() {
  local port="$1"
  local pid
  pid="$(lsof -ti "tcp:${port}" -sTCP:LISTEN 2>/dev/null | head -1)"
  if [ -n "${pid:-}" ]; then
    echo "[probar] deteniendo PID $pid en puerto $port"
    kill "$pid" 2>/dev/null || true
    sleep 1
  fi
}

wait_health() {
  local url="$1" label="$2" max="${3:-90}"
  local i=0
  while [ "$i" -lt "$max" ]; do
    if curl -sf --max-time 3 "$url" >/dev/null 2>&1; then
      echo "[probar] OK $label"
      return 0
    fi
    sleep 2
    i=$((i + 2))
  done
  echo "[probar] TIMEOUT $label ($url)" >&2
  return 1
}

echo "=== VigiEPP — modo prueba ==="
stop_port 8000
stop_port 8001

echo "[probar] iniciando VigiEPP :8000"
nohup "$UVICORN" app.main:app --host 0.0.0.0 --port 8000 --app-dir backend \
  > /tmp/vigiepp-8000.log 2>&1 &
echo $! > /tmp/vigiepp-8000.pid

wait_health "http://127.0.0.1:8000/api/health" "VigiEPP health"

echo "[probar] iniciando Forense :8001"
"$PY" -m pip install -q -r forense/requirements.txt 2>/dev/null || true
export PYTHONPATH="${ROOT}/backend:${ROOT}"
export VIGIEPP_FORENSE_DATA_DIR="${VIGIEPP_FORENSE_DATA_DIR:-${ROOT}/forense/data}"
export VIGIEPP_FORENSE=1
export VIGIEPP_FORENSE_LICENSE="${VIGIEPP_FORENSE_LICENSE:-dev}"
nohup "$PY" -m uvicorn forense.app.main:app --host 0.0.0.0 --port 8001 \
  > /tmp/vigiepp-8001.log 2>&1 &
echo $! > /tmp/vigiepp-8001.pid

wait_health "http://127.0.0.1:8001/api/forense/health" "Forense health"

BUILD="$(curl -sf http://127.0.0.1:8000/api/health | "$PY" -c 'import sys,json; print(json.load(sys.stdin).get("build","?"))')"
echo ""
echo "════════════════════════════════════════════"
echo "  VigiEPP listo para probar — build $BUILD"
echo "════════════════════════════════════════════"
echo "  App:     http://127.0.0.1:8000/"
echo "  API:     http://127.0.0.1:8000/docs"
echo "  Forense: http://127.0.0.1:8001/"
echo ""
echo "  PIN admin:    ${VIGIEPP_ADMIN_PIN}"
echo "  PIN portería: ${VIGIEPP_OPERATOR_PIN}"
echo ""
echo "  Logs: /tmp/vigiepp-8000.log  /tmp/vigiepp-8001.log"
echo "  Guía: docs/PROBAR.md"
echo "════════════════════════════════════════════"
