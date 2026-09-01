#!/usr/bin/env python3
"""Bob startup contract bundle — parser, builder, and verifier helpers."""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

HANDOFF_PATH = Path.home() / ".hermes" / "HANDOFF.md"
STAGED_RESTARTS_PATH = Path.home() / "staged-restarts.md"
SCRATCHPAD_CANONICAL = Path("/home/chris/bob-scratchpad.md")
SCRATCHPAD_LEGACY = Path("/home/chris/swap/bob-scratchpads/bob-scratchpad.md")
ACERSERVER_PATH = Path.home() / "ACERSERVER.md"
HERMES_ROOT = Path(__file__).resolve().parents[1]
BOB_PRINCIPLES_PATH = HERMES_ROOT / "bob-principles.md"
SESSION_START_SCRIPT = Path.home() / ".hermes" / "scripts" / "session-start.sh"
CONTRACT_DOC = Path.home() / ".hermes" / "STARTUP_CONTRACT.md"
PROJECT_STATUS_PATH = Path.home() / ".local" / "state" / "bob" / "project-status.json"

JSON_BEGIN = "--- BOB_STARTUP_BUNDLE_JSON ---"
JSON_END = "--- END BOB_STARTUP_BUNDLE_JSON ---"
MAX_INJECTION_CHARS = 2200
MAX_ACERSERVER_EXCERPT = 600
MAX_STARTUP_HIGHLIGHTS = 3

ACERSERVER_SECTIONS = {
    "## Server Facts",
    "## Active Agents",
    "## Source of Truth",
    "## Cron Summary",
}


def parse_staged_restarts(content: str | None = None, path: Path | None = None) -> dict[str, Any]:
    """Parse staged-restarts.md into pending/completed counts and warnings."""
    if content is None:
        src = path or STAGED_RESTARTS_PATH
        if not src.exists():
            return {
                "pending_count": 0,
                "pending_items": [],
                "completed_count": 0,
                "parse_warnings": ["staged-restarts file missing"],
            }
        content = src.read_text(encoding="utf-8", errors="replace")

    if not content.strip():
        return {
            "pending_count": 0,
            "pending_items": [],
            "completed_count": 0,
            "parse_warnings": [],
        }

    sections = re.split(r"(?=^## )", content, flags=re.MULTILINE)
    pending_items: list[dict[str, str]] = []
    completed_count = 0
    parse_warnings: list[str] = []

    for raw in sections:
        section = raw.strip()
        if not section.startswith("## "):
            continue

        header_line = section.splitlines()[0]
        title = header_line.lstrip("# ").strip()
        header_pending = "(PENDING)" in title.upper()
        status_pending = bool(re.search(r"\*\*Status:\*\*\s*PENDING", section, re.I))
        status_completed = bool(re.search(r"\*\*Status:\*\*\s*COMPLETED", section, re.I))
        has_completed_field = bool(re.search(r"\*\*Completed:\*\*", section, re.I))
        has_completed_line = bool(re.search(r"^COMPLETED\s+—", section, re.MULTILINE))
        header_completed = "COMPLETED" in title.upper()

        is_completed = (
            status_completed
            or has_completed_field
            or has_completed_line
            or (header_completed and not header_pending)
        )

        looks_pending = status_pending or header_pending

        if looks_pending and is_completed:
            parse_warnings.append(
                f"drift: section '{title}' has PENDING markers but completion evidence — treated as completed"
            )
            completed_count += 1
            continue

        if is_completed or (header_completed and not status_pending):
            completed_count += 1
            continue

        if looks_pending and not is_completed:
            service = _extract_field(section, "Service") or "unknown"
            reason = _extract_field(section, "Reason") or ""
            restart_method = _extract_field(section, "Restart method") or ""
            verification = _first_verification_command(section)
            pending_items.append(
                {
                    "title": re.sub(r"\s*\(PENDING\)\s*", "", title, flags=re.I).strip(),
                    "service": service,
                    "reason": reason,
                    "restart_method": restart_method,
                    "verification": verification,
                }
            )

    return {
        "pending_count": len(pending_items),
        "pending_items": pending_items,
        "completed_count": completed_count,
        "parse_warnings": parse_warnings,
    }


