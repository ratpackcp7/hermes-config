#!/usr/bin/env python3
"""
wifi-drop-monitor.py — Append new wpa_supplicant disconnect events to persistent log.
Run from cron (e.g., every 15 min) or manually.
"""
import subprocess, re, os, time, sys

LOG_FILE = os.path.expanduser("~/.hermes/logs/wifi-drops.log")
JOURNAL_SINCE = "5 minutes ago"  # overlap to avoid missed events

def get_last_ts():
    """Read last UNIX timestamp from log file."""
    try:
        with open(LOG_FILE) as f:
            lines = [l for l in f.readlines() if not l.startswith('#') and l.strip()]
            if not lines:
                return 0
            # Last field before comment may have newline; split on |
            last = lines[-1].strip()
            parts = last.split('|')
            if len(parts) >= 2:
                return int(parts[1])
    except Exception:
        pass
    return 0

def parse_disconnects(since):
    """Parse wpa_supplicant journal for new CTRL-EVENT-DISCONNECTED lines."""
    try:
        result = subprocess.run(
            ['journalctl', '-u', 'wpa_supplicant', '--since', since, '--no-pager'],
            capture_output=True, text=True, timeout=10
        )
        lines = result.stdout.splitlines()
    except Exception as e:
        print(f"[!] journalctl failed: {e}", file=sys.stderr)
        return []

    events = []
    for line in lines:
        if 'CTRL-EVENT-DISCONNECTED' not in line:
            continue
        # Parse: May 03 10:20:02 acerserver wpa_supplicant[1053]: ...
        m = re.match(
            r'^(\w+\s+\d+\s+\d+:\d+:\d+)\s+\S+\s+wpa_supplicant\[\d+\]:\s+.*reason=(\d+)(?:\s+locally_generated=(\d))?',
            line
        )
        if not m:
            continue
        ts_str = m.group(1)
        reason = m.group(2)
        local = m.group(4)  # will be '1' if locally_generated=1

        # Convert to UNIX timestamp
        try:
            struct = time.strptime(f"2026 {ts_str}", "%Y %b %d %H:%M:%S")
            unix_ts = int(time.mktime(struct))
        except:
            continue

        source = "acerserver" if local == "1" else "AP"
        iso = time.strftime("%Y-%m-%dT%H:%M:%S-05:00", struct)
        events.append((iso, unix_ts, reason, source))

    return events

def append_events(events, last_known_ts):
    new = [(iso, ts, r, s) for (iso, ts, r, s) in events if ts > last_known_ts]
    if not new:
        print(f"[+] No new drops since last log entry (ts={last_known_ts})")
        return 0

    with open(LOG_FILE, 'a') as f:
        for iso, ts, reason, source in new:
            f.write(f"{iso}|{ts}|{reason}|{source}|post-hardware-change\n")
    print(f"[+] Logged {len(new)} new drop(s):")
    for iso, ts, reason, source in new:
        print(f"    {iso} reason={reason} source={source}")
    return len(new)

if __name__ == '__main__':
    last_ts = get_last_ts()
    print(f"[*] Last logged drop: UNIX ts={last_ts}")
    events = parse_disconnects(JOURNAL_SINCE)
    print(f"[*] Found {len(events)} disconnect event(s) in journal since '{JOURNAL_SINCE}'")
    append_events(events, last_ts)
