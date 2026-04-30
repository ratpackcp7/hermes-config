---
name: l1-memory-management
description: Manage L1 memory (2,200 char limit) using a 3-tier system to prevent overflow. Includes decision tree, health checks, and promotion rules.
---

# L1 Memory Management — 3-Tier System

## Problem This Solves
L1 memory (`~/.hermes/memories/MEMORY.md`) has a hard 2,200-character limit. Without proactive promotion, it hits 100% and forces scrambling to prune during active sessions.

## The 3-Tier Architecture

```
L1 (~/.hermes/memories/MEMORY.md)     — 2,200 chars, hot cache, injected EVERY turn
L2 (~/.hermes/memories/L2_FACTS.md)   — ~10K chars, warm cache, grep-searchable
L3 (~/wiki/)                            — unlimited, cold storage, compiled knowledge
```

## L1 Criteria (Daily-Use Facts Only)

**ADD to L1 if ALL are true:**
1. ✅ Fact will be used **weekly or more often**
2. ✅ Fact is **short** (<100 chars ideal, 150 max)
3. ✅ Fact is a **stable environment detail** or **user preference**

**Examples that BELONG in L1:**
- `acerserver = Acer Swift 16 AI, Ubuntu 24.04, 32GB, 100.101.249.113`
- `Gateway restart: safe-restart-gateway.sh ONLY`
- `Home Assistant (GMKtec HAOS, cp7ha.duckdns.org:8123, login bob/capmkp37)`
- `Family (MK teacher, Maggie 9 CGM, Claire 7, John 4, sitter Christine Coburn)`

**Examples that DO NOT belong in L1:**
- ❌ Project-specific details (belong in wiki entity page)
- ❌ Procedural knowledge (belong in skill or wiki concept)
- ❌ Temporary issues/bugs (belong in L2 or session log)
- ❌ Full audit rules (belong in wiki concept page)
- ❌ Dashboard port numbers (lookup in AGENTS.md/wiki)
- ❌ Backup schedules (wiki or L2)

## L2 Criteria (Warm Cache)

**ADD to L2 if:**
1. ✅ Fact is useful but **not needed weekly**
2. ✅ Fact is **searchable** (grep-friendly format)
3. ✅ Fact would waste L1 space but is annoying to look up

**Format for L2 entries:**
```markdown
## Section Title
- Key fact in bullet form
- Short, scannable, grep-friendly
```

**Examples:**
- web_search freeze fix steps
- Dashboard service ports
- Empower audit rules summary
- Swap browser details

## L3 Wiki Criteria (Cold Storage)

**ADD to wiki if:**
1. ✅ Knowledge needs **compilation** or **synthesis**
2. ✅ Content is **procedural** (how-to, skills)
3. ✅ Content is **project-specific** (entity pages)
4. ✅ Content needs **version tracking** (churn_rate, last_verified)

**Wiki structure:**
- `entities/` — project/tool pages (acerserver.md, empower.md)
- `concepts/` — procedural knowledge (empower-audit-rules.md)
- `engineering/` — compiled technical knowledge
- `archive/` — deprecated pages

## Decision Tree

```
New fact to store
       │
       ▼
Is it a user preference/communication style?
   ├─ YES → L1 (short form)
   │
   └─ NO
       │
       ▼
Is it a stable environment fact used weekly?
   ├─ YES → L1 (<100 chars)
   │
   └─ NO
       │
       ▼
Is it searchable and useful but not daily?
   ├─ YES → L2 (grep-friendly bullets)
   │
   └─ NO
       │
       ▼
Is it procedural/project knowledge?
   ├─ YES → Wiki (entity or concept page)
   │
   └─ NO → Session context (session_search) or Skill
```

## L1 Health Rules (NON-NEGOTIABLE)

1. **Check at session start:**
   ```bash
   usage=$(wc -c < ~/.hermes/memories/MEMORY.md)
   pct=$((usage * 100 / 2200))
   [ $pct -gt 80 ] && echo "⚠️ L1 at ${pct}% — promote entries before adding new content"
   ```

2. **If >80%:** Promote 2-3 oldest entries to L2/wiki BEFORE adding anything new

3. **Never hit 100%:** That's a process failure — Chris gets annoyed

4. **Remove, don't just shorten:** If an entry hasn't been used in 2 weeks, remove it entirely

5. **Enforcement:** Before every `memory` tool call, check `~/.hermes/memories/FILING_RULES.md`

## What to NEVER Put in L1

- ❌ Task progress or TODO state (use ~/todo.md)
- ❌ Session outcomes (use session_search)
- ❌ Completed work logs (use changelog.md)
- ❌ Raw data dumps (use wiki raw/)
- ❌ Temporary blockers (use L2 with date)
- ❌ Long procedural text (use skills/wiki)

