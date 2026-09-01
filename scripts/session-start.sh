#!/usr/bin/env python3
"""Print Bob's generated startup orientation snapshot.

Never writes tracked HANDOFF.md: that file is this project's durable,
hand-maintained task handoff (see its own header). Homelab facts are
excerpted fresh from ~/ACERSERVER.md on every run; nothing here persists to
Git-tracked files.
"""
import argparse
import os
import subprocess
import sys
from datetime import datetime

HANDOFF_PATH = os.path.expanduser("~/.hermes/HANDOFF.md")
ACERSERVER_PATH = os.path.expanduser("~/ACERSERVER.md")
PROJECT_STATUS_SCRIPT = os.path.expanduser("~/.hermes/scripts/project_status.py")

parser = argparse.ArgumentParser(description="Print Bob's generated startup orientation snapshot")
parser.add_argument("--dry-run", action="store_true", help="Pass --dry-run through to the project-status refresh")
parser.add_argument(
    "--no-bundle-recurse",
    action="store_true",
    help="Emit the startup-bundle JSON for the startup-contract plugin",
)
args = parser.parse_args()

def extract_acerserver_sections(path):
    sections = {"## Server Facts", "## Active Agents", "## Source of Truth", "## Recent Activity"}
    if not os.path.exists(path):
        return "  (ACERSERVER.md not found — run regen-acerserver-md.sh)"
    output = []
    include = False
    with open(path, encoding="utf-8") as f:
        for line in f:
            if line.startswith("## "):
                include = line.strip() in sections
            if include:
                output.append(line.rstrip())
    return "\n".join(output[:80]) or "  (No startup sections found in ACERSERVER.md)"

summary = extract_acerserver_sections(ACERSERVER_PATH)

project_status_args = [sys.executable, PROJECT_STATUS_SCRIPT]
if args.dry_run:
    project_status_args.append("--dry-run")
project_status = subprocess.run(project_status_args, capture_output=True, text=True, timeout=30)
if project_status.returncode:
    print(f"WARNING: project status refresh failed: {project_status.stderr.strip()}")

now = datetime.now().strftime("%Y-%m-%d %H:%M %Z")
handoff = f"""# Bob Startup Snapshot
Generated: {now}

## Generated Homelab Snapshot
{summary}

This is a generated startup snapshot, printed only — it is never written to
tracked HANDOFF.md. The startup contract and the target project's AGENTS.md
+ HANDOFF.md remain authoritative for active work.

## Before Starting Any Task
1. Read ~/project-status.md only for a complete cross-project view
2. Operating standard: ACP Rule 00-90; startup contract: /home/chris/bin/agent-bootstrap (cp7-agent-stack)
   For cp7-bridge infrastructure conventions only: cp7-bridge/docs/agent-standards/AGENT-OPERATING-STANDARD.md
3. Read target project AGENTS.md + HANDOFF.md before project work
- When done: run session-save.sh with a summary of what you did
"""

handoff_updated = os.path.exists(HANDOFF_PATH)

print(handoff)

# Config freshness check — warn if L1 memory is stale
import re
CONFIG_FILE = os.path.expanduser("~/.hermes/config.yaml")
MEMORY_FILE = os.path.expanduser("~/.hermes/memories/MEMORY.md")
try:
    import yaml
    with open(CONFIG_FILE, 'r') as f:
        config = yaml.safe_load(f)
    current_model = config.get('model', {}).get('default', '')
    if current_model:
        with open(MEMORY_FILE, 'r') as f:
            memory = f.read()
        # Extract model from gateway config line in memory
        match = re.search(r'Gateway config: [^)]+', memory)
        if match:
            mem_model = re.search(r'\(([^)]+)\)', match.group(0))
            if mem_model and mem_model.group(1) != current_model:
                print(f"\n⚠️  WARNING: L1 memory model mismatch!")
                print(f"   Config.yaml: {current_model}")
                print(f"   L1 memory:   {mem_model.group(1)}")
                print(f"   Run: ~/.hermes/scripts/sync-gateway-config-to-memory.sh")
        else:
            print(f"\n⚠️  WARNING: No gateway config entry found in L1 memory")
except Exception as e:
    print(f"\n(Config freshness check skipped: {e})")

if args.no_bundle_recurse:
    from bob_startup_bundle import build_bundle_json, emit_json_block

    bundle = build_bundle_json(
        snapshot_status="local",
        handoff_updated=handoff_updated,
    )
    print(emit_json_block(bundle))
