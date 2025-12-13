# Beta UX Analyzer Skill

## Purpose
- Combine user feedback and page view stats to identify top friction points for beta users

## Inputs
- DB Table: `feedback_submissions`
- DB Table: `usage_log`
- (Optional) Frontend analytics events

## Allowed Tools
- `mcp_db_query`
- `mcp_log_search`

### Forbidden Actions
- No user re-identification
- No direct UI changes

## Output Schema
- **Friction Points:**
  - Page/component
  - Feedback theme
  - Example feedback
  - Page views
  - Suggested fix
- **Summary:**
  - Top 2 friction areas
  - Notable trends

## Quality Checks
- Validate feedback-page mapping
- Remove outlier events
- Ensure suggestions are actionable

## Escalation Rules
- Flag as critical if friction blocks onboarding or scoring
- Escalate if >5 users report same issue

## Token/Cost Budget
- Max 4,000 tokens per run
- Max 6 runs/day
- Target: <$0.10/run

## Example Output
- Friction: MatchSetupView, "confusing team select", 8 views, fix: add help icon
- Summary: 2 main issues, onboarding drop-off