def _extract_field(section: str, field: str) -> str | None:
    m = re.search(rf"\*\*{re.escape(field)}:\*\*\s*(.+)", section)
    return m.group(1).strip() if m else None


def _first_verification_command(section: str) -> str:
    in_block = False
    for line in section.splitlines():
        if line.strip().startswith("**Post-restart verification"):
            in_block = True
            continue
        if in_block and line.strip().startswith("- "):
            return line.strip().lstrip("- ").split("→")[0].strip().strip("`")
    return ""


def parse_scratchpad(path: Path | None = None) -> dict[str, Any]:
    """Parse canonical scratchpad; report duplicate legacy path if present."""
    canonical = path or SCRATCHPAD_CANONICAL
    result: dict[str, Any] = {
        "path": str(canonical),
        "active": False,
        "summary": None,
        "duplicate_paths": [],
    }

    if SCRATCHPAD_LEGACY.exists() and SCRATCHPAD_LEGACY.resolve() != canonical.resolve():
        result["duplicate_paths"].append(str(SCRATCHPAD_LEGACY))

    if not canonical.exists():
        result["summary"] = "scratchpad file missing"
        return result

    text = canonical.read_text(encoding="utf-8", errors="replace")
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    inactive_markers = (
        "_No active dispatch tasks._",
        "No active dispatch",
        "_No active task_",
    )
    if not lines or any(m in text for m in inactive_markers):
        result["summary"] = "none"
        return result

    headings = [line[3:].strip().lower() for line in lines if line.startswith("## ")]
    if headings and all(heading.startswith("completed") for heading in headings):
        result["summary"] = "none"
        return result

    for line in lines:
        if line.startswith("#"):
            continue
        if line.startswith("_") and line.endswith("_"):
            continue
        result["active"] = True
        result["summary"] = line[:200]
        break

    if not result["active"]:
        result["summary"] = "none"
    return result


def extract_acerserver_excerpt(path: Path | None = None, max_chars: int = MAX_ACERSERVER_EXCERPT) -> str:
    """Extract key ACERSERVER sections up to max_chars."""
    src = path or ACERSERVER_PATH
    if not src.exists():
        return "(ACERSERVER.md not found — run regen-acerserver-md.sh)"

    lines = src.read_text(encoding="utf-8", errors="replace").splitlines()
    output: list[str] = []
    in_section = False
    for line in lines:
        if line.startswith("## "):
            in_section = line.strip() in ACERSERVER_SECTIONS
        if in_section:
            output.append(line)

    excerpt = "\n".join(output).strip()
    if len(excerpt) > max_chars:
        excerpt = excerpt[: max_chars - 48].rstrip() + "\n[truncated — read ~/ACERSERVER.md]"
    return excerpt or "(no orientation sections found)"


def extract_bob_principle_titles(path: Path | None = None) -> list[str]:
    """Return principle titles (P00N — ...) for pointer injection."""
    src = path or BOB_PRINCIPLES_PATH
    if not src.exists():
        return []
    titles: list[str] = []
    for line in src.read_text(encoding="utf-8", errors="replace").splitlines():
        m = re.match(r"^## (P\d{3}\s+—\s+.+)$", line.strip())
        if m:
            titles.append(m.group(1))
    return titles


def _memory_freshness_warning() -> str | None:
    config_file = Path.home() / ".hermes" / "config.yaml"
    memory_file = Path.home() / ".hermes" / "memories" / "MEMORY.md"
    try:
        import yaml

        config = yaml.safe_load(config_file.read_text())
        current_model = (config or {}).get("model", {}).get("default", "")
        if not current_model or not memory_file.exists():
            return None
        memory = memory_file.read_text()
        match = re.search(r"Gateway config: [^)]+", memory)
        if not match:
            return "No gateway config entry found in L1 memory"
        mem_model = re.search(r"\(([^)]+)\)", match.group(0))
        if mem_model and mem_model.group(1) != current_model:
            return (
                f"L1 memory model mismatch: config={current_model}, memory={mem_model.group(1)}"
            )
    except Exception:
        return None
    return None


