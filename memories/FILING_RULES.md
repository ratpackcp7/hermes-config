# Memory Filing Rules — Bob's Reference

**CHECK THIS FILE before every `memory` add/replace/remove call.**

## The 3-Tier System

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

## L1 Health Rules

1. **Check at session start:** `usage=$(wc -c < ~/.hermes/memories/MEMORY.md); pct=$((usage * 100 / 2200))`
2. **If >80%:** Promote 2-3 oldest entries to L2/wiki BEFORE adding anything
3. **Never hit 100%:** That's a process failure
4. **Remove, don't just shorten:** If an entry hasn't been used in 2 weeks, remove it entirely

## What to NEVER Put in L1

- ❌ Task progress or TODO state (use ~/todo.md)
- ❌ Session outcomes (use session_search)
- ❌ Completed work logs (use changelog.md)
- ❌ Raw data dumps (use wiki raw/)
- ❌ Temporary blockers (use L2 with date)
- ❌ Long procedural text (use skills/wiki)

## Enforcement

**Before every `memory` tool call, ask:**
1. Is this L1, L2, or L3?
2. If L1: is it <100 chars and used weekly?
3. If L1: will this push us over 80%?
4. If yes to #3: promote something first

**Penalty for violation:** L1 at 100% = scrambling to fix = wasted time = Chris annoyed
