#!/usr/bin/env python3
"""Hermes orientation diagnostic.

This command is operator-facing output only. It is not injected into model
context and never writes tracked HANDOFF.md.
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
from datetime import datetime

PROJECT_STATUS_SCRIPT = os.path.expanduser("~/.hermes/scripts/project_status.py")

parser = argparse.ArgumentParser(description="Print a small Hermes orientation diagnostic")
parser.add_argument("--dry-run", action="store_true", help="Pass --dry-run through to the project-status refresh")
args = parser.parse_args()

project_status_args = [sys.executable, PROJECT_STATUS_SCRIPT]
if args.dry_run:
    project_status_args.append("--dry-run")
try:
    project_status = subprocess.run(project_status_args, capture_output=True, text=True, timeout=30)
except (OSError, subprocess.SubprocessError) as exc:
    project_status = None
    print(f"WARNING: project status refresh unavailable: {exc}", file=sys.stderr)

if project_status is not None and project_status.returncode:
    print(f"WARNING: project status refresh failed: {project_status.stderr.strip()}", file=sys.stderr)

now = datetime.now().astimezone().isoformat(timespec="seconds")
print("# Hermes orientation diagnostic")
print(f"Generated: {now}")
print()
print("This output is not automatic model context.")
print("Canonical agent context: /home/chris/projects/cp7-agent-stack/rails/agent-context-contract.md")
print("Canonical dispatch: /home/chris/cp7-bridge/docs/agent-dispatch/DISPATCH.md")
print("Project status (on demand): /home/chris/project-status.md")
