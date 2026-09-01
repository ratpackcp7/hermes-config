#!/usr/bin/env bash
set -euo pipefail

HERMES_HOME="${HERMES_HOME:-$HOME/.hermes}"
CHAT_ID="8697133440"
HEALTH_URL="http://127.0.0.1:8642/health"
MAX_WAIT=30
POLL_INTERVAL=2

# Read Telegram bot token from .env
TOKEN=$(grep -m1 '^TELEGRAM_BOT_TOKEN=' "$HERMES_HOME/.env" | cut -d= -f2-)
if [[ -z "$TOKEN" ]]; then
  echo "ERROR: TELEGRAM_BOT_TOKEN not found in $HERMES_HOME/.env" >&2
  exit 1
fi

send_telegram() {
  local msg="$1"
  curl -s -X POST "https://api.telegram.org/bot${TOKEN}/sendMessage" \
    -d chat_id="$CHAT_ID" \
    -d text="$msg" \
    -d parse_mode="HTML" >/dev/null 2>&1
}

# Notify before restart
send_telegram "🔄 Bob: Restarting gateway. Back in ~10s."

# Restart
systemctl --user restart hermes-gateway.service

# Poll for health
elapsed=0
while (( elapsed < MAX_WAIT )); do
  sleep "$POLL_INTERVAL"
  elapsed=$(( elapsed + POLL_INTERVAL ))
  if curl -s --max-time 3 "$HEALTH_URL" >/dev/null 2>&1; then
    send_telegram "✅ Bob: Gateway back online."
    exit 0
  fi
done

# Failed to come back
send_telegram "❌ Bob: Gateway failed to restart. Watchdog will retry in ~5min."
exit 1
