#!/usr/bin/env bash
# vigiepp-watchdog.sh — monitoreo HA semi-automático (activo-pasivo 2 nodos)
# Ver: docs/RUNBOOK_HA_EDGE.md
set -euo pipefail

PRIMARY_HOST="${PRIMARY_HOST:-192.168.10.11}"
STANDBY_HOST="${STANDBY_HOST:-192.168.10.12}"
PORT="${PORT:-8000}"
LOG_FILE="${LOG_FILE:-/var/log/vigiepp-ha.log}"
ALERT_WEBHOOK_URL="${ALERT_WEBHOOK_URL:-}"
FAILOVER_CMD="${FAILOVER_CMD:-}"
AUTO_FAILOVER="${AUTO_FAILOVER:-0}"
HEALTH_PATH="/api/health"
TIMEOUT="${TIMEOUT:-5}"

usage() {
  cat <<'EOF'
Uso: vigiepp-watchdog.sh [--failover] [--check-only]

Variables de entorno:
  PRIMARY_HOST   IP/host del nodo activo (default: 192.168.10.11)
  STANDBY_HOST   IP/host del nodo pasivo (default: 192.168.10.12)
  PORT           Puerto VigiEPP (default: 8000)
  AUTO_FAILOVER  1 para ejecutar FAILOVER_CMD si primary cae
  FAILOVER_CMD   Comando a ejecutar en failover (ej. ssh standby 'docker compose up -d')
  ALERT_WEBHOOK_URL  URL POST JSON opcional al detectar primary caído
  LOG_FILE       Ruta del log (default: /var/log/vigiepp-ha.log)

Ejemplo cron (cada 60 s):
  * * * * * /opt/vigiepp/scripts/vigiepp-watchdog.sh --check-only
EOF
}

log() {
  local msg="[$(date -Is)] $*"
  echo "$msg"
  if [ -w "$(dirname "$LOG_FILE")" ] 2>/dev/null || mkdir -p "$(dirname "$LOG_FILE")" 2>/dev/null; then
    echo "$msg" >>"$LOG_FILE" 2>/dev/null || true
  fi
}

primary_healthy() {
  local url="http://${PRIMARY_HOST}:${PORT}${HEALTH_PATH}"
  curl -sf --max-time "$TIMEOUT" "$url" | jq -e '.status == "ok" and .identity_ready == true' >/dev/null 2>&1
}

standby_reachable() {
  ping -c 1 -W 2 "$STANDBY_HOST" >/dev/null 2>&1
}

send_alert() {
  local event="$1"
  local detail="$2"
  [ -z "$ALERT_WEBHOOK_URL" ] && return 0
  curl -sf --max-time 8 -X POST "$ALERT_WEBHOOK_URL" \
    -H "Content-Type: application/json" \
    -d "{\"event\":\"$event\",\"primary\":\"${PRIMARY_HOST}\",\"standby\":\"${STANDBY_HOST}\",\"detail\":\"$detail\",\"ts\":\"$(date -Is)\"}" \
    >/dev/null 2>&1 || log "WARN: alert webhook falló"
}

do_failover() {
  log "PRIMARY DOWN (${PRIMARY_HOST}:${PORT}) — iniciando procedimiento failover"
  send_alert "primary_down" "identity_ready check failed"
  if [ "$AUTO_FAILOVER" = "1" ] && [ -n "$FAILOVER_CMD" ]; then
    log "Ejecutando FAILOVER_CMD: $FAILOVER_CMD"
    if eval "$FAILOVER_CMD"; then
      log "FAILOVER_CMD exitoso — verificar standby http://${STANDBY_HOST}:${PORT}${HEALTH_PATH}"
      return 0
    fi
    log "ERROR: FAILOVER_CMD falló"
    return 1
  fi
  log "Failover manual requerido — ver docs/RUNBOOK_HA_EDGE.md sección 6"
  return 2
}

CHECK_ONLY=1
DO_FAILOVER=0
for arg in "$@"; do
  case "$arg" in
    --failover) DO_FAILOVER=1; CHECK_ONLY=0 ;;
    --check-only) CHECK_ONLY=1 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Opción desconocida: $arg" >&2; usage; exit 1 ;;
  esac
done

if primary_healthy; then
  log "OK primary ${PRIMARY_HOST}:${PORT}"
  exit 0
fi

if [ "$CHECK_ONLY" = "1" ] && [ "$DO_FAILOVER" = "0" ]; then
  do_failover
  exit $?
fi

if [ "$DO_FAILOVER" = "1" ]; then
  AUTO_FAILOVER=1
  if ! standby_reachable; then
    log "WARN: standby ${STANDBY_HOST} no responde ping"
  fi
  do_failover
  exit $?
fi

exit 1
