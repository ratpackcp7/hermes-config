#!/usr/bin/env python3
"""Build a local project-status view from canonical project handoffs."""

from __future__ import annotations

import argparse
import json
import re
import tempfile
from datetime import datetime, timezone
from pathlib import Path


DEFAULT_INDEX = Path.home() / "AGENT_INDEX.md"
DEFAULT_JSON = Path.home() / ".local" / "state" / "bob" / "project-status.json"
DEFAULT_MARKDOWN = Path.home() / "project-status.md"
STALE_DAYS = 21


def canonical_roots(index_path: Path) -> list[dict[str, str]]:
    """Read only canonical project, Docker, and operational roots from AGENT_INDEX."""
    roots: list[dict[str, str]] = []
    section = ""
    for raw in index_path.read_text(encoding="utf-8", errors="replace").splitlines():
        if raw.startswith("## "):
            section = raw[3:].strip()
            continue
        if not raw.startswith("| ") or raw.startswith("| Name "):
            continue
        cells = [cell.strip() for cell in raw.strip("|").split("|")]
        if len(cells) < 2 or not cells[1].startswith("/"):
            continue
        if section not in {"Project Roots", "Docker Service Roots", "Top-Level Operational Roots"}:
            continue
        roots.append({"name": cells[0], "path": cells[1], "kind": section.removesuffix(" Roots").lower()})
    return roots


def section_lines(text: str, heading: str) -> list[str]:
    pattern = re.compile(rf"^#+\s+{re.escape(heading)}\s*$", re.IGNORECASE | re.MULTILINE)
    match = pattern.search(text)
    if not match:
        return []
    body = text[match.end():]
    body = re.split(r"^#+\s+", body, maxsplit=1, flags=re.MULTILINE)[0]
    return [line.strip().lstrip("- ").strip() for line in body.splitlines() if line.strip()]


def first_action(lines: list[str]) -> str | None:
    for line in lines:
        if line.lower() in {"none", "none.", "nothing actively in progress"}:
            continue
        if "~~" in line:
            continue
        if line.startswith(("```", "**", "_")) and line.endswith(("```", "**", "_")):
            continue
        return re.sub(r"^\d+[.)]\s*", "", line)[:280]
    return None


def parse_handoff(root: dict[str, str], now: datetime) -> dict:
    handoff = Path(root["path"]) / "HANDOFF.md"
    result = {**root, "handoff": str(handoff), "status": "missing", "next_step": None, "blocker": None}
    if not handoff.is_file():
        return result

    text = handoff.read_text(encoding="utf-8", errors="replace")
    age_days = int((now.timestamp() - handoff.stat().st_mtime) // 86400)
    result["updated_at"] = datetime.fromtimestamp(handoff.stat().st_mtime, timezone.utc).isoformat()
    result["age_days"] = age_days

    if re.search(r"^#+\s+Status:\s*RETIRED\b", text, re.IGNORECASE | re.MULTILINE):
        result["status"] = "retired"
        return result

    in_flight = first_action(section_lines(text, "In Flight"))
    next_step = first_action(section_lines(text, "Next Steps"))
    blocker = first_action(section_lines(text, "Blocked"))
    needs_chris = first_action(section_lines(text, "Needs Chris"))
    result["next_step"] = next_step or in_flight
    result["blocker"] = blocker or needs_chris

    explicit = re.search(r"^#+\s+Status:\s*([^\n]+)$", text, re.IGNORECASE | re.MULTILINE)
    explicit_value = explicit.group(1).strip().lower() if explicit else ""
    if age_days > STALE_DAYS:
        result["status"] = "stale"
    elif blocker or needs_chris or "blocked" in explicit_value:
        result["status"] = "blocked"
    elif in_flight and in_flight.lower() not in {"none", "none."}:
        result["status"] = "active"
    else:
        result["status"] = "unknown"
    return result


def build_status(index_path: Path, now: datetime | None = None) -> dict:
    now = now or datetime.now(timezone.utc)
    projects = [parse_handoff(root, now) for root in canonical_roots(index_path)]
    projects.sort(key=lambda item: (item["status"], item["name"].lower()))
    counts = {key: sum(p["status"] == key for p in projects) for key in ("active", "blocked", "stale", "unknown", "retired", "missing")}
    highlights = [p for p in projects if p["status"] in {"blocked", "active"} and p["next_step"]]
    return {
        "generated_at": now.isoformat(),
        "index": str(index_path),
        "stale_after_days": STALE_DAYS,
        "counts": counts,
        "highlights": highlights[:5],
        "projects": projects,
    }


def markdown_view(status: dict) -> str:
    counts = status["counts"]
    lines = [
        "# Project Status",
        "",
        f"Generated: {status['generated_at']}",
        f"Active: {counts['active']} | Blocked: {counts['blocked']} | Stale: {counts['stale']} | Unknown: {counts['unknown']}",
        "",
        "## Needs attention",
    ]
    highlights = status["highlights"]
    if not highlights:
        lines.append("- None identified from canonical handoffs.")
    for item in highlights:
        detail = item["blocker"] or item["next_step"]
        lines.append(f"- **{item['name']}** ({item['status']}): {detail}  ")
        lines.append(f"  Handoff: `{item['handoff']}`")
    lines.extend(["", "## All canonical handoffs", "", "| Project | Status | Age | Next step |", "|---|---|---:|---|"])
    for item in status["projects"]:
        age = f"{item.get('age_days', '—')}d" if item.get("age_days") is not None else "—"
        next_step = (item.get("next_step") or "—").replace("|", "\\|")
        lines.append(f"| {item['name']} | {item['status']} | {age} | {next_step} |")
    return "\n".join(lines) + "\n"


def atomic_write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as tmp:
        tmp.write(content)
        tmp.flush()
        tmp_name = tmp.name
    Path(tmp_name).replace(path)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--index", type=Path, default=DEFAULT_INDEX)
    parser.add_argument("--json", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--markdown", type=Path, default=DEFAULT_MARKDOWN)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    if not args.index.is_file():
        parser.error(f"index not found: {args.index}")
    status = build_status(args.index)
    rendered = markdown_view(status)
    if args.dry_run:
        print(rendered, end="")
        return 0
    atomic_write(args.json, json.dumps(status, indent=2) + "\n")
    atomic_write(args.markdown, rendered)
    print(f"project_status: {len(status['projects'])} canonical roots -> {args.markdown}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
