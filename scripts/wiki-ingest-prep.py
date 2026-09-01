#!/usr/bin/env python3
"""Wiki-ingest prep — load today's blogwatcher articles for Bob to evaluate and ingest.

Pre-script for the wiki-ingest cron. Reads the JSON saved by blogwatcher-digest.py
and outputs it as structured context for the LLM prompt.
"""
from __future__ import annotations
import json
import sys
from datetime import datetime
from pathlib import Path

POSTS_DIR = Path.home() / "wiki" / "raw" / "blogs" / "posts"


def main() -> int:
    today = datetime.now().strftime("%Y-%m-%d")
    json_file = POSTS_DIR / f"{today}.json"

    if not json_file.exists():
        print("---WIKI_INGEST_EMPTY---")
        print(f"No blogwatcher articles file for {today}.")
        return 0

    articles = json.loads(json_file.read_text())
    if not articles:
        print("---WIKI_INGEST_EMPTY---")
        print("Blogwatcher ran but found 0 new articles.")
        return 0

    print(f"# Wiki Ingest — {today}")
    print(f"**Articles to evaluate:** {len(articles)}")
    print()
    print("```json")
    print(json.dumps(articles, indent=2))
    print("```")
    print()
    print(f"_Source: {json_file}_")
    return 0


if __name__ == "__main__":
    sys.exit(main())
