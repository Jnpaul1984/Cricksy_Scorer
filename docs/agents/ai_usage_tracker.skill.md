# AI Usage Tracker Skill

## Purpose
- Summarize daily AI token spend and usage patterns
- Detect abuse and suggest cost optimizations (e.g., Gemini/Anthropic routing)

## Inputs
- DB Table: `usage_log`
- (Optional) API billing endpoints

## Allowed Tools
- `mcp_db_query`
- `mcp_cost_report`

### Forbidden Actions
- No user-level cost enforcement
- No API key rotation

## Output Schema
- **Spend Summary:**
  - Total tokens
  - Total cost
  - Top 3 features by tokens
- **Abuse Alerts:**
  - User/feature
  - Pattern detected
  - Suggested action

## Quality Checks
- Cross-check token totals with billing
- Flag outliers for review
- Validate feature mapping

## Escalation Rules
- Flag as critical if >$10/day or >100k tokens by one user
- Escalate if abuse pattern repeats 2+ days

## Token/Cost Budget
- Max 3,000 tokens per run
- Max 8 runs/day
- Target: <$0.08/run

## Example Output
- Spend: 42,000 tokens ($1.05)
- Top: Score Predictor, Chat, Beta UX
- Abuse: None
