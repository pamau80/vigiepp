#!/usr/bin/env bash
# Pruebas de agudeza de detección + reporte legible (nitidez, match, blur, EPP).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
PY="${ROOT}/.venv/bin/python"
export PYTHONPATH="${ROOT}/backend:${ROOT}"
ART="${ARTIFACTS_DIR:-/opt/cursor/artifacts}"
mkdir -p "$ART"

echo "=== VigiEPP — pruebas de agudeza de detección ==="
set +e
"$PY" -m pytest tests/test_detection_acuity.py -v --tb=short 2>&1 | tee "$ART/detection-acuity-pytest.log"
PYTEST_EXIT=${PIPESTATUS[0]}
set -e

"$PY" "$ROOT/scripts/detection_acuity_report.py" --output "$ART/detection-acuity-report.md" --json "$ART/detection-acuity-report.json"

echo ""
echo "Reporte: $ART/detection-acuity-report.md"
echo "Log pytest: $ART/detection-acuity-pytest.log"
exit "$PYTEST_EXIT"
