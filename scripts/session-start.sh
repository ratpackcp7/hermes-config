#!/usr/bin/env python3
"""
session-start.sh — Load homelab state from Notion, write server-level HANDOFF.md
Usage: python3 ~/.hermes/scripts/session-start.sh
"""
import urllib.request, urllib.error, json, sys, os
from datetime import datetime

NOTION_TOKEN = open(os.path.expanduser("~/.config/notion/api_key")).read().strip()
HOMELAB_PAGE_ID = "323f6863-72de-8163-9307-e15d1379e323"
BOB_PAGE_ID = "323f6863-72de-81d1-ab64-d9ed6697117e"
HANDOFF_PATH = os.path.expanduser("~/.hermes/HANDOFF.md")

def notion_get(endpoint):
    req = urllib.request.Request(
        f"https://api.notion.com/v1/{endpoint}",
        headers={
            "Authorization": f"Bearer {NOTION_TOKEN}",
            "Notion-Version": "2022-06-28",
        }
    )
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.loads(r.read())

def extract_text(blocks):
    lines = []
    for b in blocks.get("results", []):
        btype = b.get("type", "")
        content = b.get(btype, {})
        rich = content.get("rich_text", [])
        text = "".join(rt.get("plain_text", "") for rt in rich)
        if text.strip():
            lines.append(text.strip())
    return lines

try:
    homelab = notion_get(f"blocks/{HOMELAB_PAGE_ID}/children?page_size=50")
    lines = extract_text(homelab)
    summary = "\n".join(f"  {l}" for l in lines[:30])
except Exception as e:
    summary = f"  (Notion fetch failed: {e})"

now = datetime.now().strftime("%Y-%m-%d %H:%M %Z")
handoff = f"""# Server HANDOFF
Last loaded: {now}

## Homelab Hub
  https://notion.so/{HOMELAB_PAGE_ID.replace('-','')}

## Bob Page
  https://notion.so/{BOB_PAGE_ID.replace('-','')}

## Homelab State Snapshot
{summary}

## Before Starting Any Task
- Read this file + project CLAUDE.md + project HANDOFF.md
- When done: run session-save.sh with a summary of what you did
"""

with open(HANDOFF_PATH, "w") as f:
    f.write(handoff)

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
