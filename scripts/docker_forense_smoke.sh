#!/usr/bin/env bash
# Smoke Forense en Docker Compose edge (:8001)
set -euo pipefail
BASE="${FORENSE_URL:-http://127.0.0.1:8001}"
PIN="${FORENSE_PIN:-${VIGIEPP_ADMIN_PIN:-vigiepp}}"

echo "=== Forense Docker smoke ==="
curl -sf "$BASE/api/forense/health" | python3 -c "
import sys, json
d = json.load(sys.stdin)
assert d.get('status') == 'ok', d
print('health:', d.get('build'), 'license:', d.get('license', {}).get('valid'))
"

TOKEN=$(curl -sf -X POST "$BASE/api/forense/auth/login" \
  -H "Content-Type: application/json" \
  -d "{\"pin\":\"$PIN\"}" | python3 -c "import sys,json; print(json.load(sys.stdin).get('token',''))")

if [ -z "$TOKEN" ]; then
  echo "ERROR: login Forense falló (PIN=$PIN)" >&2
  exit 1
fi

curl -sf "$BASE/api/forense/knowledge/sources/catalog" \
  -H "X-VigiEPP-Key: $TOKEN" | python3 -c "
import sys, json
d = json.load(sys.stdin)
n = len(d.get('sources') or [])
assert n >= 10, d
print('catalog:', n, 'fuentes')
"

echo "OK Forense docker smoke"
