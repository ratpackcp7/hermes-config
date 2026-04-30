# L2 Facts — Warm Cache
Promoted from L1 memory. Searchable via grep. Not daily-use, but useful.

## Web Search
- Firecrawl paused (2026-04)
- SearXNG DDG CAPTCHAs — disable DDG, add request_timeout 5s
- Skill: searxng-ddg-captcha-fix

## Dashboard Services
- dashboard.cp7.dev (port 3090) = hub, replaces cp7hub
- bob.cp7.dev (port 3002) = workspace
- ntfy :8085 (Tailscale only)
- HA token at ~/projects/cp7-dashboard-tiles/.env.local

## Empower Audit Rules
- MK CC pattern: match by last4 + merchant
- Chase Freedom 6049 from 7718 (pair transactions)
- Reimbursements stay in original category
- Citi double-row: split transactions

## Swap Browser
- Port :8888 Tailscale (swap-browser.service)
- Serves ~/swap directory
- Charts → ~/swap/Hermes media/

## Restic Backup
- 2AM CT daily → bosGame (SFTP) + Google Drive (rclone)
- Script: ~/scripts/restic-backup.sh
- Wiki: concepts/restic-backup-to-gdrive.md
