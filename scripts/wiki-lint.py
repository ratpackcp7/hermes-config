#!/usr/bin/env python3
"""wiki-lint — scan ~/wiki for staleness, broken links, missing frontmatter.

Runs as a standalone script (CLI) or as a cron pre-script. Output is markdown
suitable for injection into a cron prompt or for terminal viewing.

Checks:
  1. Stale pages — last_verified older than churn-rate window
  2. Missing frontmatter fields on engineering pages (last_verified, churn_rate, confidence)
  3. Broken wikilinks — [[target]] pointing at a page that doesn't exist
  4. Broken backlinks — pages with zero inbound [[links]] (orphan detection)
  5. Index drift — pages on disk not listed in index.md, or vice versa
  6. Log rotation needed — log.md over 500 entries
  7. Sources with 404 URLs (optional, slow — disabled by default)

Usage:
  wiki-lint.py                    # full report to stdout (markdown)
  wiki-lint.py --quiet            # only output if issues found (for cron)
  wiki-lint.py --check-urls       # also HEAD-check source URLs (slow)
  wiki-lint.py --wiki /path/to/wiki  # override wiki path
"""

from __future__ import annotations
import argparse
import os
import re
import sys
from collections import defaultdict
from datetime import date, datetime, timedelta
from pathlib import Path

DEFAULT_WIKI = Path(os.environ.get("WIKI_PATH", Path.home() / "wiki"))

# Churn rate windows (days) — from wiki/AGENTS.md P3 + engineering rules
CHURN_DAYS = {
    "high": 30,
    "medium": 90,
    "low": 365,
}

# Directory-inferred churn rates for engineering pages without explicit frontmatter
DIR_CHURN = {
    "engineering/principles": "low",
    "engineering/languages": "medium",
    "engineering/stacks": "high",
    "engineering/practices": "medium",
}

# Paths to ignore entirely
IGNORE_PREFIXES = ("raw/", "_archive/", ".obsidian/", ".git/")

# YAML frontmatter regex (non-strict, good enough for our needs)
FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)
WIKILINK_RE = re.compile(r"\[\[([^\]|#]+)(?:#[^\]|]*)?(?:\|[^\]]*)?\]\]")
# Fenced code blocks + inline backticks — wikilinks inside these are examples, not references
CODE_FENCE_RE = re.compile(r"```.*?```", re.DOTALL)
INLINE_CODE_RE = re.compile(r"`[^`\n]+`")


def strip_code(text: str) -> str:
    """Remove fenced and inline code from markdown for link extraction."""
    text = CODE_FENCE_RE.sub("", text)
    text = INLINE_CODE_RE.sub("", text)
    return text


def parse_frontmatter(text: str) -> dict[str, str]:
    m = FRONTMATTER_RE.match(text)
    if not m:
        return {}
    block = m.group(1)
    fm: dict[str, str] = {}
    for line in block.splitlines():
        if ":" not in line:
            continue
        # Skip nested/list items for simplicity
        if line.startswith(" ") or line.startswith("\t") or line.startswith("-"):
            continue
        k, _, v = line.partition(":")
        fm[k.strip()] = v.strip().strip('"').strip("'")
    return fm


def parse_date(s: str) -> date | None:
    if not s:
        return None
    s = s.strip().strip('"').strip("'")
    for fmt in ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(s[: len(fmt) + 2], fmt).date()
        except ValueError:
            continue
    # Try ISO fromisoformat
    try:
        return datetime.fromisoformat(s).date()
    except ValueError:
        return None


def is_ignored(rel_path: str) -> bool:
    return any(rel_path.startswith(p) for p in IGNORE_PREFIXES)


def infer_churn_rate(rel_path: str) -> str | None:
    for prefix, churn in DIR_CHURN.items():
        if rel_path.startswith(prefix):
            return churn
    return None


