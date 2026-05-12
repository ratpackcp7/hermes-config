---
name: configure-hermes-gateway-model
description: Safely plan, stage, verify, and roll back Hermes Gateway model/provider changes. Restarts require explicit confirmation.
category: devops
---

# Hermes Gateway Model/Provider Configuration

## Purpose

Configure the Hermes Agent Gateway model/provider safely.

## Safety Priority

Changing config may be safe. Restarting gateway/Bob/Hermes is production-impacting.

Do not restart anything unless Chris explicitly approves the restart in the current task.

Do not print API keys, bearer tokens, credential files, or secrets.

## Current Common Config

Likely config file:

```text
/home/chris/.hermes/config.yaml
```

OpenRouter key for evaluation may be referenced from:

```text
/home/chris/.config/bob-model-eval/openrouter.env
```

Use the path, not the key value.

## Read-Only Discovery First

Before editing:

```bash
hermes config path 2>/dev/null || true
grep -nE '^model:|default:|provider:|fallback_providers:' /home/chris/.hermes/config.yaml 2>/dev/null
systemctl --user cat hermes-gateway 2>/dev/null | sed -E 's/(API[_-]?KEY|TOKEN|SECRET|PASSWORD)=.*/\1=<REDACTED>/Ig'
```

Report current:
- config path
- provider
- model
- base URL if explicit
- whether restart is required
- rollback plan

## Recommended OpenRouter DeepSeek Candidate

Current tested candidate:

```yaml
model:
  default: deepseek/deepseek-v4-flash
  provider: openrouter
```

Base URL:

```text
https://openrouter.ai/api/v1
```

## Pre-Edit Model Verification

Before editing the config, verify the target model ID exists on the provider:
- For OpenRouter: Check `https://openrouter.ai/<model-id>/api` using `web_extract` — a response indicating "model not available" means the ID is invalid.
- Example: `tencent/hy3` returns 404, while `tencent/hy3-preview` is valid.
- Skip this step only if you have confirmed the model ID from the provider's official documentation.

## Staged Edit Procedure

1. Back up the config:

```bash
cp /home/chris/.hermes/config.yaml /home/chris/swap/config.yaml.before-model-change.$(date +%Y%m%d-%H%M%S)
```

2. Edit only the model/provider keys.
3. Validate YAML if a validator exists.
4. Report diff with secrets redacted.
5. Stop before restart unless Chris explicitly approves.

## Per-Session Model Switching (Platform Commands)

For gateway platforms (Telegram, Discord, etc.), you can switch models per-session without editing `config.yaml`:
- Telegram: Send `/model` (opens interactive provider/model picker) or `/model <model-id>` for direct switches.
- Add `--global` to persist the change to `config.yaml`.
- These commands are handled by the gateway's `_handle_model_command` and do not affect the global config unless explicitly persisted.
- Useful for testing models without risking invalid global configs.

## Restart

Restarting Hermes Gateway kills/interrupts active Bob context. Use only after approval.

Preferred restart command if approved:

```bash
/home/chris/.hermes/scripts/safe-restart-gateway.sh
```

Never use raw `systemctl restart` unless a spec explicitly permits it.

## Rollback

Rollback is restoring the backup config and performing an approved safe restart.

Report the exact backup path.

## Required Report

```text
BOB_MODEL_SWITCH_PLAN
current_config:
  path:
  provider:
  model:
  base_url:
  secrets_redacted: yes/no
openrouter_key:
  available: yes/no
  source_path:
proposed_model:
  provider: openrouter
  model: deepseek/deepseek-v4-flash
  base_url: https://openrouter.ai/api/v1
proposed_change:
  - ...
backup_path:
restart_required: yes/no/unknown
can_apply_without_restart: yes/no
rollback:
  - ...
risks:
  - ...
ready_for_confirmation: yes/no
```
