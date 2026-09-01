#!/usr/bin/env bash
# cleanup-orphans.sh — Kill orphaned claude-agent/next-server from cc-loop runs
# Called by hermes-gateway.service ExecStopPre before gateway restart.
# Runs inside the gateway cgroup, so we CANNOT iterate cgroup.procs safely.

set +e

GATEWAY_PID=$(systemctl --user show hermes-gateway --property=MainPID --value)
echo "[cleanup-orphans] Gateway PID: $GATEWAY_PID"

# Kill orphaned next-server processes (from hermes-workspace, NOT the gateway)
# Only kill next-server processes whose parent is NOT a legitimate service
echo "[cleanup-orphans] Checking for orphaned next-server..."
for pid in $(pgrep -f "next-server" 2>/dev/null || true); do
    [ "$pid" = "$GATEWAY_PID" ] && continue
    parent=$(ps -o ppid= -p "$pid" 2>/dev/null | tr -d ' ')
    # Skip if parent is init (1) or the gateway - these are legitimate
    [ "$parent" = "1" ] && continue
    [ "$parent" = "$GATEWAY_PID" ] && continue
    # Check if parent is a known good service
    if [ -n "$parent" ] && kill -0 "$parent" 2>/dev/null; then
        parent_comm=$(cat /proc/$parent/comm 2>/dev/null || echo "unknown")
        # If parent is systemd, node, or another legit process, it's not orphaned
        case "$parent_comm" in
            systemd|node|npm|pnpm)
                echo "[cleanup-orphans] Skipping PID $pid (parent: $parent_comm - legitimate)"
                continue
                ;;
        esac
    fi
    echo "[cleanup-orphans] Killing orphaned next-server PID $pid (parent: $parent)"
    kill -TERM "$pid" 2>/dev/null
    sleep 0.5
    kill -KILL "$pid" 2>/dev/null
done

# Kill orphaned claude-agent processes
echo "[cleanup-orphans] Checking for orphaned claude-agent..."
for pid in $(pgrep -f "claude-agent" 2>/dev/null || true); do
    [ "$pid" = "$GATEWAY_PID" ] && continue
    if kill -0 "$pid" 2>/dev/null; then
        echo "[cleanup-orphans] Killing orphaned claude-agent PID $pid"
        kill -TERM "$pid" 2>/dev/null
        sleep 0.5
        kill -KILL "$pid" 2>/dev/null
    fi
done

# Kill stale tmux sessions from cc-loop
if command -v tmux &>/dev/null; then
    echo "[cleanup-orphans] Checking for stale tmux sessions..."
    sessions=$(tmux list-sessions -F "#{session_name}" 2>/dev/null || true)
    for session in $sessions; do
        if [[ "$session" == cc-loop* ]] || [[ "$session" == claude* ]]; then
            echo "[cleanup-orphans] Killing tmux session: $session"
            tmux kill-session -t "$session" 2>/dev/null
        fi
    done
fi

echo "[cleanup-orphans] Cleanup complete"
exit 0
