# ADR 2026-09-01 — Bob policy path localization

## Status
Accepted for startup-context closeout.

## Context
Bob/Hermes policy was moved from `/home/chris/bob-principles.md` into the Hermes runtime project at `~/.hermes/bob-principles.md`, but tracked startup code and identity text still referenced the deleted global path and ACP Rule 00-80. That leaves Bob with stale routing and incorrectly implies Bob-specific policy participates in shared cross-harness authority.

## Decision
- Resolve Bob principles from the Hermes project/runtime root next to the startup code.
- Render Bob's startup brief with `~/.hermes/bob-principles.md` and ACP Rule 00-90.
- Update tracked Bob identity/tests to the same Rule 00-90 reference.
- Do not reintroduce Bob principles into ACP shared policy.
- Preserve unrelated live Hermes edits; live activation must apply only these reviewed substitutions.

## Verification
- Bob startup-bundle unit tests pass.
- Generated/injected startup brief contains `ACP Rule 00-90` and `~/.hermes/bob-principles.md`.
- No tracked active Hermes source references `/home/chris/bob-principles.md`, `~/bob-principles.md`, or `ACP Rule 00-80` after the change.

## Rollback
Revert this change. No unrelated Hermes runtime content is part of the decision.
