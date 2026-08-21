#!/usr/bin/env bash
# VigiEPP — arranque del backend (terminal del entorno).
# Auto-reparable: si falta el venv (p. ej. snapshot sin instalar), corre install.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VIGIEPP_HOME="${VIGIEPP_HOME:-$HOME/.vigiepp}"
VENV_DIR="$VIGIEPP_HOME/venv"
MODELS_DIR="$VIGIEPP_HOME/models"

if [ ! -x "$VENV_DIR/bin/uvicorn" ]; then
  echo "[start] venv ausente; ejecutando install.sh (puede tardar unos minutos)…"
  bash "$REPO_ROOT/.cursor/install.sh"
fi

# El detector YOLO busca los pesos en backend/models (dentro de /workspace, que se
# re-clona en cada arranque). Copiamos desde la caché durable de $HOME si falta.
mkdir -p "$REPO_ROOT/backend/models"
if [ ! -s "$REPO_ROOT/backend/models/best_ppe.pt" ] && [ -s "$MODELS_DIR/best_ppe.pt" ]; then
  cp "$MODELS_DIR/best_ppe.pt" "$REPO_ROOT/backend/models/best_ppe.pt"
fi

cd "$REPO_ROOT/backend"
export VIGIEPP_DOCS="${VIGIEPP_DOCS:-1}"
export ULTRALYTICS_OFFLINE="${ULTRALYTICS_OFFLINE:-false}"
export VIGIEPP_MODELS_DIR="${VIGIEPP_MODELS_DIR:-$MODELS_DIR}"  # YuNet/SFace durables

exec "$VENV_DIR/bin/uvicorn" app.main:app --host 0.0.0.0 --port 8000 --reload
