#!/bin/bash
# Auto-sync gateway config (model.default) to L1 memory
# Called from nightly-retrospective or session-start

set -euo pipefail

CONFIG_FILE="$HOME/.hermes/config.yaml"
MEMORY_FILE="$HOME/.hermes/memories/MEMORY.md"
SYNC_LOG="$HOME/.hermes/logs/config-sync.log"

mkdir -p "$(dirname "$SYNC_LOG")"

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$SYNC_LOG"; }

# Check if config file exists
if [[ ! -f "$CONFIG_FILE" ]]; then
    log "ERROR: Config file not found: $CONFIG_FILE"
    exit 1
fi

# Extract model.default from config.yaml
CURRENT_MODEL=$(python3 -c "
import yaml, sys
try:
    with open('$CONFIG_FILE', 'r') as f:
        config = yaml.safe_load(f)
    print(config.get('model', {}).get('default', ''))
except Exception as e:
    print('', file=sys.stderr)
    sys.exit(1)
" 2>/dev/null)

if [[ -z "$CURRENT_MODEL" ]]; then
    log "ERROR: Could not extract model.default from $CONFIG_FILE"
    exit 1
fi

log "Current model in config.yaml: $CURRENT_MODEL"

# Check if L1 memory exists
if [[ ! -f "$MEMORY_FILE" ]]; then
    log "ERROR: Memory file not found: $MEMORY_FILE"
    exit 1
fi

# Check if memory already has correct model
if grep -q "Gateway config:.*($CURRENT_MODEL)" "$MEMORY_FILE"; then
    log "L1 memory already up-to-date: $CURRENT_MODEL"
    exit 0
fi

log "Model changed — updating L1 memory"
log "New model: $CURRENT_MODEL"

# Use python to update the memory file safely
export CURRENT_MODEL
python3 << 'PYEOF'
import re, os

memory_file = os.path.expanduser("$MEMORY_FILE")
current_model = os.environ.get("CURRENT_MODEL", "")

with open(memory_file, 'r') as f:
    content = f.read()

# Find and replace the gateway config line
pattern = r'(Gateway config: [^)]+ \()[^)]+(\))'
replacement = fr'\1{current_model}\2'
new_content = re.sub(pattern, replacement, content)

if new_content != content:
    with open(memory_file, 'w') as f:
        f.write(new_content)
    print(f'Updated L1 memory with new model: {current_model}')
else:
    print('No change needed or pattern not found')
PYEOF

log "L1 memory sync complete"

# Commit to hermes-config repo if it exists
HERMES_DIR="$HOME/.hermes"
if [[ -d "$HERMES_DIR/.git" ]]; then
    cd "$HERMES_DIR"
    if git diff --quiet "$MEMORY_FILE" 2>/dev/null; then
        log "No changes to commit"
    else
        git add "$MEMORY_FILE"
        git commit -m "memory: auto-sync gateway model to $CURRENT_MODEL"
        git push 2>&1 | tee -a "$SYNC_LOG"
        log "Committed and pushed to hermes-config repo"
    fi
fi

exit 0
