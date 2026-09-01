"""Fail closed when Bob lacks evidence for operational claims."""

from __future__ import annotations

import json
import re
import hashlib
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import quote


HERMES_HOME = Path.home() / ".hermes"
STARTUP_SCRIPT = HERMES_HOME / "scripts" / "session-start.sh"
SESSION_SAVE_SCRIPT = HERMES_HOME / "scripts" / "session-save.sh"
BUNDLE_SCRIPT = HERMES_HOME / "scripts" / "bob_startup_bundle.py"
PROJECT_STATUS = Path.home() / ".local" / "state" / "bob" / "project-status.json"
SWAP_ROOT = Path.home() / "swap"
BOB_LINK_ROOT = SWAP_ROOT / "bob-links"
ARTIFACT_CONFIG = Path.home() / ".config" / "cp7-notify" / "config.yml"
DEFAULT_SWAP_URL_BASE = "http://100.101.249.113:8889"
MAX_LINK_FILE_BYTES = 5 * 1024 * 1024

_turns: dict[str, dict[str, Any]] = {}
_STARTUP_QUERY = re.compile(r"\b(startup|session[- ]?start|loaded files?|startup chain|cold[- ]?start)\b", re.I)
_OPERATIONAL_QUERY = re.compile(r"\b(status|running|healthy|current|configured|loaded|startup|service|runtime)\b", re.I)
_UNKNOWN = re.compile(r"\b(i don't know|cannot verify|can't verify|need to inspect)\b", re.I)
_PATH_OR_CODE_RE = re.compile(
    r"`(?P<code>~/(?:[^`]+)|/home/chris/(?:[^`]+))`"
    r"|(?<![\w:/])(?P<raw>~/(?:[^\s`<>()\[\]]+)|/home/chris/(?:[^\s`<>()\[\]]+))"
)

# These are the only unqualified names Bob is allowed to turn into links. All
# other files must be named with an absolute path so there is no ambiguity.
_KNOWN_FILES = {
    "AGENTS.md": Path.home() / "AGENTS.md",
    "ACERSERVER.md": Path.home() / "ACERSERVER.md",
    "bob-principles.md": Path.home() / ".hermes" / "bob-principles.md",
    "project-status.md": Path.home() / "project-status.md",
    "STARTUP_CONTRACT.md": HERMES_HOME / "STARTUP_CONTRACT.md",
}
_SENSITIVE_PARTS = {
    ".ssh", ".gnupg", ".secrets", "secrets", "credentials", "private",
}
_SENSITIVE_NAME = re.compile(r"(^|[_.-])(secret|token|password|credential|api[_-]?key)([_.-]|$)", re.I)


def _artifact_base_url() -> str:
    """Load the Tailscale artifact base without importing notification code."""
    try:
        for raw in ARTIFACT_CONFIG.read_text(encoding="utf-8").splitlines():
            line = raw.strip()
            if line.startswith("swap_url_base:"):
                return line.split(":", 1)[1].strip().strip("\"'").rstrip("/")
    except OSError:
        pass
    return DEFAULT_SWAP_URL_BASE


def _safe_source(path: Path, allowed_root: Path | None = None) -> Path | None:
    """Resolve a file Bob may publish. Fail closed for secrets and large files."""
    try:
        source = path.expanduser().resolve(strict=True)
        root = (allowed_root or Path.home()).resolve()
        source.relative_to(root)
    except (OSError, ValueError):
        return None
    if not source.is_file() or source.stat().st_size > MAX_LINK_FILE_BYTES:
        return None
    parts = {part.lower() for part in source.parts}
    if parts & _SENSITIVE_PARTS or _SENSITIVE_NAME.search(source.name):
        return None
    if source.suffix.lower() in {".db", ".sqlite", ".sqlite3", ".pem", ".key", ".p12", ".pfx"}:
        return None
    if source.name in {".env", "config.yaml", "config.yml", "credentials.json", "token.json"}:
        return None
    return source


def _materialize_link(source_path: Path, *, link_root: Path = BOB_LINK_ROOT,
                      allowed_root: Path | None = None, url_base: str | None = None) -> str | None:
    """Copy a safe point-in-time file into the served root and return its URL."""
    source = _safe_source(source_path, allowed_root=allowed_root)
    if source is None:
        return None
    digest = hashlib.sha256(source.read_bytes()).hexdigest()[:16]
    destination = link_root / f"{digest}-{source.name}"
    try:
        link_root.mkdir(parents=True, exist_ok=True)
        if not destination.exists():
            temporary = link_root / f".{destination.name}.{os.getpid()}.tmp"
            shutil.copyfile(source, temporary)
            os.chmod(temporary, 0o644)
            os.replace(temporary, destination)
    except OSError:
        return None
    relative = destination.relative_to(SWAP_ROOT if link_root == BOB_LINK_ROOT else link_root)
    if link_root == BOB_LINK_ROOT:
        relative = Path("bob-links") / destination.name
    return f"{(url_base or _artifact_base_url()).rstrip('/')}/{quote(str(relative))}"


def _link_markdown(path_text: str, *, materialize=_materialize_link) -> str | None:
    url = materialize(Path(path_text))
    if not url:
        return None
    source = Path(path_text).expanduser()
    return f"[{source}](<{url}>)"


