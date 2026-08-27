#!/usr/bin/env bash
# Revisión E2E completa — todos los módulos API VigiEPP v55
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
BASE="${BASE_URL:-http://127.0.0.1:8000}"
COOKIE=/tmp/vigi-full.cookie
PASS=0
FAIL=0
PY="${VIGIEPP_PYTHON:-}"
if [ -z "$PY" ] && [ -x "$ROOT/.venv/bin/python" ]; then
  PY="$ROOT/.venv/bin/python"
else
  PY="${PY:-python3}"
fi
export PYTHONPATH="${PYTHONPATH:-}:$ROOT/backend"

ok() { echo "✓ $1"; PASS=$((PASS+1)); }
bad() { echo "✗ $1"; FAIL=$((FAIL+1)); }

echo "=== VigiEPP FULL API Review v55 ==="

# Auth first (profiles/ppe require session)
curl -s -c "$COOKIE" -X POST "$BASE/api/auth/login" -H 'Content-Type: application/json' -d '{"pin":"vigiepp"}' | $PY -c "import sys,json; assert json.load(sys.stdin).get('ok')" && ok "auth login" || bad "auth login"

# Health + core
H=$(curl -s "$BASE/api/health")
echo "$H" | $PY -c "import sys,json; d=json.load(sys.stdin); assert d['build']=='v55'" && ok "health v55" || bad "health"

curl -s -b "$COOKIE" "$BASE/api/profiles" | $PY -c "import sys,json; assert isinstance(json.load(sys.stdin),list)" && ok "profiles" || bad "profiles"
curl -s -b "$COOKIE" "$BASE/api/ppe/catalog" | $PY -c "import sys,json; assert 'items' in json.load(sys.stdin)" && ok "ppe catalog" || bad "ppe"

# Auth (me + oidc)
curl -s -b "$COOKIE" "$BASE/api/auth/me" | $PY -c "import sys,json; assert json.load(sys.stdin).get('authenticated')" && ok "auth me" || bad "auth me"
curl -s -b "$COOKIE" "$BASE/api/auth/oidc/config" | $PY -c "import sys,json; assert 'enabled' in json.load(sys.stdin)" && ok "oidc config" || bad "oidc"

# Zones
curl -s -b "$COOKIE" "$BASE/api/zones" | $PY -c "import sys,json; assert 'zones' in json.load(sys.stdin)" && ok "zones get" || bad "zones"
curl -s -b "$COOKIE" "$BASE/api/zones/presets" | $PY -c "import sys,json; assert 'presets' in json.load(sys.stdin)" && ok "zones presets" || bad "zones presets"
curl -s -b "$COOKIE" -X POST "$BASE/api/zones" -H 'Content-Type: application/json' -d '{"zones":[]}' | $PY -c "import sys,json; assert json.load(sys.stdin)" && ok "zones save" || bad "zones save"

# Scans + reports
curl -s -b "$COOKIE" "$BASE/api/scans/recent" | $PY -c "import sys,json; assert isinstance(json.load(sys.stdin),list)" && ok "scans recent" || bad "scans"
curl -s -b "$COOKIE" "$BASE/api/reports/stats?days=7" | $PY -c "import sys,json; assert json.load(sys.stdin)" && ok "reports stats" || bad "reports stats"
curl -s -b "$COOKIE" "$BASE/api/reports/export.csv" | head -c 20 | grep -q . && ok "reports csv" || bad "reports csv"
curl -s -b "$COOKIE" "$BASE/api/reports/print.html" | head -c 50 | grep -qi html && ok "reports html" || bad "reports html"

# Notifications
curl -s -b "$COOKIE" "$BASE/api/notifications/config" | $PY -c "import sys,json; assert json.load(sys.stdin)" && ok "notif config" || bad "notif config"
curl -s -b "$COOKIE" "$BASE/api/notifications/log" | $PY -c "import sys,json; assert isinstance(json.load(sys.stdin),list)" && ok "notif log" || bad "notif log"
curl -s -b "$COOKIE" -X POST "$BASE/api/notifications/test" | $PY -c "import sys,json; assert json.load(sys.stdin)" && ok "notif test" || bad "notif test"

