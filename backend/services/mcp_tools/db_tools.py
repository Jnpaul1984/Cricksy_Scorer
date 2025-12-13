from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from typing import List, Optional
from backend.security import require_admin_or_analyst
from backend.services.mcp_tools.util import audit_log

router = APIRouter()

# ------------------- Schemas -------------------
class FeedbackListIn(BaseModel):
    since: str
    until: str
    limit: int = 100
    offset: int = 0
class FeedbackItem(BaseModel):
    id: str
    submitted_at: str
    user_id: str
    page: str
    type: str
    severity: str
    text: str
class FeedbackListOut(BaseModel):
    items: List[FeedbackItem]

class FeedbackStatsIn(BaseModel):
    since: str
    until: str
class FeedbackStatsOut(BaseModel):
    countsByType: dict
    countsByPage: dict
    countsBySeverity: dict

# ------------------- Endpoints -------------------
@router.post("/feedback.list", response_model=FeedbackListOut)
async def feedback_list(
    body: FeedbackListIn,
    user=Depends(require_admin_or_analyst)
):
    # TODO: Query DB for feedback_submissions
    result = FeedbackListOut(items=[])
    await audit_log("feedback.list", user, body)
    return result

@router.post("/feedback.stats", response_model=FeedbackStatsOut)
async def feedback_stats(
    body: FeedbackStatsIn,
    user=Depends(require_admin_or_analyst)
):
    # TODO: Query DB for feedback stats
    result = FeedbackStatsOut(countsByType={}, countsByPage={}, countsBySeverity={})
    await audit_log("feedback.stats", user, body)
    return result
