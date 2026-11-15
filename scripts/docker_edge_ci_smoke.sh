#!/usr/bin/env bash
# Valida compose + build CI (sin pesos) + smoke /api/health — lanzamiento v68
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

echo "=== docker compose config ==="
docker compose config -q

TAG="${VIGIEPP_CI_IMAGE:-vigiepp-edge:ci}"
echo "=== docker build SKIP_MODEL_DOWNLOAD=1 → $TAG ==="
docker build --build-arg SKIP_MODEL_DOWNLOAD=1 -t "$TAG" .

NAME="vigiepp-ci-smoke-$$"
PORT="${VIGIEPP_CI_PORT:-18000}"
cleanup() { docker rm -f "$NAME" >/dev/null 2>&1 || true; }
trap cleanup EXIT

docker run -d --name "$NAME" \
  -e VIGIEPP_AUTH=0 \
  -e VIGIEPP_EPHEMERAL=0 \
  -e VIGIEPP_DATA_DIR=/data \
  -e VIGIEPP_COMBINED_INFERENCE=0 \
  -e ULTRALYTICS_OFFLINE=true \
  -p "${PORT}:8000" \
  "$TAG"

echo "=== esperando /api/health ==="
for _ in $(seq 1 60); do
  if curl -fsS "http://127.0.0.1:${PORT}/api/health" >/tmp/vigiepp-ci-health.json 2>/dev/null; then
    python3 -c "
import json
d=json.load(open('/tmp/vigiepp-ci-health.json'))
assert d.get('status')=='ok', d
assert d.get('build')=='v68', d
print('OK build', d['build'], 'release', (d.get('excellence') or {}).get('release'))
"
    exit 0
  fi
  sleep 2
done
docker logs "$NAME" || true
echo "ERROR: health timeout" >&2
exit 1
