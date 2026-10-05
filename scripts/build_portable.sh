#!/usr/bin/env bash
# Genera vigiepp-portable.zip listo para Windows (doble clic en VigiEPP.bat)
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
OUT="${1:-${ROOT}/dist/vigiepp-portable.zip}"
mkdir -p "$(dirname "$OUT")"

echo "[build] Empaquetando VigiEPP portable -> $OUT"

zip -r "$OUT" . \
  -x ".git/*" \
  -x ".venv/*" \
  -x "*/__pycache__/*" \
  -x "*/node_modules/*" \
  -x "backend/runs/*" \
  -x "backend/datasets/*" \
  -x "backend/yolov8n.pt" \
  -x "agent-tools/*" \
  -x "hardware/*" \
  -x "tests/*" \
  -x "forense/tests/*" \
  -x "dist/*" \
  -x "portable/logs/*.log" \
  -x "*.pyc" \
  -x ".cursor/*"

echo "[build] OK — $(du -h "$OUT" | cut -f1)"
echo "  Copia el ZIP a Windows, descomprime y doble clic en VigiEPP.bat"