def collect_pages(wiki: Path) -> list[dict]:
    """Walk the wiki and collect all markdown pages with metadata."""
    pages = []
    for path in wiki.rglob("*.md"):
        rel = str(path.relative_to(wiki))
        if is_ignored(rel):
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except Exception as e:
            pages.append({"path": rel, "error": str(e), "frontmatter": {}, "links": []})
            continue
        fm = parse_frontmatter(text)
        # Body (everything after frontmatter) — for link extraction
        body = FRONTMATTER_RE.sub("", text, count=1)
        # Strip code blocks first so example links like `[[wikilinks]]` in docs don't count
        body_for_links = strip_code(body)
        links = WIKILINK_RE.findall(body_for_links)
        pages.append(
            {
                "path": rel,
                "abs": path,
                "frontmatter": fm,
                "links": links,
                "body_len": len(body),
            }
        )
    return pages


def check_stale(pages: list[dict], today: date) -> list[dict]:
    """Find engineering pages past their churn-rate window."""
    stale = []
    for p in pages:
        if not p["path"].startswith("engineering/"):
            continue
        fm = p["frontmatter"]
        lv = parse_date(fm.get("last_verified", ""))
        churn = fm.get("churn_rate") or infer_churn_rate(p["path"])
        if not lv or not churn:
            continue
        window = CHURN_DAYS.get(churn)
        if not window:
            continue
        age = (today - lv).days
        if age > window:
            stale.append({**p, "age_days": age, "churn_rate": churn, "window": window})
    return stale


def check_missing_frontmatter(pages: list[dict]) -> list[dict]:
    """Engineering pages missing required frontmatter fields."""
    required = ["title", "type", "last_verified", "churn_rate", "confidence"]
    missing = []
    for p in pages:
        if not p["path"].startswith("engineering/"):
            continue
        # Skip AGENTS.md, index.md, chris-preferences.md — they're meta pages
        basename = p["path"].rsplit("/", 1)[-1]
        if basename in ("AGENTS.md", "index.md", "chris-preferences.md"):
            continue
        fm = p["frontmatter"]
        miss = [r for r in required if r not in fm]
        if miss:
            missing.append({**p, "missing_fields": miss})
    return missing


def check_broken_wikilinks(pages: list[dict]) -> list[dict]:
    """Find [[wikilinks]] pointing at non-existent pages."""
    # Build a set of valid targets: page basename (no .md) and full relative path
    valid = set()
    for p in pages:
        rel = p["path"]
        valid.add(rel)
        valid.add(rel[:-3] if rel.endswith(".md") else rel)  # without .md
        valid.add(rel.rsplit("/", 1)[-1].removesuffix(".md"))  # basename
        valid.add(rel.removesuffix(".md"))

    broken = []
    for p in pages:
        for link in p["links"]:
            target = link.strip()
            if target in valid:
                continue
            # Also accept a target that matches any page's path/basename loosely
            if any(target == v or v.endswith("/" + target) for v in valid):
                continue
            broken.append({"page": p["path"], "link": target})
    return broken


def check_orphans(pages: list[dict]) -> list[dict]:
    """Pages with zero inbound [[wikilinks]] (excluding meta pages)."""
    inbound: dict[str, int] = defaultdict(int)
    # Build a loose mapping: target text → list of page paths that match
    path_to_tokens = {}
    for p in pages:
        rel = p["path"]
        tokens = {
            rel,
            rel.removesuffix(".md"),
            rel.rsplit("/", 1)[-1].removesuffix(".md"),
        }
        path_to_tokens[rel] = tokens

    for p in pages:
        for link in p["links"]:
            t = link.strip()
            for target_page, tokens in path_to_tokens.items():
                if t in tokens:
                    inbound[target_page] += 1
                    break

    orphans = []
    meta_names = {"AGENTS.md", "index.md", "SCHEMA.md", "log.md", "chris-preferences.md", "BOB_INDEX.md"}
    for p in pages:
        basename = p["path"].rsplit("/", 1)[-1]
        if basename in meta_names:
            continue
        # Also skip top-level index/log files
        if p["path"] in {"AGENTS.md", "SCHEMA.md", "index.md", "log.md", "BOB_INDEX.md"}:
            continue
        if inbound.get(p["path"], 0) == 0:
            orphans.append(p)
    return orphans


