"""
Activity tracker hook — writes agent state to status.json
for the CP7 Hub dashboard to read.

Events:
  agent:start  — context: platform, user_id, session_id, message
  agent:step   — context: platform, user_id, session_id, iteration, tool_names
  agent:end    — context: platform, user_id, session_id, message, response
"""

import json
import time
import os
from pathlib import Path

STATUS_FILE = Path(__file__).parent / "status.json"

# In-memory state (persists across events within a gateway process)
_state = {
    "status": "idle",
    "task": None,
    "platform": None,
    "session_id": None,
    "step_count": 0,
    "tools_used": [],
    "started_at": None,
    "last_updated": None,
    "duration_seconds": None,
}


def _write_status():
    """Atomically write state to status.json."""
    _state["last_updated"] = time.time()
    tmp = STATUS_FILE.with_suffix(".tmp")
    try:
        tmp.write_text(json.dumps(_state, indent=2))
        tmp.replace(STATUS_FILE)
    except Exception:
        pass


def handle(event_type: str, context: dict):
    if event_type == "gateway:startup":
        # Reset to idle on gateway restart so stale "working" state is cleared
        _state["status"] = "idle"
        _state["task"] = None
        _state["platform"] = None
        _state["session_id"] = None
        _state["step_count"] = 0
        _state["tools_used"] = []
        _state["started_at"] = None
        _state["duration_seconds"] = None
        _write_status()
        return

    if event_type == "agent:start":
        message = context.get("message", "") or ""
        # Truncate task summary to first 120 chars
        task = message[:120] + ("..." if len(message) > 120 else "")

        _state["status"] = "working"
        _state["task"] = task
        _state["platform"] = context.get("platform", "unknown")
        _state["session_id"] = context.get("session_id")
        _state["step_count"] = 0
        _state["tools_used"] = []
        _state["started_at"] = time.time()
        _state["duration_seconds"] = None
        _write_status()

    elif event_type == "agent:step":
        _state["step_count"] = context.get("iteration", _state["step_count"] + 1)

        # Track tools used this session
        tool_names = context.get("tool_names", [])
        if tool_names:
            for t in tool_names:
                if t and t not in _state["tools_used"]:
                    _state["tools_used"].append(t)

        _state["status"] = "working"
        if _state["started_at"]:
            _state["duration_seconds"] = round(time.time() - _state["started_at"], 1)
        _write_status()

    elif event_type == "agent:end":
        if _state["started_at"]:
            _state["duration_seconds"] = round(time.time() - _state["started_at"], 1)
        _state["status"] = "idle"
        _write_status()
