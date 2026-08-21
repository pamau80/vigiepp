#!/usr/bin/env bash
# VigiEPP — Cloud Agent start (idempotente).
# Re-enlaza los pesos persistentes de $HOME/.vigiepp al checkout fresco de /workspace.
# No levanta el servidor: eso vive en el terminal "backend".
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
HOME_DIR="${HOME:-/home/ubuntu}"
MODELS_DIR="$HOME_DIR/.vigiepp/models"
VENV_DIR="$HOME_DIR/.vigiepp/venv"

if [ ! -x "$VENV_DIR/bin/python" ]; then
  echo "[start] venv ausente; ejecutando install"
  if [ -f "$REPO_ROOT/.cursor/install.sh" ]; then
    bash "$REPO_ROOT/.cursor/install.sh"
  else
    echo "[start] falta $REPO_ROOT/.cursor/install.sh" >&2
    exit 1
  fi
fi

mkdir -p "$REPO_ROOT/backend/models" "$REPO_ROOT/backend/data/models" "$REPO_ROOT/backend/data/faces"
if [ -s "$MODELS_DIR/best_ppe.pt" ]; then
  ln -sfn "$MODELS_DIR/best_ppe.pt" "$REPO_ROOT/backend/models/best_ppe.pt"
fi
if [ -s "$MODELS_DIR/face_detection_yunet_2023mar.onnx" ]; then
  ln -sfn "$MODELS_DIR/face_detection_yunet_2023mar.onnx" "$REPO_ROOT/backend/data/models/face_detection_yunet_2023mar.onnx"
fi
if [ -s "$MODELS_DIR/face_recognition_sface_2021dec.onnx" ]; then
  ln -sfn "$MODELS_DIR/face_recognition_sface_2021dec.onnx" "$REPO_ROOT/backend/data/models/face_recognition_sface_2021dec.onnx"
fi

echo "[start] OK"
