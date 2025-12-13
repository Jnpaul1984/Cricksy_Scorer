
# MCP (Model Context Protocol) Audit – Cricksy Scorer

## 1. Current MCP Implementation: Summary

- **Dedicated MCP server**: `backend/services/mcp_server.py` exposes all tool contracts as HTTP endpoints.
- **MCP = Tool API**: Tools are grouped by domain (db_tools, usage_tools, error_tools, analytics_tools, system_tools).
- **Transport:**
  - All MCP tools are served via **FastAPI HTTP endpoints** (not stdio/SSE).
  - Example: `/tools/db/feedback.list`, `/tools/usage/usage.summary`, `/tools/errors/errors.recent`, `/tools/system/config.runtime`
- **Tool registry**: Each tool is a POST endpoint, input/output validated by Pydantic.
- **Audit logging**: All tool calls are logged with {tool, userId, timestamp, status}.
- **Strict auth**: All tools require admin or analyst role/token.

## 2. MCP Context Architecture (ASCII)

```
[DB + Models]
    |
    v
[MCP Tool Server (FastAPI)]
    |-- /tools/db/feedback.list, /tools/db/feedback.stats
    |-- /tools/usage/usage.summary
    |-- /tools/errors/errors.recent
    |-- /tools/analytics/events.pageviews
    |-- /tools/system/config.runtime, /tools/system/health.check
    v
[Agents / LLMs / Scripts]
```

## 3. Available Tools & Endpoints

### MCP Tool Endpoints
- `/tools/db/feedback.list` → List feedback
- `/tools/db/feedback.stats` → Feedback stats
- `/tools/usage/usage.summary` → Usage summary
- `/tools/errors/errors.recent` → Recent errors
- `/tools/analytics/events.pageviews` → Pageview stats
- `/tools/system/config.runtime` → Runtime config
- `/tools/system/health.check` → Health check

#### Input/Output Shapes
- See `docs/agents/MCP_TOOL_CONTRACTS.md` for full schemas.

## 4. Auth Model
- **All tool endpoints**: Require admin or analyst role/token (uses FastAPI Depends).
- **Audit logging**: All calls logged for traceability.

## 5. Env Vars Used
- `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `LLM_MODEL`, `LLM_PROVIDER` (for scripts)
- Standard FastAPI/DB env vars for backend

## 6. Existing Docs
- `backend/api_contract.md` (API shapes)
- `docs/agents/MCP_TOOL_CONTRACTS.md` (tool contracts)
- Inline docstrings in tool modules

## 7. Gaps vs Agent Needs
| Agent                | Needs DB/Log/Feedback Access? | Can Use Current MCP? | Gaps |
|----------------------|-------------------------------|----------------------|------|
| FeedbackDigest       | Yes (feedback_submissions)    | No                   | No tool for feedback aggregation, no DB query tool |
| AIUsageTracker       | Yes (usage_log, billing)      | No                   | No usage/cost aggregation endpoint/tool |
| ErrorWatcher         | Yes (errors, logs)            | No                   | No error summary endpoint/tool |
| BetaUXAnalyzer       | Yes (feedback, usage_log)     | Partial (context)    | No feedback+usage join, no friction summary |

**Summary:**
- MCP context endpoints are rich for match/game/player analysis, but there is no general-purpose MCP server, tool registry, or DB/log access for agent skills.
- Agents like FeedbackDigest, AIUsageTracker, ErrorWatcher, and BetaUXAnalyzer will need new endpoints or tool APIs for DB/log access and aggregation.
