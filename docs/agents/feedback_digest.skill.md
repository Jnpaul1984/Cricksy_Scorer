# Feedback Digest Skill

## Purpose
- Group user feedback by theme and severity
- Propose actionable next steps for product and engineering

## Inputs
- DB Table: `feedback_submissions`
- (Optional) Usage logs for context

## Allowed Tools
- `mcp_db_query`
- `mcp_log_search`

### Forbidden Actions
- No direct user contact
- No data deletion or modification

## Output Schema
- **Themes:**
  - Theme name
  - Severity (low/med/high)
  - Example feedback
  - Proposed action
- **Summary:**
  - Total feedback
  - Top 3 urgent issues

## Quality Checks
- Remove duplicate feedback
- Validate theme assignment
- Ensure actionable proposals

## Escalation Rules
- Flag as critical if >3 high-severity issues in 24h
- Escalate if feedback suggests data loss or security

## Token/Cost Budget
- Max 4,000 tokens per run
- Max 6 runs/day
- Target: <$0.10/run

## Example Output
- Themes:
  - Onboarding Confusion (high): "I couldn't find the start match button." → Add tooltip
  - Slow Score Update (med): "Scores lag behind live play." → Optimize socket events
- Summary: 12 feedback, 2 urgent
