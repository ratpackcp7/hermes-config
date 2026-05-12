#!/usr/bin/env python3
"""
Regenerates the Active Jobs section of ~/.hermes/CRON.md from jobs.json.
Safe to run any time — only replaces content between ## Active Jobs and ## Job Configuration Fields.
"""

import json
import os
import sys
from datetime import datetime

JOBS_JSON = os.path.expanduser("~/.hermes/cron/jobs.json")
CRON_MD   = os.path.expanduser("~/.hermes/CRON.md")

def model_label(job):
    model    = job.get("model") or "default (config)"
    provider = job.get("provider") or "default"
    enabled  = job.get("enabled", True)
    status   = "" if enabled else " *(disabled)*"
    return f"`{model}` via {provider}{status}"

def schedule_label(job):
    sched = job.get("schedule", {})
    if isinstance(sched, dict):
        return sched.get("expr") or sched.get("kind") or "unknown"
    return str(sched)

def build_active_jobs_section(jobs):
    lines = ["## Active Jobs", ""]
    lines.append("*Auto-generated from `jobs.json` — content reflects current jobs.json*")
    lines.append("")

    for job in jobs:
        name     = job.get("name", "unnamed")
        schedule = schedule_label(job)
        model    = model_label(job)
        prompt   = job.get("prompt", "")
        desc     = (prompt[:120] + "…") if len(prompt) > 120 else prompt
        deliver  = job.get("deliver", "unknown")
        runs     = job.get("repeat", {}).get("completed", 0) if isinstance(job.get("repeat"), dict) else 0
        last_run = job.get("last_run_at") or "never"
        last_status = job.get("last_status") or "—"
        script   = job.get("script")

        lines.append(f"### {name}")
        lines.append(f"- **Schedule:** `{schedule}`")
        lines.append(f"- **Model:** {model}")
        if script:
            lines.append(f"- **Pre-script:** `{script}`")
        lines.append(f"- **Delivers to:** {deliver}")
        lines.append(f"- **Runs completed:** {runs}")
        lines.append(f"- **Last run:** {last_run} | **Last status:** {last_status}")
        lines.append(f"- **What it does:** {desc}")
        lines.append("")

    return lines

def main():
    with open(JOBS_JSON) as f:
        data = json.load(f)
    jobs = data if isinstance(data, list) else data.get("jobs", [])

    with open(CRON_MD) as f:
        original = f.read()

    md_lines = original.splitlines()

    start_idx = next((i for i, l in enumerate(md_lines) if l.strip() == "## Active Jobs"), None)
    end_idx   = next((i for i, l in enumerate(md_lines) if l.strip() == "## Job Configuration Fields"), None)

    if start_idx is None or end_idx is None:
        print("ERROR: Could not find section markers in CRON.md", file=sys.stderr)
        sys.exit(1)

    new_section = build_active_jobs_section(jobs)
    new_lines   = md_lines[:start_idx] + new_section + md_lines[end_idx:]
    new_content = "\n".join(new_lines) + "\n"

    if new_content == original:
        print("CRON.md already up to date — no changes written.")
        return

    with open(CRON_MD, "w") as f:
        f.write(new_content)

    print(f"CRON.md updated — {len(jobs)} jobs written.")

if __name__ == "__main__":
    main()
