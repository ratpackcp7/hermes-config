#!/usr/bin/env python3
"""blogwatcher-cache-feeds — download UA-blocked RSS feeds to a local cache.

blogwatcher-cli sends `User-Agent: Go-http-client/1.1` which some sites
(Cloudflare-protected blogs like StrongDM) block. This script runs before
blogwatcher-digest.py, downloads the real feed with a browser UA, and
writes it to ~/swap/feeds/ where swap-browser.service (SimpleHTTPServer
on :8888) already serves it. blogwatcher-cli then fetches the cached copy
over HTTP, which is not UA-blocked because it's our own box.

The cached feeds are added to blogwatcher via their local URL:
  http://100.101.249.113:8888/feeds/<name>.xml

Usage:
  blogwatcher-cache-feeds.py           # refresh all cached feeds
  blogwatcher-cache-feeds.py --dry-run # show what would be fetched
"""
from __future__ import annotations
import argparse
import os
import sys
import urllib.request
from pathlib import Path

CACHE_DIR = Path.home() / "swap" / "feeds"
BROWSER_UA = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36"
)

# Feeds that need caching because blogwatcher-cli's UA is blocked at the origin
CACHED_FEEDS = [
    ("strongdm-blog", "https://www.strongdm.com/blog/rss.xml"),
]


def fetch(url: str) -> bytes:
    req = urllib.request.Request(url, headers={
        "User-Agent": BROWSER_UA,
        "Accept": "application/rss+xml, application/atom+xml, application/xml, text/xml, */*",
    })
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    CACHE_DIR.mkdir(parents=True, exist_ok=True)

    ok = 0
    failed = 0
    for name, url in CACHED_FEEDS:
        dest = CACHE_DIR / f"{name}.xml"
        if args.dry_run:
            print(f"would fetch {url} → {dest}")
            continue
        try:
            data = fetch(url)
            if len(data) < 100:
                print(f"  ✗ {name}: feed suspiciously small ({len(data)} bytes)", file=sys.stderr)
                failed += 1
                continue
            tmp = dest.with_suffix(".xml.tmp")
            tmp.write_bytes(data)
            tmp.rename(dest)
            print(f"  ✓ {name}: {len(data):,} bytes → {dest}")
            ok += 1
        except Exception as e:
            print(f"  ✗ {name}: {e}", file=sys.stderr)
            failed += 1

    print(f"\ncached: {ok} ok, {failed} failed")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
