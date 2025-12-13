# Agent-to-MCP Tool Mapping (Allowlist)

## 1. FeedbackDigestAgent
- **Allowed tools:**
  - feedback.list
  - feedback.stats
  - config.runtime
- **Forbidden tools:**
  - Any write/delete tool
  - usage.summary, errors.recent, events.pageviews, health.check

## 2. AIUsageTrackerAgent
- **Allowed tools:**
  - usage.summary
  - config.runtime
  - health.check
- **Forbidden tools:**
  - Any write/delete tool
  - feedback.list, feedback.stats, errors.recent, events.pageviews

## 3. ErrorWatcherAgent
- **Allowed tools:**
  - errors.recent
  - health.check
  - config.runtime
- **Forbidden tools:**
  - Any write/delete tool
  - feedback.list, feedback.stats, usage.summary, events.pageviews

## 4. BetaUXAnalyzerAgent
- **Allowed tools:**
  - feedback.stats
  - events.pageviews
  - usage.summary (optional)
  - config.runtime
- **Forbidden tools:**
  - Any write/delete tool
  - feedback.list, errors.recent, health.check

---
-
## 5. CyberSecurityWatcherAgent
- **Allowed tools:**
  - security.auth_failures
  - security.suspicious_ips
  - security.rate_limit_hits
  - security.admin_route_attempts
  - security.http_4xx_5xx_summary
  - health.check
  - config.runtime
- **Forbidden tools:**
  - Any write/delete tool
  - Any user creation
  - Any secret access
- All agents are strictly limited to the tools above (allowlist only).
- No agent is allowed to use write/delete or mutation tools.
