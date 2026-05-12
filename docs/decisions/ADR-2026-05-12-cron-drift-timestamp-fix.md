# ADR: Fix cron-doc-drift-check false positives

**Date**: 2026-05-12
**Status**: Accepted
**Context**: The `cron-doc-drift-check` cron job was sending hourly pings even when no real drift existed. Investigation revealed that `regen-cron-doc.py` embedded `datetime.now()` in the generated output, causing `new_content == original` to always fail (timestamp always differs).

**Decision**: Remove the volatile timestamp from the generated `## Active Jobs` section. The comparison is now stable — it only triggers on real structural changes to `jobs.json`.

**Consequences**:
- Hourly false-positive pings eliminated
- `CRON.md` no longer has a "last updated" timestamp (not needed for a generated file)
- Real drift (added/removed/changed cron jobs) still correctly triggers the ping

**Files changed**: `scripts/regen-cron-doc.py`
