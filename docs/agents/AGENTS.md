# Cricksy Agents Overview

| Agent                | When it runs                | Inputs                        | Outputs                | Token Budget         | Owner      |
|----------------------|----------------------------|-------------------------------|------------------------|---------------------|------------|
| [Feedback Digest](feedback_digest.skill.md)      | Daily, or on feedback spike    | feedback_submissions    | Themes, summary     | 4,000/run, 6/day, <$0.10 | Product    |
| [AI Usage Tracker](ai_usage_tracker.skill.md)    | Daily, post-billing, abuse alert | usage_log, billing     | Spend, abuse alerts | 3,000/run, 8/day, <$0.08 | Engineering|
| [Error Watcher](error_watcher.skill.md)          | Hourly, on error spike         | errors, /logs/errors   | Error, perf summary | 3,000/run, 8/day, <$0.08 | Backend    |
| [Beta UX Analyzer](beta_ux_analyzer.skill.md)    | Daily, or after beta session   | feedback_submissions, usage_log | Friction points, summary | 4,000/run, 6/day, <$0.10 | Product    |

- See each skill page for full details, output schema, and escalation rules.