def load_project_summary(path: Path | None = None) -> dict[str, Any]:
    """Load only the bounded status summary that belongs in a startup prompt."""
    src = path or PROJECT_STATUS_PATH
    if not src.exists():
        return {"available": False, "error": "project status has not been generated"}
    try:
        status = json.loads(src.read_text(encoding="utf-8"))
        return {
            "available": True,
            "generated_at": status.get("generated_at"),
            "counts": status.get("counts", {}),
            "highlights": status.get("highlights", [])[:MAX_STARTUP_HIGHLIGHTS],
            "full_view": str(Path.home() / "project-status.md"),
        }
    except (OSError, json.JSONDecodeError) as exc:
        return {"available": False, "error": str(exc)}


def build_bundle_json(
    *,
    snapshot_status: str = "local",
    handoff_updated: bool = False,
    session_id: str | None = None,
    staged_content: str | None = None,
) -> dict[str, Any]:
    """Assemble the startup bundle JSON object."""
    staged = parse_staged_restarts(content=staged_content)
    scratchpad = parse_scratchpad()
    bundle: dict[str, Any] = {
        "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "session_id": session_id,
        "handoff_path": str(HANDOFF_PATH),
        "handoff_updated": handoff_updated,
        "snapshot_status": snapshot_status,
        "acerserver_excerpt": extract_acerserver_excerpt(),
        "staged_restarts": staged,
        "scratchpad": {
            "path": scratchpad["path"],
            "active": scratchpad["active"],
            "summary": scratchpad["summary"],
        },
        "scratchpad_duplicates": scratchpad.get("duplicate_paths", []),
        "bob_principles_pointer": str(BOB_PRINCIPLES_PATH),
        "bob_principle_titles": extract_bob_principle_titles()[:12],
        "memory_freshness_warning": _memory_freshness_warning(),
        "project_summary": load_project_summary(),
        "startup_blocked": staged["pending_count"] > 0,
        "contract_doc": str(CONTRACT_DOC),
    }
    return bundle


def build_injection_text(bundle: dict[str, Any], session_id: str = "unknown") -> str:
    """Build a compact, blocker-first first-turn briefing (max 2200 chars)."""
    staged = bundle.get("staged_restarts", {})
    pending_count = staged.get("pending_count", 0)
    scratch = bundle.get("scratchpad", {})
    project_summary = bundle.get("project_summary", {})
    sid = bundle.get("session_id") or session_id

    if pending_count:
        pending_lines = [
            f"- {item.get('title', 'untitled')} ({item.get('service', 'unknown')}): "
            f"{item.get('reason', 'needs Chris approval')}"
            for item in staged.get("pending_items", [])[:3]
        ]
        pending_block = "STOP — pending restart work:\n" + "\n".join(pending_lines)
    else:
        pending_block = "Restart queue: clear."

    if project_summary.get("available"):
        counts = project_summary.get("counts", {})
        summary_lines = [
            f"Active projects: {counts.get('active', 0)} | blocked: {counts.get('blocked', 0)}",
        ]
        for item in project_summary.get("highlights", []):
            detail = item.get("blocker") or item.get("next_step") or "needs review"
            summary_lines.append(f"- {item.get('name', 'unknown')}: {detail}")
        project_block = "\n".join(summary_lines)
    else:
        project_block = "Project summary unavailable — read ~/project-status.md if needed."

    # Canon pointers live in the brief itself — ACERSERVER excerpt is capped at
    # MAX_ACERSERVER_EXCERPT and routinely truncates before ## Source of Truth.
    text = f"""# Bob startup brief

{pending_block}

Dispatch scratchpad: {'active — ' + str(scratch.get('summary')) if scratch.get('active') else 'none'}
{project_block}

Canon (do not invent a second):
- operating policy: ACP Rule 00-90 (rendered per harness)
- startup paths: /home/chris/bin/agent-bootstrap
- Bob ops preferences: ~/.hermes/bob-principles.md
- cp7-bridge infra sections only: ~/cp7-bridge/docs/agent-standards/AGENT-OPERATING-STANDARD.md

Host facts when needed:
{bundle.get('acerserver_excerpt', '')}

On demand: ~/project-status.md · ~/ACERSERVER.md

Before project work: read target AGENTS.md + HANDOFF.md. Do not report this brief unless a restart blocker exists.
"""

    if len(text) > MAX_INJECTION_CHARS:
        text = text[: MAX_INJECTION_CHARS - 20].rstrip() + "\n[truncated]"
    return text


