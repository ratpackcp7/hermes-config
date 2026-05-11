---
name: handoff
description: Create or resume session handoffs. Use /home/chris/swap for handoffs meant for ChatGPT/file exchange; use ~/handoffs for local durable handoffs.
category: productivity
---

# Handoff Skill

## Purpose

Use this when Chris says “handoff,” “make a handoff,” “resume handoff,” or needs a clean summary to continue work later.

## Default locations

Local durable handoffs:

```text
/home/chris/handoffs/
```

File exchange handoffs for ChatGPT/phone/laptop:

```text
/home/chris/swap/
```

If Chris mentions ChatGPT, upload, phone, file share, or swap, use `/home/chris/swap/`.

## Flow

### Create a handoff

If title is missing, ask for a short title. Then write:

```text
/home/chris/handoffs/YYYY-MM-DD-<slug>.md
```

After writing, publish it so Chris can open it from Telegram:

```python
from agent.published_artifacts import publish_artifact

url = publish_artifact(
    "/home/chris/handoffs/YYYY-MM-DD-<slug>.md",
    display_name="YYYY-MM-DD-<slug>.md"
)
# Send to Chris: f"Handoff saved: [{display_name}]({url})"
```

or, for file exchange (ChatGPT/phone/laptop — no publish needed):

```text
/home/chris/swap/YYYY-MM-DD-<slug>-handoff.md
```

## Handoff format

```markdown
# <Title> — Handoff (<date>)

## Situation
One paragraph: what were we doing and why did we stop?

## Current state
- Important files/paths
- Current branch/commit/session IDs
- Running jobs or blockers

## Decisions made
- ...

## What worked
- ...

## What failed / watch-outs
- ...

## Next safe step
- Exact next action

## Do not do
- Restarts/redeploys/protected-path writes/etc. if relevant
```

## Safety

Do not include API keys, tokens, passwords, cookies, or raw secrets.
If a handoff references secrets, say where they live, not the values.
