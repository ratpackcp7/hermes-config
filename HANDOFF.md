# Server HANDOFF
Last loaded: 2026-08-02 21:49 

## Generated Homelab Snapshot
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
- Operating standard: ACP Rule 00-80 (rendered per harness, e.g. ~/.claude/CLAUDE.md, ~/.codex/AGENTS.md); startup contract: /home/chris/bin/agent-bootstrap (cp7-agent-stack)
- Infrastructure conventions (cp7-bridge scope only): /home/chris/cp7-bridge/docs/agent-standards/AGENT-OPERATING-STANDARD.md
- Recent infrastructure log: /home/chris/changelog.md
- Open work tracker: ~/todo.md (curated priorities) and ~/project-status.md (generated handoff view)

## Recent Activity


This file is a generated startup snapshot, not a durable task handoff. The
startup contract and the target project's AGENTS.md + HANDOFF.md remain
authoritative for active work.

## Before Starting Any Task
1. Read ~/project-status.md only for a complete cross-project view
2. Operating standard: ACP Rule 00-80; startup contract: /home/chris/bin/agent-bootstrap (cp7-agent-stack)
   For cp7-bridge infrastructure conventions only: cp7-bridge/docs/agent-standards/AGENT-OPERATING-STANDARD.md
3. Read target project AGENTS.md + HANDOFF.md before project work
- When done: run session-save.sh with a summary of what you did