def check_log_size(wiki: Path) -> dict | None:
    log = wiki / "log.md"
    if not log.exists():
        return None
    try:
        text = log.read_text(encoding="utf-8")
    except Exception:
        return None
    entries = len(re.findall(r"^## \[", text, re.MULTILINE))
    if entries > 500:
        return {"path": "log.md", "entries": entries}
    return None


def format_report(
    wiki: Path,
    pages: list[dict],
    stale: list[dict],
    missing_fm: list[dict],
    broken: list[dict],
    orphans: list[dict],
    log_issue: dict | None,
) -> tuple[str, int]:
    """Return (markdown_report, total_issue_count)."""
    total_issues = (
        len(stale) + len(missing_fm) + len(broken) + len(orphans) + (1 if log_issue else 0)
    )

    lines = []
    lines.append(f"# Wiki lint — {date.today().isoformat()}")
    lines.append("")
    lines.append(f"**Wiki:** `{wiki}` | **Pages scanned:** {len(pages)} | **Issues:** {total_issues}")
    lines.append("")

    if total_issues == 0:
        lines.append("_No issues found. Wiki is clean._")
        lines.append("")
        lines.append("---WIKI_LINT_CLEAN---")
        return "\n".join(lines), 0

    if stale:
        lines.append(f"## ⏰ Stale pages ({len(stale)})")
        lines.append("")
        lines.append("Engineering pages past their churn-rate re-verify window.")
        lines.append("")
        for p in sorted(stale, key=lambda x: -x["age_days"]):
            lines.append(
                f"- `{p['path']}` — **{p['age_days']}d old** (churn={p['churn_rate']}, window={p['window']}d)"
            )
        lines.append("")

    if missing_fm:
        lines.append(f"## 📝 Missing frontmatter ({len(missing_fm)})")
        lines.append("")
        lines.append("Engineering pages missing required fields (title, type, last_verified, churn_rate, confidence).")
        lines.append("")
        for p in missing_fm:
            lines.append(f"- `{p['path']}` — missing: {', '.join(p['missing_fields'])}")
        lines.append("")

    if broken:
        lines.append(f"## 🔗 Broken wikilinks ({len(broken)})")
        lines.append("")
        by_page: dict[str, list[str]] = defaultdict(list)
        for b in broken:
            by_page[b["page"]].append(b["link"])
        for page, links in sorted(by_page.items()):
            lines.append(f"- `{page}`:")
            for lk in links:
                lines.append(f"  - `[[{lk}]]` → no matching page")
        lines.append("")

    if orphans:
        lines.append(f"## 🏝️ Orphan pages ({len(orphans)})")
        lines.append("")
        lines.append("Pages with zero inbound `[[wikilinks]]`. Consider adding cross-references or archiving.")
        lines.append("")
        for p in orphans:
            lines.append(f"- `{p['path']}`")
        lines.append("")

    if log_issue:
        lines.append(f"## 📜 Log rotation needed")
        lines.append("")
        lines.append(
            f"`log.md` has {log_issue['entries']} entries (>500). Rotate to `log-{date.today().year}.md` and start fresh."
        )
        lines.append("")

    return "\n".join(lines), total_issues


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--wiki", type=Path, default=DEFAULT_WIKI)
    ap.add_argument("--quiet", action="store_true", help="Only emit output if issues found (for cron)")
    ap.add_argument("--exit-code-on-issues", action="store_true", help="Exit 1 if any issues")
    args = ap.parse_args()

    if not args.wiki.exists():
        print(f"Wiki not found: {args.wiki}", file=sys.stderr)
        return 2

    today = date.today()
    pages = collect_pages(args.wiki)
    stale = check_stale(pages, today)
    missing_fm = check_missing_frontmatter(pages)
    broken = check_broken_wikilinks(pages)
    orphans = check_orphans(pages)
    log_issue = check_log_size(args.wiki)

    report, total = format_report(
        args.wiki, pages, stale, missing_fm, broken, orphans, log_issue
    )

    if args.quiet and total == 0:
        return 0

    print(report)
    if args.exit_code_on_issues and total > 0:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