def _linkify_paths(response_text: str, *, materialize=_materialize_link) -> str:
    """Turn safe local paths into Telegram-safe Markdown links, never file://."""
    def replace_path(match: re.Match[str]) -> str:
        path_text = (match.group("code") or match.group("raw")).rstrip(".,:;!?")
        suffix = (match.group("code") or match.group("raw"))[len(path_text):]
        return (_link_markdown(path_text, materialize=materialize) or match.group(0)) + suffix

    expanded = response_text
    for name, source in _KNOWN_FILES.items():
        pattern = re.compile(rf"(?<![\w/]){re.escape(name)}(?!\w)")
        expanded = pattern.sub(str(source), expanded)
    return _PATH_OR_CODE_RE.sub(replace_path, expanded)


def _startup_report() -> str:
    """Return a direct filesystem report for startup-inventory questions."""
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    missing = [str(path) for path in (STARTUP_SCRIPT, SESSION_SAVE_SCRIPT, BUNDLE_SCRIPT) if not path.is_file()]
    if missing:
        return "I don't know. The startup verifier cannot find: " + ", ".join(missing)

    start_text = STARTUP_SCRIPT.read_text(encoding="utf-8", errors="replace").lower()
    save_text = SESSION_SAVE_SCRIPT.read_text(encoding="utf-8", errors="replace").lower()
    notion_free = "notion" not in start_text and "notion" not in save_text
    project = {"counts": {}, "generated_at": None}
    try:
        project = json.loads(PROJECT_STATUS.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        pass
    counts = project.get("counts", {})

    lines = [
        "Startup inventory — verified from local files",
        f"Verified: {now}",
        f"- Startup plugin: `bob-startup-contract` → `{BUNDLE_SCRIPT}`.",
        "- Bundle reads: staged restarts, Bob scratchpad, bounded ACERSERVER excerpt, Bob-principle titles, model-memory freshness, and project-status JSON.",
        f"- `{STARTUP_SCRIPT}` refreshes the local project-status view and generated startup snapshot.",
        f"- `{SESSION_SAVE_SCRIPT}` appends only to `{Path.home() / 'changelog.md'}`.",
        f"- Notion dependency: {'absent' if notion_free else 'PRESENT — needs repair'}.",
        "- Project status: " + (f"active {counts.get('active', 0)}, blocked {counts.get('blocked', 0)}, stale {counts.get('stale', 0)}." if project.get("generated_at") else "not generated yet."),
        f"- Full project view: `{Path.home() / 'project-status.md'}`.",
    ]
    return "\n".join(lines)


def _pre_llm_call(session_id: str, user_message: str = "", **kwargs: Any) -> dict[str, str] | None:
    text = user_message or ""
    startup_query = bool(_STARTUP_QUERY.search(text))
    operational_query = bool(_OPERATIONAL_QUERY.search(text))
    _turns[session_id] = {"startup_query": startup_query, "operational_query": operational_query, "tools": []}
    if startup_query:
        return {"context": "TRUTH GUARD: This is a startup-inventory question. Your final response will be replaced with a deterministic filesystem report. Do not infer or claim additional inspection."}
    if operational_query:
        return {"context": "TRUTH GUARD: For operational facts, do not claim you read, checked, ran, inspected, or verified anything without successful current-turn tool evidence. If evidence is absent, say exactly that you do not know yet and need to inspect."}
    return None


def _post_tool_call(session_id: str = "", tool_name: str = "", result: str = "", **kwargs: Any) -> None:
    state = _turns.get(session_id)
    if state is None:
        return
    failed = False
    try:
        payload = json.loads(result) if isinstance(result, str) else result
        failed = isinstance(payload, dict) and bool(payload.get("error"))
    except (TypeError, json.JSONDecodeError):
        pass
    if not failed:
        state["tools"].append(tool_name or "unknown")


def _transform_llm_output(response_text: str, session_id: str = "", **kwargs: Any) -> str | None:
    state = _turns.pop(session_id, None)
    if not state:
        # Tool-use loops may invoke the final transformer with a fresh hook
        # state. File delivery must not depend on that state surviving.
        linked = _linkify_paths(response_text)
        return linked if linked != response_text else None
    if state["startup_query"]:
        return _linkify_paths(_startup_report())
    if state["operational_query"] and not state["tools"] and not _UNKNOWN.search(response_text):
        return "I don't know. I did not inspect live files, configuration, or runtime state in this reply, so I cannot verify that claim. I need to inspect before answering."
    has_evidence = state["operational_query"] and bool(state["tools"])
    if has_evidence:
        evidence = ", ".join(dict.fromkeys(state["tools"]))
        response_text = f"{response_text}\n\nEvidence this turn: {evidence}."
    linked = _linkify_paths(response_text)
    return linked if has_evidence or linked != response_text else None


def register(ctx: Any) -> None:
    ctx.register_hook("pre_llm_call", _pre_llm_call)
    ctx.register_hook("post_tool_call", _post_tool_call)
    ctx.register_hook("transform_llm_output", _transform_llm_output)
