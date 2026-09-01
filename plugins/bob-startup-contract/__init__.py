"""Bob startup contract plugin — injects startup bundle on first turn."""

from __future__ import annotations

import sys
from pathlib import Path

_SCRIPTS = Path.home() / ".hermes" / "scripts"
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from bob_startup_bundle import build_startup_bundle  # noqa: E402

_pending: dict[str, str] = {}


def _on_session_start(session_id: str, **kwargs) -> None:
    _bundle, injection = build_startup_bundle(session_id, run_session_start_script=True)
    _pending[session_id] = injection


def _pre_llm_call(session_id: str, is_first_turn: bool = False, **kwargs) -> dict | None:
    if not is_first_turn:
        return None
    text = _pending.pop(session_id, None)
    if not text:
        return None
    return {"context": text}


def register(ctx) -> None:
    ctx.register_hook("on_session_start", _on_session_start)
    ctx.register_hook("pre_llm_call", _pre_llm_call)
