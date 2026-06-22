# Server HANDOFF
Last loaded: 2026-05-11 16:13 

## Homelab Hub
  https://notion.so/323f686372de81639307e15d1379e323

## Bob Page
  https://notion.so/323f686372de81d1ab64d9ed6697117e

## Homelab State Snapshot
  Purpose
  Acer server, Bob/Hermes agent, cron jobs, bosGame as always-on Windows server, Claude Desktop MCP config, dashboard.cp7.dev, and Empower finance app.
  Context
  Acer Server
  Hardware: Acer Swift 16 AI (SF16-51T), Intel Core Ultra 7 258V, 32GB LPDDR5X, 1TB NVMe, Intel Arc 140V iGPU, headless (cracked display)
  OS: Ubuntu 24.04.4 LTS, Kernel 6.17.0-14-generic (HWE)
  User: chris
  Tailscale: 100.101.249.113 (SSH enabled)
  Domain: cp7.dev (Cloudflare Registrar)
  Tunnel: cloudflared systemd service, auto-starts
  Published routes: glances, studio, search, dashboard, homarr, tgwebhook, abs, qtorrent, assets, mcp, finance, actual, roster (14 total)
  Route management: cf-tunnel.sh — API-based list/add/remove via bridge (no dashboard needed)
  Access: Cloudflare Access (Zero Trust) — wildcard *.cp7.dev, Google OAuth + email OTP
  Key software: Hermes Agent (Bob), Docker 29.3.0, Ollama 0.17.7 (CPU-only, qwen3 models), Glances, SearXNG, Network Monitoring Stack (Prometheus/Blackbox/Node-Exporter/Speedtest at /home/chris/docker/network-monitoring/, Tailscale-only at :9091), Tautulli (Plex analytics at /home/chris/docker/tautulli/, Tailscale-only at :8181), socat Grafana proxy (Tailscale-only at :3000)
  Dormant: Nginx Proxy Manager, Authentik 2025.12.4
  Security: UFW Tailscale-only (100.64.0.0/10), SSH password auth disabled, passwordless sudo still enabled (to be removed)
  Detailed specs: See Acer sub-pages (CurrentState, Bob, Agents/Cron, InstallHistory)
  bosGame Desktop
  Hardware: Intel N100 (800 MHz), 16GB RAM (15.7 usable), x64
  OS: Windows 11 Pro 25H2 (build 26200.8037)
  Tailscale: 100.107.88.108
  Role: Secondary / always-on Windows machine
  MCP status: Still needs uv installed and claude_desktop_config.json created
  Claude Desktop MCP
  Filesystem MCP: Allowed paths include C:UsersratpaDownloadsNew_folder, C:UsersratpaDocumentsCoWork, C:Usersratpa
  HA MCP: ha-mcp via uvx + long-lived token (claude-desktop). Official OAuth broken since Dec 2025.
  Open Questions / Blockers
  WiFi BSSID flap — RESOLVED (2026-04-30). BSSID pinned to F0:72:EA:54:F9:8D, roaming between pucks eliminated. NEW ISSUE: disconnects still occur (reason=3/4, locally_generated=1, 71 in 24h) — link stability investigation needed.
  HA skill hang — Bob hung on first HA query (2+ min, no response). Cause unknown.
  bosGame MCP config — needs uv install + claude_desktop_config.json

## Recent Changes (2026-06-21)
- **Bob Contract Pack v1 — SOUL.md Rule #3**: Added binding Rule #3 to SOUL.md on branch `feature/bob-contract-pack-v1`. Points Bob at runtime helpers from ratpackcp7/home-config#20 (`bob-dispatch route`, `bob-spec-new`, `bob-route-smoke`, `pif`, `bob-closeout-summary`, `bob-dirty-report`, `bob-artifact-url`, `bob-pr-inspect`, `bob-emp-deploy-check`). Cursor is now default build agent (OC sidelined). PR pending against master.

## Recent Changes (2026-05-12)
- **cron-doc-drift-check fix**: `regen-cron-doc.py` had two bugs causing hourly false-positive pings:
  1. Volatile timestamp (`datetime.now()`) in generated output
  2. Volatile runtime fields (`last_run_at`, `last_status`, `runs completed`) included in output — these change every cron run
  
  Removed both. `CRON.md` now only contains static job configuration. Script: `~/.hermes/scripts/regen-cron-doc.py`.

## Before Starting Any Task
1. Read ~/ACERSERVER.md — server map, active projects, recent activity
2. Read /home/chris/cp7-bridge/docs/agent-standards/AGENT-OPERATING-STANDARD.md — rules, templates, ADR triggers
3. Read target project AGENTS.md + target project HANDOFF.md
- When done: run session-save.sh with a summary of what you did
