#!/bin/bash
# Auto-reset exhausted Anthropic credentials so token refresh can occur
# Called via cron every 30 minutes

HERMES_BIN="/home/chris/.hermes/hermes-agent/venv/bin/python"
HERMES_CLI="hermes_cli.main"

STATUS=$($HERMES_BIN -m $HERMES_CLI auth list 2>&1)

if echo "$STATUS" | grep -q "anthropic.*exhausted"; then
    $HERMES_BIN -m $HERMES_CLI auth reset anthropic 2>&1
    echo "$(date -Iseconds) Reset exhausted anthropic credential" >> /home/chris/.hermes/logs/auth-reset.log
fi

if echo "$STATUS" | grep -q "openrouter.*exhausted"; then
    $HERMES_BIN -m $HERMES_CLI auth reset openrouter 2>&1
    echo "$(date -Iseconds) Reset exhausted openrouter credential" >> /home/chris/.hermes/logs/auth-reset.log
fi
