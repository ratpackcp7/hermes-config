#!/usr/bin/env python3
"""Parse himalaya JSON output and print unread message IDs."""
import sys
import json

try:
    msgs = json.load(sys.stdin)
    # Filter for unread (no 'seen' flag)
    unread = [m for m in msgs if 'seen' not in m.get('flags', [])]
    for m in unread:
        print(m['id'])
except Exception:
    pass
