#!/usr/bin/env python3
"""Blogwatcher daily digest — scan all feeds, emit new articles as markdown.

Called by a cron job's pre-run script. Output goes to stdout and is injected
into the cron prompt as context.

Behavior:
  1. Scan all feeds via blogwatcher-cli
  2. Print any new (unread) articles as a markdown digest, grouped by blog
  3. Mark all as read so tomorrow starts clean
  4. Emit ---BLOGWATCHER_EMPTY--- sentinel on empty days for [SILENT] detection
"""

from __future__ import annotations
import os
import re
import subprocess
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

HOME = Path.home()
BW_BIN = HOME / ".local" / "bin" / "blogwatcher-cli"
DB_PATH = os.environ.get("BLOGWATCHER_DB", str(HOME / "wiki" / "raw" / "blogs" / "blogwatcher-cli.db"))


def run_bw(*args: str, check: bool = False) -> tuple[int, str, str]:
    env = os.environ.copy()
    env["BLOGWATCHER_DB"] = DB_PATH
    env["BLOGWATCHER_SILENT"] = "1"
    r = subprocess.run(
        [str(BW_BIN), *args],
        capture_output=True,
        text=True,
        env=env,
        timeout=90,
    )
    if check and r.returncode != 0:
        raise RuntimeError(f"blogwatcher-cli {args} failed: {r.stderr}")
    return r.returncode, r.stdout, r.stderr


def scan_all() -> tuple[int, list[str]]:
    """Scan all feeds. Returns (feed_count, failed_feed_names)."""
    rc, out, err = run_bw("scan")
    combined = out + "\n" + err
    # Parse failed feeds: look for "  BlogName" followed by "    Error:"
    failed = []
    current_blog = None
    for line in combined.splitlines():
        m = re.match(r"^  ([A-Za-z].*?)\s*$", line)
        if m:
            current_blog = m.group(1).strip()
            continue
        if "Error:" in line and current_blog:
            failed.append(current_blog)
            current_blog = None
    return _count_feeds(), failed


def _count_feeds() -> int:
    rc, out, _ = run_bw("blogs")
    m = re.search(r"Tracked blogs \((\d+)\)", out)
    return int(m.group(1)) if m else 0


def list_unread() -> list[dict]:
    """Parse `blogwatcher-cli articles` output into structured records."""
    rc, out, _ = run_bw("articles")
    articles = []
    current: dict | None = None
    for line in out.splitlines():
        # Title line: "  [12] [new] Some title"
        m = re.match(r"^  \[(\d+)\]\s*(?:\[new\]\s*)?(.+)$", line)
        if m:
            if current:
                articles.append(current)
            current = {"id": m.group(1), "title": m.group(2).strip()}
            continue
        if current is None:
            continue
        ms = re.match(r"^\s+Blog:\s*(.+)$", line)
        if ms:
            current["blog"] = ms.group(1).strip()
            continue
        mu = re.match(r"^\s+URL:\s*(.+)$", line)
        if mu:
            current["url"] = mu.group(1).strip()
            continue
        mp = re.match(r"^\s+Published:\s*(.+)$", line)
        if mp:
            current["published"] = mp.group(1).strip()
            continue
    if current and "blog" in current:
        articles.append(current)
    return [a for a in articles if "blog" in a and "url" in a]


def mark_all_read() -> None:
    run_bw("read-all", "--yes")


def refresh_cached_feeds() -> tuple[int, int]:
    """Run blogwatcher-cache-feeds.py to refresh UA-blocked feeds into ~/swap/feeds/.

    Returns (ok_count, failed_count). Errors are non-fatal — the scan proceeds
    with whatever is currently in the cache.
    """
    cache_script = Path.home() / ".hermes" / "scripts" / "blogwatcher-cache-feeds.py"
    if not cache_script.exists():
        return 0, 0
    try:
        r = subprocess.run(
            ["python3", str(cache_script)],
            capture_output=True,
            text=True,
            timeout=120,
        )
        # Parse "cached: N ok, M failed" line
        for line in r.stdout.splitlines():
            m = re.search(r"cached:\s*(\d+)\s*ok,\s*(\d+)\s*failed", line)
            if m:
                return int(m.group(1)), int(m.group(2))
        return 0, 0
    except Exception:
        return 0, 0


def save_articles_json(articles: list[dict]) -> None:
    """Persist today's articles to JSON for downstream wiki-ingest cron."""
    import json
    posts_dir = Path(HOME / "wiki" / "raw" / "blogs" / "posts")
    posts_dir.mkdir(parents=True, exist_ok=True)
    today = datetime.now().strftime("%Y-%m-%d")
    out = posts_dir / f"{today}.json"
    out.write_text(json.dumps(articles, indent=2))


def main() -> int:
    now = datetime.now().strftime("%Y-%m-%d %H:%M %Z").strip()
    cache_ok, cache_failed = refresh_cached_feeds()
    feed_count, failed = scan_all()
    articles = list_unread()
    save_articles_json(articles)

    print(f"# Blogwatcher digest — {now}")
    print()
    header = f"**Feeds scanned:** {feed_count} | **New articles:** {len(articles)} | **Feed errors:** {len(failed)}"
    print(header)
    if cache_ok or cache_failed:
        print(f"**Cache refresh:** {cache_ok} ok, {cache_failed} failed (UA-blocked upstream feeds)")
    if failed:
        print(f"**Failed feeds:** {', '.join(failed)}")
    print()

    if not articles:
        print("_No new articles today._")
        print()
        print("---BLOGWATCHER_EMPTY---")
        return 0

    # Group by blog
    by_blog: dict[str, list[dict]] = defaultdict(list)
    for a in articles:
        by_blog[a["blog"]].append(a)

    for blog in sorted(by_blog.keys()):
        print(f"## {blog}")
        for a in by_blog[blog]:
            pub = a.get("published", "")
            pub_str = f" _({pub})_" if pub else ""
            print(f"- [{a['title']}]({a['url']}){pub_str}")
        print()

    print("---")
    print(f"_Database: `{DB_PATH}` | Source: blogwatcher-cli 0.1.1_")

    # Mark all as read so tomorrow starts clean
    try:
        mark_all_read()
    except Exception as e:
        print(f"\n_Warning: mark-all-read failed: {e}_", file=sys.stderr)

    return 0


if __name__ == "__main__":
    sys.exit(main())
