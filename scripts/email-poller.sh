#!/usr/bin/env bash
# Email poller for Bob's Gmail "Bob" folder
# Captures new messages to ~/wiki/raw/blogs/ and marks them read

set -euo pipefail

BOB_FOLDER="Bob"
ACCOUNT="ratpack"
WIKI_RAW_BLOGS="$HOME/wiki/raw/blogs"
TIMESTAMP=$(date +%Y-%m-%d)
LOG_FILE="$HOME/.hermes/cron/output/email-poller.log"

mkdir -p "$WIKI_RAW_BLOGS"
mkdir -p "$(dirname "$LOG_FILE")"

log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG_FILE"
}

log "=== Starting email poll ==="

# Get list of unread messages in Bob folder
MESSAGES=$(himalaya envelope list -a "$ACCOUNT" --folder "$BOB_FOLDER" --output json 2>/dev/null | python3 "$HOME/.hermes/scripts/parse-unread.py")

if [ -z "$MESSAGES" ]; then
    log "No new messages in $BOB_FOLDER folder"
    exit 0
fi

COUNT=$(echo "$MESSAGES" | wc -l)
log "Found $COUNT new message(s) in $BOB_FOLDER folder"

# Process each message
for MSG_ID in $MESSAGES; do
    log "Processing message ID: $MSG_ID"
    
    # Get message details
    MSG_JSON=$(himalaya message read "$MSG_ID" -a "$ACCOUNT" --folder "$BOB_FOLDER" --output json 2>/dev/null)
    
    # Extract subject, from, date
    SUBJECT=$(echo "$MSG_JSON" | python3 -c "import sys, json; m=json.load(sys.stdin); print(m.get('subject', 'no-subject'))" 2>/dev/null | tr '/' '-' | tr ' ' '-' | tr -d '[:cntrl:]')
    FROM=$(echo "$MSG_JSON" | python3 -c "import sys, json; m=json.load(sys.stdin); f=m.get('from', {}); print(f.get('addr', 'unknown'))" 2>/dev/null)
    DATE=$(echo "$MSG_JSON" | python3 -c "import sys, json; m=json.load(sys.stdin); print(m.get('date', '$TIMESTAMP'))" 2>/dev/null | cut -d' ' -f1)
    
    # Sanitize filename
    SAFE_SUBJECT=$(echo "$SUBJECT" | tr -d '?!@#$%^&*()[]{}|;:\"'\''<>' | cut -c1-50)
    FILENAME="$WIKI_RAW_BLOGS/${DATE}-${SAFE_SUBJECT}.md"
    
    # Avoid duplicates
    if [ -f "$FILENAME" ]; then
        log "Skipping duplicate: $FILENAME"
        continue
    fi
    
    # Export message as markdown
    {
        echo "---"
        echo "source_email: $FROM"
        echo "subject: $SUBJECT"
        echo "date: $DATE"
        echo "message_id: $MSG_ID"
        echo "fetched: $(date +%Y-%m-%dT%H:%M:%S%z)"
        echo "folder: $BOB_FOLDER"
        echo "---"
        echo ""
        echo "# $SUBJECT"
        echo ""
        echo "$MSG_JSON" | python3 -c "import sys, json; m=json.load(sys.stdin); print(m.get('text', 'No plain text body'))" 2>/dev/null
    } > "$FILENAME"
    
    log "Saved: $FILENAME"
    
    # Mark as read (add 'seen' flag)
    himalaya flag add "$MSG_ID" -a "$ACCOUNT" --folder "$BOB_FOLDER" --flag seen 2>&1 | tee -a "$LOG_FILE"
done

log "=== Email poll complete ==="

# Git commit new blog posts
cd "$HOME/wiki"
git add raw/blogs/*.md 2>/dev/null
git commit -m "email: capture new messages from Bob folder ($COUNT new)" 2>/dev/null || true
git push origin master 2>/dev/null || true

log "Wiki updated and pushed"
