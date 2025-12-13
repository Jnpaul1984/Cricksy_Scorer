
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional, List
from backend.security import require_admin
import os
import pathlib
import time
from backend.services.agent_budget import check_agent_limits, record_agent_run, get_recent_runs, get_today_token_total
from backend.sql_app.database import get_db

router = APIRouter(prefix="/admin/agents", tags=["admin_agents"])

AGENT_SKILLS = {
    "feedback_digest": "feedback_digest.skill.md",
    "ai_usage_tracker": "ai_usage_tracker.skill.md",
    "error_watcher": "error_watcher.skill.md",
    "beta_ux_analyzer": "beta_ux_analyzer.skill.md",
    "cyber_security_watcher": "cyber_security_watcher.skill.md",
}

AGENT_TOOL_ALLOWLIST = {
    "feedback_digest": ["feedback.list", "feedback.stats", "config.runtime"],
    "ai_usage_tracker": ["usage.summary", "config.runtime", "health.check"],
    "error_watcher": ["errors.recent", "health.check", "config.runtime"],
    "beta_ux_analyzer": ["feedback.stats", "events.pageviews", "usage.summary", "config.runtime"],
    "cyber_security_watcher": [
        "security.auth_failures",
        "security.suspicious_ips",
        "security.rate_limit_hits",
        "security.admin_route_attempts",
        "security.http_4xx_5xx_summary",
        "health.check",
        "config.runtime"
    ],
}

SKILLS_PATH = pathlib.Path(__file__).parents[2] / "docs" / "agents"


class RunAgentIn(BaseModel):
    agentKey: str
    since: str
    until: str

class RunAgentOut(BaseModel):
    markdownReport: str
    jsonSummary: Optional[dict]
    tokenUsage: int
    modelUsed: str

class AgentRunSummary(BaseModel):
    id: int
    agentKey: str
    userId: str
    since: str
    until: str
    model: str
    tokensIn: int
    tokensOut: int
    costUsdEstimate: float
    createdAt: str
    status: str

class UsagePanelOut(BaseModel):
    recent: List[AgentRunSummary]
    todayTokens: int


@router.post("/run", response_model=RunAgentOut)
async def run_agent(
    body: RunAgentIn,
    user=Depends(require_admin),
    db=Depends(get_db)
):
    if body.agentKey not in AGENT_SKILLS:
        raise HTTPException(400, "Unknown agentKey")
    # Budget enforcement
    tokensRequested = 1200  # Estimate for mock; replace with real count
    ok, reason = await check_agent_limits(db, body.agentKey, user.id, tokensRequested)
    if not ok:
        raise HTTPException(429, reason)
    # Load skills page
    skill_file = SKILLS_PATH / AGENT_SKILLS[body.agentKey]
    if not skill_file.exists():
        raise HTTPException(404, f"Skill page not found: {skill_file.name}")
    with open(skill_file, "r", encoding="utf-8") as f:
        skills_md = f.read()
    # Compose LLM prompt
    system = skills_md
    user_prompt = f"Run report for {body.since} to {body.until}."
    tools = AGENT_TOOL_ALLOWLIST[body.agentKey]
    # Call LLM (Gemini Pro, fallback Anthropic)
    try:
        model = "gemini-pro"
        markdownReport = f"## {body.agentKey} Report\n\n(Report for {body.since} to {body.until})\n\n...mock output..."
        tokenUsage = tokensRequested
        status = "ok"
    except Exception:
        model = "anthropic"
        markdownReport = f"## {body.agentKey} Report\n\n(Anthropic fallback for {body.since} to {body.until})\n\n...mock output..."
        tokenUsage = tokensRequested
        status = "fallback"
    # Estimate cost
    costUsdEstimate = round(tokenUsage * 0.000025, 4)
    # Log run
    await record_agent_run(
        db,
        agentKey=body.agentKey,
        userId=user.id,
        since=body.since,
        until=body.until,
        model=model,
        tokensIn=tokenUsage,
        tokensOut=tokenUsage,
        costUsdEstimate=costUsdEstimate,
        createdAt=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        status=status,
        markdownReport=markdownReport,
    )
    return RunAgentOut(
        markdownReport=markdownReport,
        jsonSummary=None,
        tokenUsage=tokenUsage,
        modelUsed=model
    )

@router.get("/usage", response_model=UsagePanelOut)
async def get_usage_panel(db=Depends(get_db)):
    recents = await get_recent_runs(db, limit=10)
    today_tokens = await get_today_token_total(db)
    # Convert recents to pydantic
    items = [AgentRunSummary(
        id=row.id,
        agentKey=row.agentKey,
        userId=row.userId,
        since=row.since,
        until=row.until,
        model=row.model,
        tokensIn=row.tokensIn,
        tokensOut=row.tokensOut,
        costUsdEstimate=row.costUsdEstimate,
        createdAt=str(row.createdAt),
        status=row.status
    ) for row in recents]
    return UsagePanelOut(recent=items, todayTokens=today_tokens)
