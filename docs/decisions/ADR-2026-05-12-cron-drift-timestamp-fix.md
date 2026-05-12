# ADR: Fix cron-doc-drift-check false positives

**Date**: 2026-05-12
**Status**: Accepted
**Context**: The `cron-doc-drift-check` cron job was sending hourly pings even when no real drift existed. Investigation revealed two issues:

1. `regen-cron-doc.py` embedded `datetime.now()` in the generated output (line 30), causing `new_content == original` to always fail.
2. The generated output included volatile runtime fields: `last_run_at`, `last_status`, and `runs completed`. These change every time any cron job runs, causing the generated content to always differ from `CRON.md`.

**Decision**: 
1. Remove the volatile timestamp from the section header.
2. Remove all volatile runtime fields (`last_run`, `last_status`, `runs completed`) from the generated output. The `CRON.md` should document the static job configuration, not runtime state.

**Consequences**:
- Hourly false-positive pings eliminated
- `CRON.md` no longer has volatile content (no timestamp, no runtime state)
- Real drift (added/removed/changed cron job configurations) still correctly triggers the ping
- The `CRON.md` is now a stable document that only changes when job config changes

**Files changed**: `scripts/regen-cron-doc.py`
