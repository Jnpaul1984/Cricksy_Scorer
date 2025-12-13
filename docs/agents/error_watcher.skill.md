# Error Watcher Skill

## Purpose
- Summarize recurring backend 5xx errors and slow endpoints
- Highlight top stack traces and provide reproduction hints

## Inputs
- DB Table: `errors`
- API: `/logs/errors` endpoint

## Allowed Tools
- `mcp_db_query`
- `mcp_log_search`

### Forbidden Actions
- No error suppression
- No direct code changes

## Output Schema
- **Error Summary:**
  - Endpoint
  - Error count
  - Top stack trace
  - Repro hint
- **Performance:**
  - Slowest endpoints
  - Avg/max latency

## Quality Checks
- Deduplicate stack traces
- Confirm error reproducibility
- Check for recent regressions

## Escalation Rules
- Flag as critical if same 5xx >10x/hr
- Escalate if error blocks scoring or login

## Token/Cost Budget
- Max 3,000 tokens per run
- Max 8 runs/day
- Target: <$0.08/run

## Example Output
- Error: /games/score (17x), stack: IntegrityError, repro: submit duplicate delivery
- Perf: /auth/login slowest (avg 1.2s)
