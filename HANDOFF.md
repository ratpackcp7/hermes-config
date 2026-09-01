# HANDOFF — hermes-config

Durable, hand-maintained task handoff for this project (`~/.hermes`, the
Bob/Hermes runtime-config repo) — same AGENTS.md + HANDOFF.md convention
used for every other project. `scripts/session-start.sh` never writes this file;
update it by hand when active work on this repo changes.

## Homelab Reference (snapshot as of last manual update)

Kept in sync by hand, not by session-start.sh. See `~/ACERSERVER.md` for the live version.
## Server Facts

- Host: acerserver
- OS: Ubuntu 24.04, headless, WiFi-only
- User: chris
- Tailscale IP: 100.101.249.113
- Domain: cp7.dev through Cloudflare Zero Trust tunnel
- Home Assistant: https://ha.cp7.dev
- GitHub: ratpackcp7
- Backup: Restic nightly at 2 AM CT to bosGame SFTP and Google Drive rclone

## Active Agents

- Bob: Hermes gateway agent. Primary enforcement and nightly audit runner.
- Codex: coding agent using /home/chris/.codex/rules/default.rules plus project AGENTS.md files.
- Claude: claude.ai / Claude Code. Advisory injection through user preferences, HANDOFF.md, and Claude Code hooks.

## Source of Truth

- Project/service map: /home/chris/AGENT_INDEX.md
- Live service inventory: /home/chris/projects/service-register/services.yaml
- Operating standard: ACP Rule 00-90 (rendered per harness); startup contract: /home/chris/bin/agent-bootstrap (cp7-agent-stack)
- Infrastructure conventions (cp7-bridge scope only): /home/chris/cp7-bridge/docs/agent-standards/AGENT-OPERATING-STANDARD.md
- Recent infrastructure log: /home/chris/changelog.md
- Open work: ~/todo.md is the primary global open-work surface (curated priorities). ~/project-status.md is a generated secondary cross-project view — never a canonical queue.

## Recent Activity


Homelab-wide facts (not project-specific) live in `~/ACERSERVER.md` and are
excerpted fresh into Bob's printed startup snapshot and startup-brief
injection on every session — never written here.

## Before Starting Any Task
1. Read ~/project-status.md only for a complete cross-project view
2. Operating standard: ACP Rule 00-90; startup contract: /home/chris/bin/agent-bootstrap (cp7-agent-stack)
   For cp7-bridge infrastructure conventions only: cp7-bridge/docs/agent-standards/AGENT-OPERATING-STANDARD.md
3. Read target project AGENTS.md + HANDOFF.md before project work
- When done: run session-save.sh with a summary of what you did
