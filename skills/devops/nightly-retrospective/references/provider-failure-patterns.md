# Provider Failure Patterns

## Common Error
- `Unknown provider '<provider>'`

## Diagnosis
```bash
# Check cron job configuration for provider references
grep -A5 -B5 "provider:" ~/.hermes/cron/jobs.json

# List available providers in Hermes model registry
hermes model list

# Validate specific provider availability
hermes model list --provider <provider_name>
```

## Prevention Strategies
1. **Provider Validation**: Always verify model providers exist in hermes model registry before configuring cron jobs
2. **Pre-Flight Checks**: Add provider existence check in script pre-flight logic
3. **Fallback Handling**: Implement try/except blocks around Honcho API calls with local file fallback
4. **Error Logging**: Capture and report exact error messages from cron scheduler

## Example Script Snippet
```python
import subprocess
import urllib.request
import json

# Validate provider before executing cron logic
try:
    available_providers = subprocess.check_output(
        ['hermes', 'model', 'list'], text=True
    )
    if 'openai' not in available_providers:
        raise RuntimeError('Required provider openai not configured')
except subprocess.CalledProcessError as e:
    raise RuntimeError(f'Hermes model list failed: {e}')