#!/usr/bin/env bash
# VigiEPP — Cloud Agent install (idempotente).
# El venv y los pesos viven en $HOME/.vigiepp para que sobrevivan un re-checkout
# de /workspace y queden capturados en el snapshot del entorno.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

HOME_DIR="${HOME:-/home/ubuntu}"
PREFIX="$HOME_DIR/.vigiepp"
VENV_DIR="$PREFIX/venv"
MODELS_DIR="$PREFIX/models"
PY="$VENV_DIR/bin/python"

# 0) Paquetes de sistema (venv + libs de OpenCV). Idempotente vía apt.
if command -v apt-get >/dev/null 2>&1; then
  APT="apt-get"
  if command -v sudo >/dev/null 2>&1 && [ "$(id -u)" != "0" ]; then
    APT="sudo apt-get"
  fi
  NEEDED=""
  dpkg -s python3-venv >/dev/null 2>&1 || dpkg -s python3.12-venv >/dev/null 2>&1 || NEEDED="$NEEDED python3-venv"
  ldconfig -p 2>/dev/null | grep -q "libGL.so.1" || NEEDED="$NEEDED libgl1"
  ldconfig -p 2>/dev/null | grep -q "libglib-2.0.so.0" || NEEDED="$NEEDED libglib2.0-0"
  if [ -n "$NEEDED" ]; then
    echo "[install] instalando paquetes de sistema:$NEEDED"
    $APT update -qq
    # shellcheck disable=SC2086
    $APT install -y -q $NEEDED
  fi
fi

mkdir -p "$MODELS_DIR" "$PREFIX"

# 1) venv (reutiliza si ya existe)
if [ ! -x "$PY" ]; then
  echo "[install] Creando venv en $VENV_DIR"
  python3 -m venv "$VENV_DIR"
fi

"$PY" -m pip install --upgrade pip

# 2) PyTorch CPU primero (más liviano que CUDA)
"$PY" -m pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu

# 3) Dependencias del backend
"$PY" -m pip install -r "$REPO_ROOT/backend/requirements.txt"

# 4) Precargar pesos de IA (idempotente: solo baja lo que falta)
fetch() {
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

# 5) Enlazar pesos al checkout actual (el app los busca en backend/)
mkdir -p "$REPO_ROOT/backend/models" "$REPO_ROOT/backend/data/models" "$REPO_ROOT/backend/data/faces"
ln -sfn "$MODELS_DIR/best_ppe.pt" "$REPO_ROOT/backend/models/best_ppe.pt"
ln -sfn "$MODELS_DIR/face_detection_yunet_2023mar.onnx" "$REPO_ROOT/backend/data/models/face_detection_yunet_2023mar.onnx"
ln -sfn "$MODELS_DIR/face_recognition_sface_2021dec.onnx" "$REPO_ROOT/backend/data/models/face_recognition_sface_2021dec.onnx"

echo "[install] OK"
