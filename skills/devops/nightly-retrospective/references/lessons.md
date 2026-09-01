# Lessons Learned from Previous Runs
- Always use timestamp-based date filtering (YESTERDAY_EPOCH/TODAY_EPOCH)
- Prefer hardcoded values over f-strings in cron scripts
- API error handling requires explicit fallback paths
- Skill patch requires complete 'old_string' match pattern