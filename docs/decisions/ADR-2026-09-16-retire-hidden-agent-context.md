# ADR — Retire hidden legacy agent context

Date: 2026-09-16
Status: accepted

## Context

The context-provenance audit found legacy startup plugins that injected generated operational summaries and extra policy before the first model call, plus an output transformer that could replace or append to model responses. Those layers duplicated visible Hermes/project context and could silently reintroduce stale routing rules.

## Decision

Hermes no longer enables those legacy startup/output-policy plugins. The runtime uses its visible harness contract, `SOUL.md`, intentional memory/user-profile/session features, the current conversation, and project files explicitly read for the task. Operator diagnostics remain operator output only and are never model injection.

## Consequences

The retired plugins, generated startup bundle, agent-specific policy file, and agent-specific maintenance skill are removed from source. Product memory remains intentional. Existing running processes require a normal future restart/new process to unload already-imported code; no restart is performed by this source change.