## Pointer-to-Truth Pattern (NEW — 2026-04-30)

**NEVER hardcode dynamic values in L1.** When config values change (like gateway model), the L1 entry becomes stale.

**BAD (stale snapshot):**
```
Gateway default: xiaomi/mimo-v2-pro/nous
```

**GOOD (pointer to truth):**
```
Gateway config: ~/.hermes/config.yaml (model.default, provider)
```

Then when you need the current value, **read the file** — never stale.

### Auto-Sync Script

Created `~/.hermes/scripts/sync-gateway-config-to-memory.sh`:
- Reads `config.yaml`, extracts `model.default`
- Compares to L1 memory
- Updates L1 if different
- Commits to `hermes-config` repo

**Integrate into nightly retro** — update the `nightly-retrospective` skill to call the sync script.

### Session Start Check

Updated `~/.hermes/scripts/session-start.sh` with config freshness check:
```python
# Check if L1 memory matches config.yaml
import yaml, re
current_model = config.get('model', {}).get('default', '')
# Compare to L1 entry, warn if mismatch
```

## Wiki Optimization for Bob (NEW — 2026-04-30)

### BOB_INDEX.md

Created `~/wiki/BOB_INDEX.md` — personal cheatsheet mapping tools/tasks to wiki pages.

**Structure:**
```markdown
# Bob's Wiki Index
## Tools I Use Daily (table: Tool → Wiki Page)
## Concepts I Need (table: Concept → Wiki Page)  
## Common Tasks (table: Task → Where to Look)
## Quick Facts (merged from L2 cache)
## Search Tips (grep commands)
```

**Why:** I never "browse" the wiki — I `grep` everything. BOB_INDEX gives me instant lookup without remembering paths.

### Wiki Lint Exemptions

Updated `~/.hermes/scripts/wiki-lint.py`:
- Added `BOB_INDEX.md` to orphan exemption list
- Fix case-sensitive wikilinks: `[[bob-index]]` → `[[BOB_INDEX]]`

### Wiki Health

- 77 pages, 52 orphans (69%) — **doesn't matter** for my workflow (I grep, not browse)
- Cross-link top orphans I actually use (e.g., `empower.md` → `[[BOB_INDEX]]`)
- Archive duplicates: `family-finance.md`, `family_and_finances.md` → `archive/`

### When L1 hits 80%:
1. Read `~/.hermes/memories/MEMORY.md`
2. Identify 2-3 longest/oldest entries
3. Move them to L2_FACTS.md (create if missing)
4. Remove from L1
5. Verify L1 drops below 80%
6. THEN add new content

### Creating L2 Facts file (one-time setup):
```bash
cat > ~/.hermes/memories/L2_FACTS.md << 'EOF'
# L2 Facts — Warm Cache
Promoted from L1 memory. Searchable via grep. Not daily-use, but useful.

## Section Title
- Fact in bullet form
EOF
```

### Git hygiene (Rule #2):
- L2_FACTS.md lives in `~/.hermes/` — init as git repo, push to `ratpackcp7/hermes-config`
- Wiki content pushes to `ratpackcp7/wiki`
- Commit ALL documentation changes immediately

## Files Created During Implementation

- `~/.hermes/memories/L2_FACTS.md` — warm cache for promoted L1 entries
- `~/.hermes/memories/FILING_RULES.md` — decision tree reference (check before every `memory` call)
- `~/.hermes/memories/MEMORY.md` — L1 itself (2,200 char limit)
- `~/wiki/` — L3 cold storage (git repo: `ratpackcp7/wiki`)
- `~/.hermes/` — git repo for configs (`ratpackcp7/hermes-config`)

## Lessons Learned

1. **L1 overflow is a process failure, not a storage bug** — the space is intentionally small to force curation
2. **Check percentage at session start, not when it's already 100%** — proactive > reactive
3. **Chris was right:** "This is your memory. You should manage it." Don't make the user police your memory hygiene
4. **FILING_RULES.md is load-bearing** — check it before every `memory` tool call
5. **Promote at 80%, not 95%** — gives margin for the session's new content
6. **Merge related wiki pages** rather than creating orphans (e.g., MK finance → empower.md#chris-mk-finance)

## Pitfalls

- **Appending without checking usage first** → hits 100% mid-session
- **Shortening entries instead of removing** → still wastes space with unused facts
- **Putting procedural knowledge in L1** → belongs in skills or wiki concepts
- **Forgetting to commit L2/wiki changes** → violates Rule #2 (git as source of truth)
- **Creating wiki orphans** → merge into existing pages instead
