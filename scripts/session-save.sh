#!/usr/bin/env python3
"""Append a completed Bob session summary to the local changelog."""
import sys, os
from datetime import datetime

if len(sys.argv) < 2 or not sys.argv[1].strip():
    print("Usage: session-save.sh \"Session summary\"")
    sys.exit(1)

CHANGELOG = os.path.expanduser("~/changelog.md")

summary = " ".join(sys.argv[1:]).strip()
now = datetime.now().strftime("%Y-%m-%d %H:%M")

# Append to changelog.md
with open(CHANGELOG, "a") as f:
    f.write(f"\n## {now} — Bob session\n{summary}\n")
print(f"Appended to {CHANGELOG}")

print(f"Summary: {summary}")