# Cameras + watchlist + mass
curl -s -b "$COOKIE" "$BASE/api/cameras" | $PY -c "import sys,json; assert json.load(sys.stdin).get('ok')" && ok "cameras list" || bad "cameras"
curl -s -b "$COOKIE" "$BASE/api/watchlist" | $PY -c "import sys,json; assert json.load(sys.stdin).get('ok')" && ok "watchlist" || bad "watchlist"
curl -s -b "$COOKIE" -X POST "$BASE/api/surveillance/mass/scan" | $PY -c "import sys,json; assert json.load(sys.stdin).get('ok')" && ok "mass scan" || bad "mass scan"

# NVR
curl -s -b "$COOKIE" "$BASE/api/nvr/vendors" | $PY -c "import sys,json; assert json.load(sys.stdin).get('ok')" && ok "nvr vendors" || bad "nvr vendors"
curl -s -b "$COOKIE" "$BASE/api/nvr/devices" | $PY -c "import sys,json; assert json.load(sys.stdin).get('ok')" && ok "nvr devices" || bad "nvr devices"

# Identity + teach
curl -s -b "$COOKIE" "$BASE/api/identity/workers" | $PY -c "import sys,json; assert isinstance(json.load(sys.stdin),list)" && ok "identity workers" || bad "identity"
curl -s -b "$COOKIE" "$BASE/api/identity/consent.csv" | head -c 30 | grep -q id && ok "consent csv" || bad "consent csv"
curl -s -b "$COOKIE" "$BASE/api/teach/guide" | $PY -c "import sys,json; assert json.load(sys.stdin)" && ok "teach guide" || bad "teach"
curl -s -b "$COOKIE" "$BASE/api/teach/classes" | $PY -c "import sys,json; assert isinstance(json.load(sys.stdin),list)" && ok "teach classes" || bad "teach classes"
curl -s -b "$COOKIE" "$BASE/api/teach/stats" | $PY -c "import sys,json; assert json.load(sys.stdin)" && ok "teach stats" || bad "teach stats"

# Sites + privacy + ehs + audit
curl -s -b "$COOKIE" "$BASE/api/sites" | $PY -c "import sys,json; assert 'sites' in json.load(sys.stdin)" && ok "sites" || bad "sites"
curl -s -b "$COOKIE" "$BASE/api/privacy/config" | $PY -c "import sys,json; assert json.load(sys.stdin).get('ok')" && ok "privacy" || bad "privacy"
curl -s -b "$COOKIE" "$BASE/api/ehs/config" | $PY -c "import sys,json; assert json.load(sys.stdin).get('ok')" && ok "ehs" || bad "ehs"
curl -s -b "$COOKIE" "$BASE/api/audit" | $PY -c "import sys,json; assert json.load(sys.stdin).get('ok')" && ok "audit" || bad "audit"
curl -s -b "$COOKIE" "$BASE/api/audit/export.csv" | head -c 10 | grep -q ts && ok "audit export" || bad "audit export"

# Metrics + security headers
curl -s "$BASE/metrics" | grep -q vigiepp_uptime_seconds && ok "metrics" || bad "metrics"
curl -sI "$BASE/api/health" | grep -qi "x-content-type-options: nosniff" && ok "security headers" || bad "security headers"

# RTSP stop (no stream required)
curl -s -b "$COOKIE" -X POST "$BASE/api/rtsp/stop" -H 'Content-Type: application/json' -d '{"url":"rtsp://127.0.0.1/x"}' | $PY -c "import sys,json; assert json.load(sys.stdin).get('ok')" && ok "rtsp stop" || bad "rtsp stop"

echo "=== FULL RESULT: $PASS passed, $FAIL failed ==="
[ "$FAIL" -eq 0 ]
