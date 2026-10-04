#!/usr/bin/env bash
# Genera ZIP portable para PC de prueba Windows.
# Salida SIEMPRE fuera de OneDrive: /opt/cursor/artifacts/ (Linux) o ruta explícita.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

# Destino fuera de OneDrive / carpetas sincronizadas.
# Usar /tmp para staging+zip (evita cuota en cursor-agent-store) y copiar a artifacts.
OUT_BASE="${VIGIEPP_PORTABLE_OUT:-/opt/cursor/artifacts}"
WORK_BASE="${VIGIEPP_PORTABLE_WORK:-/tmp/vigiepp-portable-build}"
export TMPDIR="${TMPDIR:-/tmp}"
STAMP="$(date -u +%Y%m%d)"
BUILD_V="$(grep -m1 'BUILD_VERSION' backend/app/routers/core.py | sed 's/.*"\(v[0-9]*\)".*/\1/')"
FORENSE_B="$(grep -m1 '^BUILD' forense/app/config.py | sed 's/.*"\([^"]*\)".*/\1/')"
PKG_NAME="VigiEPP-portable-PC-prueba-${BUILD_V}-${FORENSE_B}-${STAMP}"
STAGING="${WORK_BASE}/${PKG_NAME}"
ZIP_WORK="${WORK_BASE}/${PKG_NAME}.zip"
ZIP_PATH="${OUT_BASE}/${PKG_NAME}.zip"

if echo "${OUT_BASE}" | grep -qi 'onedrive'; then
  echo "[build] ERROR: destino parece OneDrive: ${OUT_BASE}"
  echo "        Use: export VIGIEPP_PORTABLE_OUT=/opt/cursor/artifacts"
  exit 1
fi

echo "[build] VigiEPP portable → ${ZIP_PATH}"
echo "[build] Destino confirmado FUERA de OneDrive"

rm -rf "${STAGING}" "${ZIP_WORK}"
mkdir -p "${STAGING}" "${OUT_BASE}" "${WORK_BASE}"

RSYNC_EXCLUDES=(
  --exclude '.git'
  --exclude '.venv'
  --exclude 'backend/.venv'
  --exclude 'node_modules'
  --exclude '__pycache__'
  --exclude '*.pyc'
  --exclude '.pytest_cache'
  --exclude 'forense/data/jobs'
  --exclude 'forense/data/knowledge'
  --exclude 'backend/data/faces/*'
  --exclude 'backend/data/evidence'
  --exclude 'backend/runs'
  --exclude 'backend/datasets'
  --exclude 'agent-tools'
  --exclude '.cursor'
  --exclude 'hardware'
)

echo "[build] Copiando código..."
tar -cf - \
  --exclude='.git' \
  --exclude='.venv' \
  --exclude='backend/.venv' \
  --exclude='node_modules' \
  --exclude='__pycache__' \
  --exclude='forense/data/jobs' \
  --exclude='forense/data/knowledge' \
  --exclude='forense/tests' \
  --exclude='tests' \
  --exclude='backend/data/faces' \
  --exclude='backend/data/evidence' \
  --exclude='backend/runs' \
  --exclude='backend/datasets' \
  --exclude='.cursor' \
  --exclude='hardware' \
  backend frontend forense scripts docs/PROBAR.md docs/FORENSE_LICENSE_EDGE.md docs/RUNBOOK_DEPLOY_EDGE.md portable \
  docker-compose.yml Dockerfile .env.example README.md AGENTS.md start-edge.bat \
  | tar -xf - -C "${STAGING}"

# Modelos IA (offline en PC prueba)
echo "[build] Incluyendo modelos IA..."
mkdir -p "${STAGING}/backend/models" "${STAGING}/backend/data/models"
if [ -f backend/models/best_ppe.pt ]; then
  cp backend/models/best_ppe.pt "${STAGING}/backend/models/"
fi
for f in face_detection_yunet_2023mar.onnx face_recognition_sface_2021dec.onnx; do
  if [ -f "backend/data/models/${f}" ]; then
    cp "backend/data/models/${f}" "${STAGING}/backend/data/models/"
  fi
done

# Launchers en raíz del paquete
cp portable/LEEME-PC-PRUEBA.txt "${STAGING}/"
cp portable/INSTALAR.bat "${STAGING}/"
cp portable/INICIAR.bat "${STAGING}/"
cp portable/DETENER.bat "${STAGING}/"
cp portable/env.portable.example "${STAGING}/env.portable.example"

# Manifest
cat > "${STAGING}/VERSION.txt" <<EOF
VigiEPP=${BUILD_V}
Forense=${FORENSE_B}
fecha_utc=${STAMP}
destino_recomendado=C:\\VigiEPP-prueba\\
NO_ONEDRIVE=1
EOF

mkdir -p "${STAGING}/backend/data" "${STAGING}/forense/data"
touch "${STAGING}/backend/data/.gitkeep" "${STAGING}/forense/data/.gitkeep"

echo "[build] Comprimiendo en ${WORK_BASE}..."
rm -f "${ZIP_WORK}"
(cd "${WORK_BASE}" && zip -rq "${PKG_NAME}.zip" "${PKG_NAME}")
cp -f "${ZIP_WORK}" "${ZIP_PATH}"

BYTES="$(stat -c%s "${ZIP_PATH}" 2>/dev/null || stat -f%z "${ZIP_PATH}")"
MB=$((BYTES / 1024 / 1024))

echo "[build] OK: ${ZIP_PATH} (${MB} MB)"
echo "[build] Extraer en PC prueba en: C:\\VigiEPP-prueba\\  (NO OneDrive)"
sha256sum "${ZIP_PATH}" > "${ZIP_PATH}.sha256"
cat "${ZIP_PATH}.sha256"
rm -rf "${STAGING}" "${ZIP_WORK}"
