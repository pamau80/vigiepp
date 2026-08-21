#!/usr/bin/env bash
# VigiEPP — Cloud Agent install (idempotente).
# IMPORTANTE: el venv y los modelos viven en $HOME (fuera de /workspace) porque
# Cursor re-clona /workspace en cada arranque y borraría lo no versionado. $HOME
# sí persiste en el snapshot y sobrevive al re-checkout.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

VIGIEPP_HOME="${VIGIEPP_HOME:-$HOME/.vigiepp}"
VENV_DIR="$VIGIEPP_HOME/venv"
MODELS_DIR="$VIGIEPP_HOME/models"          # YuNet/SFace + best_ppe.pt (caché durable)
PY="$VENV_DIR/bin/python"

mkdir -p "$VIGIEPP_HOME" "$MODELS_DIR"

# 0) Paquetes de sistema (venv + libs de OpenCV). Idempotente vía apt.
if command -v apt-get >/dev/null 2>&1; then
  APT="apt-get"; command -v sudo >/dev/null 2>&1 && [ "$(id -u)" != "0" ] && APT="sudo apt-get"
  NEEDED=""
  dpkg -s python3.12-venv >/dev/null 2>&1 || NEEDED="$NEEDED python3.12-venv"
  ldconfig -p | grep -q "libGL.so.1" || NEEDED="$NEEDED libgl1"
  ldconfig -p | grep -q "libglib-2.0.so.0" || NEEDED="$NEEDED libglib2.0-0"
  if [ -n "$NEEDED" ]; then
    echo "[install] instalando paquetes de sistema:$NEEDED"
    $APT update -qq
    $APT install -y -q $NEEDED
  fi
fi

# 1) venv en $HOME (reutiliza si ya existe)
if [ ! -x "$PY" ]; then
  echo "[install] Creando venv en $VENV_DIR"
  python3 -m venv "$VENV_DIR"
fi

"$PY" -m pip install --upgrade pip

# 2) PyTorch CPU primero (más liviano que CUDA)
"$PY" -m pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu

# 3) Dependencias del backend
"$PY" -m pip install -r "$REPO_ROOT/backend/requirements.txt"

# 4) Precargar pesos de IA en la caché durable de $HOME (idempotente)
fetch() { # url destino
  local url="$1" dest="$2"
  if [ -s "$dest" ]; then
    echo "[install] ya existe $(basename "$dest")"
    return 0
  fi
  echo "[install] descargando $(basename "$dest")"
  curl -fsSL -o "$dest" "$url"
}

fetch "https://huggingface.co/ayushgupta7777/safetyvision-yolov8/resolve/main/v2/best.pt" \
      "$MODELS_DIR/best_ppe.pt"
fetch "https://github.com/opencv/opencv_zoo/raw/main/models/face_detection_yunet/face_detection_yunet_2023mar.onnx" \
      "$MODELS_DIR/face_detection_yunet_2023mar.onnx"
fetch "https://github.com/opencv/opencv_zoo/raw/main/models/face_recognition_sface/face_recognition_sface_2021dec.onnx" \
      "$MODELS_DIR/face_recognition_sface_2021dec.onnx"

echo "[install] OK (venv=$VENV_DIR, models=$MODELS_DIR)"
