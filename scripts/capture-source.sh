#!/usr/bin/env bash
# capture-source.sh — Capture a primary source into ~/wiki/raw/
#
# Usage:
#   capture-source.sh docs <url> <tool> <version> [slug]
#   capture-source.sh changelog <url> <tool> <version>
#   capture-source.sh blog <url> <author> [slug]
#   capture-source.sh correction <topic> <content-file>
#
# Writes a properly-frontmattered file into the right raw/ subdirectory.
# Fetches URLs via Firecrawl if FIRECRAWL_API_URL is set, otherwise falls back
# to markdown via w3m or curl+pandoc.
#
# Examples:
#   capture-source.sh docs https://nextjs.org/docs/app nextjs 16.2 app-router
#   capture-source.sh changelog https://nextjs.org/blog/next-16 nextjs 16.0
#   capture-source.sh blog https://simonwillison.net/2026/apr/05/some-post/ simon-willison
#   capture-source.sh correction tuya-10x-bug /tmp/correction.md
#
# Exit codes:
#   0 - success
#   1 - usage error
#   2 - fetch error
#   3 - write error
#
# This script is called by:
#   - llm-wiki skill (via mcp_terminal)
#   - blogwatcher cron (suggestion #3, when built)
#   - Chris directly from the shell
#
# Author: Bob
# Created: 2026-04-08

set -euo pipefail

WIKI="${WIKI_PATH:-$HOME/wiki}"
RAW="$WIKI/raw"
LOG="$WIKI/log.md"

# Default Firecrawl endpoint on acerserver. Override with env var if needed.
: "${FIRECRAWL_API_URL:=http://127.0.0.1:3200}"
export FIRECRAWL_API_URL

# ---------- helpers ----------

die() {
  echo "ERROR: $*" >&2
  exit "${2:-1}"
}

usage() {
  sed -n '3,20p' "$0" | sed 's/^# \{0,1\}//'
  exit 1
}

# Slugify: lowercase, replace non-alnum with dashes, squeeze repeats, trim.
slugify() {
  local s="$1"
  s="${s,,}"
  s="${s//[^a-z0-9]/-}"
  s="$(echo "$s" | tr -s '-' | sed 's/^-//;s/-$//')"
  [[ -z "$s" ]] && s="untitled"
  echo "$s"
}

# Extract slug from a URL's last path segment if no slug was provided.
slug_from_url() {
  local url="$1"
  local last
  last="$(echo "$url" | sed -E 's#/+$##; s#.*/##; s#\?.*$##; s#\#.*$##')"
  [[ -z "$last" ]] && last="index"
  slugify "$last"
}

# ISO 8601 timestamp with local timezone (e.g., 2026-04-08T11:30:00-05:00)
iso_now() {
  date -u '+%Y-%m-%dT%H:%M:%SZ'
}

# Just the date (YYYY-MM-DD) in local time.
date_today() {
  date '+%Y-%m-%d'
}

# Ensure directory exists.
ensure_dir() {
  mkdir -p "$1" || die "failed to create $1" 3
}

# Fetch a URL and return markdown on stdout.
# Priority: Firecrawl (if FIRECRAWL_API_URL set) > pandoc+curl > w3m > curl raw
fetch_markdown() {
  local url="$1"

  # Firecrawl (self-hosted at 127.0.0.1:3200 on acerserver)
  if [[ -n "${FIRECRAWL_API_URL:-}" ]]; then
    local resp
    resp="$(curl -sS -X POST "$FIRECRAWL_API_URL/v1/scrape" \
      -H "Content-Type: application/json" \
      -d "$(jq -n --arg url "$url" '{url: $url, formats: ["markdown"]}')" 2>/dev/null || true)"
    if [[ -n "$resp" ]]; then
      local md
      md="$(echo "$resp" | jq -r '.data.markdown // empty' 2>/dev/null || true)"
      if [[ -n "$md" ]]; then
        echo "$md"
        return 0
      fi
    fi
    echo "WARN: firecrawl fetch failed, falling back" >&2
  fi

  # pandoc + curl
  if command -v pandoc >/dev/null 2>&1 && command -v curl >/dev/null 2>&1; then
    local html
    html="$(curl -sSL -H "User-Agent: Mozilla/5.0 (bob-capture)" "$url" 2>/dev/null || true)"
    if [[ -n "$html" ]]; then
      echo "$html" | pandoc -f html -t markdown_strict --wrap=none 2>/dev/null && return 0
    fi
  fi

  # w3m fallback
  if command -v w3m >/dev/null 2>&1; then
    w3m -dump "$url" 2>/dev/null && return 0
  fi

  # curl raw as absolute last resort
  curl -sSL -H "User-Agent: Mozilla/5.0 (bob-capture)" "$url" 2>/dev/null || die "all fetchers failed for $url" 2
}

