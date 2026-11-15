#!/usr/bin/env bash
# Portable Windows ZERO-ADMIN: Python embebido + deps preinstaladas.
# No requiere Python del sistema, UAC ni INSTALAR.bat en el PC destino.
# Salida fuera de OneDrive: /opt/cursor/artifacts/
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

OUT_BASE="${VIGIEPP_PORTABLE_OUT:-/opt/cursor/artifacts}"
WORK_BASE="${VIGIEPP_PORTABLE_WORK:-/tmp/vigiepp-portable-build}"
export TMPDIR="${TMPDIR:-/tmp}"
PY_EMBED_VER="${VIGIEPP_PYTHON_EMBED:-3.12.7}"
STAMP="$(date -u +%Y%m%d)"
BUILD_V="$(grep -m1 'BUILD_VERSION' backend/app/routers/core.py | sed 's/.*"\(v[0-9]*\)".*/\1/')"
FORENSE_B="$(grep -m1 '^BUILD' forense/app/config.py | sed 's/.*"\([^"]*\)".*/\1/')"
PKG_NAME="VigiEPP-portable"
STAGING="${WORK_BASE}/${PKG_NAME}"
WHEELS="${WORK_BASE}/wheels-win-${STAMP}"
ZIP_WORK="${WORK_BASE}/${PKG_NAME}.zip"
ZIP_PATH="${OUT_BASE}/${PKG_NAME}.zip"

if echo "${OUT_BASE}" | grep -qi 'onedrive'; then
  echo "[build] ERROR: destino parece OneDrive: ${OUT_BASE}"
  exit 1
fi

echo "[build] Portable ZERO-ADMIN → ${ZIP_PATH}"
echo "[build] Python embed ${PY_EMBED_VER} + wheels win_amd64"

rm -rf "${STAGING}" "${ZIP_WORK}" "${WHEELS}"
mkdir -p "${STAGING}" "${OUT_BASE}" "${WORK_BASE}" "${WHEELS}"

# --- Código aplicación ---
echo "[build] [1/5] Copiando aplicación..."
tar -cf - \
  --exclude='.git' --exclude='.venv' --exclude='backend/.venv' \
  --exclude='node_modules' --exclude='__pycache__' \
  --exclude='forense/data/jobs' --exclude='forense/data/knowledge' \
  --exclude='forense/tests' --exclude='tests' \
  --exclude='backend/data/faces' --exclude='backend/data/evidence' \
  --exclude='backend/runs' --exclude='backend/datasets' \
  --exclude='.cursor' --exclude='hardware' \
  backend frontend forense scripts \
  docs/PROBAR.md docs/FORENSE_LICENSE_EDGE.md docs/RUNBOOK_DEPLOY_EDGE.md \
  README.md \
  | tar -xf - -C "${STAGING}"

# No incluir carpeta portable/ duplicada (confunde INICIAR.bat)
rm -rf "${STAGING}/portable"

mkdir -p "${STAGING}/backend/models" "${STAGING}/backend/data/models" \
  "${STAGING}/backend/data" "${STAGING}/forense/data"
if [ -f backend/models/best_ppe.pt ]; then
  cp backend/models/best_ppe.pt "${STAGING}/backend/models/"
fi
for f in face_detection_yunet_2023mar.onnx face_recognition_sface_2021dec.onnx; do
  [ -f "backend/data/models/${f}" ] && cp "backend/data/models/${f}" "${STAGING}/backend/data/models/"
done

# --- Python embebido Windows ---
echo "[build] [2/5] Descargando Python embebido Windows..."
EMBED_URL="https://www.python.org/ftp/python/${PY_EMBED_VER}/python-${PY_EMBED_VER}-embed-amd64.zip"
EMBED_ZIP="${WORK_BASE}/python-embed.zip"
curl -fsSL -o "${EMBED_ZIP}" "${EMBED_URL}"
mkdir -p "${STAGING}/python/Lib/site-packages"
unzip -q "${EMBED_ZIP}" -d "${STAGING}/python"
cat > "${STAGING}/python/python312._pth" <<'PTH'
python312.zip
.
Lib/site-packages
import site
PTH

# --- Wheels Windows ---
echo "[build] [3/5] Descargando dependencias Windows (~300 MB, varios minutos)..."
pip install -q pip --upgrade
pip download \
  -r "${ROOT}/portable/requirements-portable.txt" \
  torch torchvision \
  --platform win_amd64 \
  --python-version 312 \
  --only-binary=:all: \
  --extra-index-url https://download.pytorch.org/whl/cpu \
  -d "${WHEELS}"

echo "[build] [4/5] Instalando en python/Lib/site-packages..."
pip install \
  --target "${STAGING}/python/Lib/site-packages" \
  --platform win_amd64 \
  --python-version 312 \
  --implementation cp \
  --only-binary=:all: \
  --no-index \
  --find-links "${WHEELS}" \
  -r "${ROOT}/portable/requirements-portable.txt" \
  torch torchvision

# Launchers raíz
cp portable/LEEME-PC-PRUEBA.txt "${STAGING}/"
cp portable/INICIAR.bat "${STAGING}/"
cp portable/DETENER.bat "${STAGING}/"
cp portable/INSTALAR.bat "${STAGING}/"
cp portable/env.portable.example "${STAGING}/env.portable.example"

# CRLF obligatorio para cmd.exe (LF rompe title/set -> errores "tle", "et")
for _bat in INICIAR.bat DETENER.bat INSTALAR.bat; do
  sed -i 's/\r$//' "${STAGING}/${_bat}"
  sed -i 's/$/\r/' "${STAGING}/${_bat}"
done

cat > "${STAGING}/VERSION.txt" <<EOF
VigiEPP=${BUILD_V}
Forense=${FORENSE_B}
python_embed=${PY_EMBED_VER}
modo=zero-admin
auth_default=0
fecha_utc=${STAMP}
destino_recomendado=C:\\VigiEPP-prueba\\
NO_ONEDRIVE=recomendado
EOF

echo "[build] [5/5] Comprimiendo (puede tardar)..."
rm -f "${ZIP_WORK}"
(cd "${WORK_BASE}" && zip -rq -9 "${PKG_NAME}.zip" "${PKG_NAME}")
mkdir -p "${ROOT}/dist"
FINAL="${ROOT}/dist/${PKG_NAME}.zip"
cp -f "${ZIP_WORK}" "${FINAL}"
cp -f "${FINAL}" "${ZIP_PATH}" 2>/dev/null || true

BYTES="$(stat -c%s "${FINAL}" 2>/dev/null || stat -f%z "${FINAL}")"
MB=$((BYTES / 1024 / 1024))
sha256sum "${FINAL}" > "${FINAL}.sha256"

echo "[build] OK — UN SOLO ARCHIVO: ${FINAL} (${MB} MB)"
echo "[build] SHA256:"
cat "${FINAL}.sha256"
echo "[build] Windows: extraer → INICIAR.bat (sin admin)"

rm -rf "${STAGING}" "${ZIP_WORK}" "${WHEELS}" "${EMBED_ZIP}"
