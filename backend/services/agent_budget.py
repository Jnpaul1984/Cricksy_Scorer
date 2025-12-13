# Agent run budget config and enforcement
from datetime import datetime, timedelta
from typing import Dict

AGENT_BUDGETS = {
    "feedback_digest": {"max_runs_per_day": 6, "max_tokens_per_run": 4000},
    "ai_usage_tracker": {"max_runs_per_day": 8, "max_tokens_per_run": 3000},
    "error_watcher": {"max_runs_per_day": 8, "max_tokens_per_run": 3000},
    "beta_ux_analyzer": {"max_runs_per_day": 6, "max_tokens_per_run": 4000},
}
MAX_DAILY_TOKENS_TOTAL = 20000

async def check_agent_limits(db, agentKey, userId, tokensRequested):
    from backend.sql_app.models_agent import AgentRun
    today = datetime.utcnow().date()
    # Count runs for this agent/user today
    runs_today = await db.execute(
        f"SELECT COUNT(*), COALESCE(SUM(tokensOut),0) FROM agent_runs WHERE agentKey=:agentKey AND userId=:userId AND createdAt >= :start",
        {"agentKey": agentKey, "userId": userId, "start": today}
    )
    count, tokens = runs_today.first() if runs_today else (0, 0)
    if count >= AGENT_BUDGETS[agentKey]["max_runs_per_day"]:
        return False, f"Max runs per day for {agentKey} exceeded"
    if tokensRequested > AGENT_BUDGETS[agentKey]["max_tokens_per_run"]:
        return False, f"Token limit per run exceeded"
    # Check global daily tokens
    total_tokens_today = await db.execute(
        f"SELECT COALESCE(SUM(tokensOut),0) FROM agent_runs WHERE createdAt >= :start",
        {"start": today}
    )
    total_tokens = total_tokens_today.scalar() or 0
    if total_tokens + tokensRequested > MAX_DAILY_TOKENS_TOTAL:
        return False, "Max daily tokens exceeded"
    return True, None

async def record_agent_run(db, **kwargs):
    from backend.sql_app.models_agent import AgentRun
    run = AgentRun(**kwargs)
    db.add(run)
    await db.commit()
    return run

async def get_recent_runs(db, limit=10):
    from backend.sql_app.models_agent import AgentRun
    return (await db.execute(f"SELECT * FROM agent_runs ORDER BY createdAt DESC LIMIT :limit", {"limit": limit})).fetchall()

async def get_today_token_total(db):
    from backend.sql_app.models_agent import AgentRun
    today = datetime.utcnow().date()
    total = await db.execute(f"SELECT COALESCE(SUM(tokensOut),0) FROM agent_runs WHERE createdAt >= :start", {"start": today})
    return total.scalar() or 0