# Append one line to wiki/log.md
log_capture() {
  local content_type="$1"
  local dest="$2"
  local source_url="$3"
  local today
  today="$(date_today)"
  ensure_dir "$WIKI"
  [[ ! -f "$LOG" ]] && printf '# Wiki Log\n\n' > "$LOG"
  {
    echo "## [$today] ingest | $content_type"
    echo "- dest: ${dest#$HOME/}"
    echo "- source: $source_url"
  } >> "$LOG"
}

# ---------- content-type handlers ----------

capture_docs() {
  local url="$1"
  local tool="$2"
  local version="$3"
  local slug="${4:-$(slug_from_url "$url")}"

  [[ -z "$url" || -z "$tool" || -z "$version" ]] && die "docs needs url, tool, version" 1

  local dir="$RAW/docs/$(slugify "$tool")/$(slugify "$version")"
  ensure_dir "$dir"
  local dest="$dir/$(slugify "$slug").md"

  echo "→ fetching $url" >&2
  local body
  body="$(fetch_markdown "$url")"
  [[ -z "$body" ]] && die "fetched empty body from $url" 2

  local now
  now="$(iso_now)"
  cat > "$dest" <<EOF
---
source_url: $url
fetched: $now
fetcher: capture-source.sh
content_type: docs
tool: $tool
version: "$version"
slug: $slug
---

$body
EOF

  log_capture "docs" "$dest" "$url"
  echo "✓ captured: $dest"
}

capture_changelog() {
  local url="$1"
  local tool="$2"
  local version="$3"

  [[ -z "$url" || -z "$tool" || -z "$version" ]] && die "changelog needs url, tool, version" 1

  local dir="$RAW/changelogs/$(slugify "$tool")"
  ensure_dir "$dir"
  local dest="$dir/$(slugify "$version").md"

  echo "→ fetching $url" >&2
  local body
  body="$(fetch_markdown "$url")"
  [[ -z "$body" ]] && die "fetched empty body from $url" 2

  local now
  now="$(iso_now)"
  cat > "$dest" <<EOF
---
source_url: $url
fetched: $now
fetcher: capture-source.sh
content_type: changelog
tool: $tool
version: "$version"
---

$body
EOF

  log_capture "changelog" "$dest" "$url"
  echo "✓ captured: $dest"
}

capture_blog() {
  local url="$1"
  local author="$2"
  local slug="${3:-$(slug_from_url "$url")}"

  [[ -z "$url" || -z "$author" ]] && die "blog needs url, author" 1

  local today
  today="$(date_today)"
  local dir="$RAW/blogs"
  ensure_dir "$dir"
  local dest="$dir/${today}-$(slugify "$author")-$(slugify "$slug").md"

  echo "→ fetching $url" >&2
  local body
  body="$(fetch_markdown "$url")"
  [[ -z "$body" ]] && die "fetched empty body from $url" 2

  local now
  now="$(iso_now)"
  cat > "$dest" <<EOF
---
source_url: $url
fetched: $now
fetcher: capture-source.sh
content_type: blog
author: $author
slug: $slug
published_date: unknown
---

$body
EOF

  log_capture "blog" "$dest" "$url"
  echo "✓ captured: $dest"
  echo ""
  echo "REMINDER: blog posts are attention signals, not knowledge."
  echo "Next step: identify the primary source this post discusses and capture that too:"
  echo "  capture-source.sh docs <primary-source-url> <tool> <version>"
}

capture_correction() {
  local topic="$1"
  local content_file="$2"

  [[ -z "$topic" || -z "$content_file" ]] && die "correction needs topic, content-file" 1
  [[ ! -r "$content_file" ]] && die "content file not readable: $content_file" 1

  local today
  today="$(date_today)"
  local dir="$RAW/corrections"
  ensure_dir "$dir"
  local dest="$dir/${today}-$(slugify "$topic").md"

  local body
  body="$(cat "$content_file")"

  local now
  now="$(iso_now)"
  cat > "$dest" <<EOF
---
correction_date: $today
captured_at: $now
topic: $topic
content_type: correction
---

$body
EOF

  log_capture "correction" "$dest" "local-input"
  echo "✓ captured: $dest"
  echo ""
  echo "REMINDER: also update ~/wiki/engineering/chris-preferences.md"
  echo "with the distilled preference, referencing this correction file."
}

# ---------- dispatch ----------

[[ $# -lt 1 ]] && usage

mode="$1"
shift

case "$mode" in
  docs)
    capture_docs "$@"
    ;;
  changelog)
    capture_changelog "$@"
    ;;
  blog)
    capture_blog "$@"
    ;;
  correction)
    capture_correction "$@"
    ;;
  -h|--help|help)
    usage
    ;;
  *)
    die "unknown mode: $mode (use: docs | changelog | blog | correction)" 1
    ;;
esac
