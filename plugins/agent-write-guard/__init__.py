"""Hermes adapter for the shared agent write guard."""

from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import Any


GUARD_PATH = Path("/home/chris/scripts/agent-write-guard.py")
WRITE_TOOLS = {"edit", "patch", "patch_file", "write", "write_file"}


def _load_guard():
    spec = importlib.util.spec_from_file_location("agent_write_guard", GUARD_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("agent write guard unavailable")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _pre_tool_call(
    session_id: str = "",
    tool_name: str = "",
    args: dict[str, Any] | None = None,
    cwd: str = "",
    task_id: str = "",
    **kwargs: Any,
) -> dict[str, str] | None:
    if tool_name not in WRITE_TOOLS:
        return None
    try:
        guard = _load_guard()
        allowed, message = guard.check_hook(
            {
                "cwd": cwd or str(Path.cwd()),
                "session_id": session_id or task_id or "hermes-interactive",
                "tool_input": args or {},
            },
            "hermes",
        )
        return None if allowed else {"action": "block", "message": message}
    except Exception as exc:
        return {"action": "block", "message": f"Agent write guard failed closed: {exc}"}


def register(ctx: Any) -> None:
    ctx.register_hook("pre_tool_call", _pre_tool_call)
