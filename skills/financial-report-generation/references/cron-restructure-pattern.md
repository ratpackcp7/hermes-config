# Cron Restructure Pattern: Agent-SQL → Deterministic Wrapper

**Pattern**: When a cron job's prompt generates SQL/business logic at runtime, restructure it to call a deterministic wrapper instead.

## Why

- Agent-generated SQL causes schema drift, silent failures, and misleading reports
- Business logic in cron prompts is untested and unreviewable
- Wrappers are deterministic, testable, and fail loudly

## How

1. **Identify the cron job** — find the job in `~/.hermes/cron/jobs.json`
2. **Create the wrapper** — `~/.hermes/scripts/<name>.sh`:
   - Calls API/source-of-truth (not direct DB)
   - Computes date windows deterministically (weekly = last 7 days, MTD = month start)
   - Generates output artifact (HTML, JSON, etc.)
   - Hard verification: exits nonzero on missing/empty/mismatched output
   - Prints `WEEKLY_FINANCE_REPORT_OK` + `REPORT_PATH=...` on success
3. **Update the cron prompt** — replace SQL-generating prompt with:
   > Run ONLY: `bash ~/.hermes/scripts/<name>.sh`. Do NOT generate SQL. Do NOT query DB directly. If script exits nonzero, report exact error. If exit 0, send artifact to user.
4. **Dry run** — run the wrapper manually, verify exit 0 and artifact exists
5. **Do NOT restart gateway** — cron picks up new prompt on next tick

## Example: Weekly Finance Report

**Before:** Agent prompt instructed SQL against `finance-hub-db` Postgres, manual HTML generation, agent-owned date windows.

**After:** Agent runs `bash ~/.hermes/scripts/run-empower-weekly-finance-report.sh` only. Wrapper calls Empower API, generates verified HTML, exits nonzero on failure.

**Result:** Cron no longer owns finance business logic. Empower API is the sole source of truth.

## Key Rules

- Wrapper must fail nonzero if artifact is missing, empty, or has period mismatch
- No "silent ok" — if the deliverable failed, the cron must report failure
- Date windows must be computed, not invented (weekly = today-6 to today, MTD = 1st to today)
- Labels in output must match actual data windows (no "Jan-Jun" title with Jan-Mar data)
