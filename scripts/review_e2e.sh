#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
BASE="${BASE_URL:-http://127.0.0.1:8000}"
COOKIE=/tmp/vigi-review.cookie
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

echo "=== VigiEPP E2E Review v47 ==="

# Health
H=$(curl -s "$BASE/api/health")
echo "$H" | python3 -c "import sys,json; d=json.load(sys.stdin); assert d['build']=='v47'; assert 'default_pins' not in d; assert 'privacy' in d" && ok "health v47 sin default_pins" || bad "health"

# Auth login
curl -s -c "$COOKIE" -X POST "$BASE/api/auth/login" -H 'Content-Type: application/json' -d '{"pin":"vigiepp"}' | python3 -c "import sys,json; d=json.load(sys.stdin); assert d.get('ok')" && ok "auth login" || bad "auth login"

# Privacy roundtrip
curl -s -b "$COOKIE" -X POST "$BASE/api/privacy/config" -H 'Content-Type: application/json' -d '{"qr_only_mode":true,"retention_days":60}' | python3 -c "import sys,json; d=json.load(sys.stdin); c=d['config']; assert c['qr_only_mode'] and c['retention_days']==60" && ok "privacy save" || bad "privacy save"

curl -s -b "$COOKIE" "$BASE/api/privacy/config" | python3 -c "import sys,json; d=json.load(sys.stdin); assert d['config']['qr_only_mode']" && ok "privacy read" || bad "privacy read"

# Restore privacy
curl -s -b "$COOKIE" -X POST "$BASE/api/privacy/config" -H 'Content-Type: application/json' -d '{"qr_only_mode":false,"retention_days":90}' > /dev/null

# Sites
curl -s -b "$COOKIE" -X POST "$BASE/api/sites" -H 'Content-Type: application/json' -d '{"name":"Faena Review Test"}' | python3 -c "import sys,json; d=json.load(sys.stdin); assert d.get('site',{}).get('id')" && ok "site create" || bad "site create"

SITES=$(curl -s -b "$COOKIE" "$BASE/api/sites")
SITE_ID=$(echo "$SITES" | python3 -c "import sys,json; s=json.load(sys.stdin); sites=[x for x in s['sites'] if x['name']=='Faena Review Test']; print(sites[0]['id'] if sites else '')")
if [ -n "$SITE_ID" ]; then
  curl -s -b "$COOKIE" -X POST "$BASE/api/sites/active" -H 'Content-Type: application/json' -d "{\"site_id\":\"$SITE_ID\"}" | python3 -c "import sys,json; assert json.load(sys.stdin).get('ok')" && ok "site activate" || bad "site activate"
  curl -s -b "$COOKIE" -X POST "$BASE/api/sites/active" -H 'Content-Type: application/json' -d '{"site_id":"default"}' > /dev/null
else
  bad "site id"
fi

# Mass scan empty watchlist
curl -s -b "$COOKIE" -X POST "$BASE/api/surveillance/mass/scan" | python3 -c "import sys,json; d=json.load(sys.stdin); assert d.get('ok')" && ok "mass scan empty" || bad "mass scan"

# Metrics
curl -s "$BASE/metrics" | grep -q vigiepp_uptime_seconds && ok "metrics" || bad "metrics"

# SSRF webhook blocked on render sim
export RENDER=1
$PY -c "
import os
os.environ['RENDER']='1'
os.environ.pop('VIGIEPP_ALLOW_LAN', None)
os.environ.pop('VIGIEPP_DATA_DIR', None)
from app.security_urls import validate_lan_http_host
ok, msg = validate_lan_http_host('192.168.1.1')
assert not ok, msg
" && ok "ssrf lan block" || bad "ssrf lan block"

# NVR encrypt roundtrip
$PY -c "
from app.secret_box import encrypt_text, decrypt_text
t=encrypt_text('secret-pass')
assert t and decrypt_text(t)=='secret-pass'
" && ok "nvr encrypt" || bad "nvr encrypt"

# Compliance helper
$PY -c "
from app.detect_pipeline import compliance_cell_fields
p={'compliance':{'overall_compliant':False,'alerts':['a'],'persons':[{'missing':['casco']}]}}
f=compliance_cell_fields(p)
assert f['compliant'] is False and 'casco' in f['missing']
" && ok "mass compliance helper" || bad "compliance helper"

# EHS config
curl -s -b "$COOKIE" "$BASE/api/ehs/config" | python3 -c "import sys,json; d=json.load(sys.stdin); assert d.get('ok') and 'webhook' in d['config']['connectors']" && ok "ehs config" || bad "ehs config"

echo "=== RESULT: $PASS passed, $FAIL failed ==="
[ "$FAIL" -eq 0 ]