def emit_json_block(bundle: dict[str, Any]) -> str:
    """Return machine-parseable JSON block for stdout."""
    return f"{JSON_BEGIN}\n{json.dumps(bundle, indent=2)}\n{JSON_END}"


def parse_json_block(stdout: str) -> dict[str, Any] | None:
    """Extract bundle JSON from session-start stdout."""
    if JSON_BEGIN not in stdout:
        return None
    try:
        payload = stdout.split(JSON_BEGIN, 1)[1].split(JSON_END, 1)[0].strip()
        return json.loads(payload)
    except (json.JSONDecodeError, IndexError):
        return None


def run_session_start(extra_argv: list[str] | None = None) -> tuple[str, dict[str, Any]]:
    """Run session-start.sh with --no-bundle-recurse; return stdout and bundle."""
    argv = [sys.executable, str(SESSION_START_SCRIPT), "--no-bundle-recurse"]
    if extra_argv:
        argv.extend(extra_argv)
    proc = subprocess.run(
        argv,
        capture_output=True,
        text=True,
        timeout=30,
        cwd=str(SESSION_START_SCRIPT.parent),
    )
    stdout = proc.stdout or ""
    if proc.stderr:
        stdout = stdout + "\n" + proc.stderr
    bundle = parse_json_block(stdout)
    if bundle is None:
        bundle = build_bundle_json(snapshot_status="failed", handoff_updated=False)
    return stdout, bundle


def build_startup_bundle(
    session_id: str,
    *,
    run_session_start_script: bool = True,
    snapshot_status: str | None = None,
) -> tuple[dict[str, Any], str]:
    """Build bundle + injection text for hook consumption."""
    if run_session_start_script:
        _, bundle = run_session_start()
        bundle["session_id"] = session_id
    else:
        bundle = build_bundle_json(
            snapshot_status=snapshot_status or "local",
            handoff_updated=HANDOFF_PATH.exists(),
            session_id=session_id,
        )
    injection = build_injection_text(bundle, session_id=session_id)
    return bundle, injection


def test_staged_restarts_parser() -> int:
    """Unit tests for staged-restarts parser. Returns exit code."""
    failures: list[str] = []

    live = parse_staged_restarts()
    drift_titles = [i.get("title", "") for i in live.get("pending_items", []) if "Bob role/dispatch" in i.get("title", "")]
    if drift_titles:
        failures.append(f"live file: drift section incorrectly pending: {drift_titles}")

    synthetic_pending = """
## 2099-01-01 — synthetic pending test

**Status:** PENDING
**Service:** test.service
**Reason:** unit test
**Restart method:** echo test

**Post-restart verification:**
- `echo ok` → expect PASS
"""
    syn = parse_staged_restarts(content=synthetic_pending)
    if syn["pending_count"] != 1:
        failures.append(f"synthetic pending: expected 1, got {syn['pending_count']}")

    drift = """
## 2026-06-16 — Bob role/dispatch boundary fix (PENDING)

**Service:** hermes-gateway.service
**Status:** COMPLETED — 2026-06-17 19:37 CDT
**Completed:** 2026-06-17 19:37 CDT
"""
    drift_result = parse_staged_restarts(content=drift)
    if drift_result["pending_count"] != 0:
        failures.append(f"drift case: expected pending_count=0, got {drift_result['pending_count']}")
    if not drift_result["parse_warnings"]:
        failures.append("drift case: expected parse_warnings")

    if failures:
        for f in failures:
            print(f"FAIL: {f}", file=sys.stderr)
        return 1

    print("test_staged_restarts_parser: PASS")
    print(f"  live pending_count={live['pending_count']}")
    print(f"  synthetic pending_count={syn['pending_count']}")
    print(f"  drift pending_count={drift_result['pending_count']}")
    return 0


def main() -> int:
    if "--test-staged-restarts" in sys.argv:
        return test_staged_restarts_parser()

    no_session = "--no-session-start" in sys.argv
    session_id = "verify"
    for i, arg in enumerate(sys.argv):
        if arg == "--session-id" and i + 1 < len(sys.argv):
            session_id = sys.argv[i + 1]

    bundle, injection = build_startup_bundle(
        session_id,
        run_session_start_script=not no_session,
    )
    print(emit_json_block(bundle))
    if "--print-injection" in sys.argv:
        print(injection)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
