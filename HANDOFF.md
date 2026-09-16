# HANDOFF — hermes-config

Durable handoff for the Hermes runtime-config repo at `~/.hermes`. `scripts/session-start.sh` never writes this file.

## Current state

- Hermes is the runtime/product owner; there is no separate legacy agent policy or routing authority.
- Hidden startup/output-transform context has been retired by the 2026-09-16 context cleanup.
- Intentional Hermes memory, user-profile, and session context remains enabled unless separately changed.
- No gateway restart is part of this source cleanup; an already-running process may retain code loaded before the change until a separately authorized restart or new process.

## Canonical references

- Project/service map: `/home/chris/AGENT_INDEX.md`
- Canonical cross-harness dispatch: `/home/chris/cp7-bridge/docs/agent-dispatch/DISPATCH.md`
- Shared agent-context contract: `/home/chris/projects/cp7-agent-stack/rails/agent-context-contract.md`
- `~/todo.md` is the primary global open-work surface.
- `~/project-status.md` is a generated secondary cross-project view.

## Working rule

For work in another project, use that project's current `AGENTS.md` and `HANDOFF.md` when relevant. Do not import policy from retired compatibility files, generated startup snapshots, or unrelated parent directories.
